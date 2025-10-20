# app.py
import os
import smtplib
from dotenv import load_dotenv
load_dotenv()
from email.message import EmailMessage
from functools import wraps
import secrets, hashlib
from flask import Flask, render_template, request, redirect, url_for, session, g, flash
from bson import ObjectId
from config import settings
from db import db, ping
from auth import auth_bp
from werkzeug.security import check_password_hash
from datetime import datetime, timedelta, timezone
from werkzeug.security import check_password_hash, generate_password_hash


app = Flask(__name__)
app.config.from_object(settings)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev')
app.register_blueprint(auth_bp)  # keeps your /api/auth/* JSON endpoints

# ---------- Helpers ----------
def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()

def _new_reset_token():
    """Return (raw_token, token_hash, expires_at_utc)."""
    raw = secrets.token_urlsafe(32)  # safe to put in URL
    return raw, _hash_token(raw), datetime.now(timezone.utc) + timedelta(hours=1)

def login_required_view(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))  # endpoint name below
        return f(*args, **kwargs)
    return wrapper

@app.before_request
def load_current_user():
    g.current_user = None
    uid = session.get("user_id")
    if uid:
        from bson import ObjectId
        user = db.users.find_one({"_id": ObjectId(uid)}, {"password_hash": 0})
        g.current_user = user

@app.context_processor
def inject_globals():
    def to_id(v):
        return str(v) if v is not None else None
    return {"current_user": g.current_user, "to_id": to_id}

# ---------- Sample data (can delete later) ----------
sample_user = {'username': 'JohnDoe'}
sample_categories = [
    {'id': 1, 'name': 'School'},
    {'id': 2, 'name': 'Personal'},
    {'id': 3, 'name': 'Shopping'}
]
sample_tasks = [
    {'id': 1, 'title': 'Complete project report', 'category': 'Work', 'status': 'In Progress', 'priority': 'High'},
    {'id': 2, 'title': 'Buy groceries', 'category': 'Shopping', 'status': 'Pending', 'priority': 'Medium'},
    {'id': 3, 'title': 'Call dentist', 'category': 'Personal', 'status': 'Pending', 'priority': 'Low'}
]

# ---------- Public pages ----------
@app.get("/")
def home():
    return render_template("landing.html")

# SINGLE /login GET route (renders the page with optional email)
@app.get("/login")
def login():
    email = request.args.get("email", "")
    return render_template("login.html", email=email)

@app.post("/login")
def login_submit():
    email = (request.form.get("email") or "").strip().lower()
    password = request.form.get("password") or ""

    user = db.users.find_one({"email": email})
    # Check password using Werkzeug's secure hash comparison
    if not user or not check_password_hash(user.get("password_hash"), password):
        flash("Invalid email or password", "error")
        # PRG pattern; keep the typed email
        return redirect(url_for("login", email=email))

    # success
    session["user_id"] = str(user["_id"])                     # <— use user_id consistently
    session["name"] = user.get("name") or user.get("email")
    flash("Welcome back!", "success")
    return redirect(url_for("dashboard"))

@app.get("/signup")
def signup():
    return render_template("signup.html")

@app.get("/logout")
def logout_page():
    session.clear()
    flash("You’ve been logged out.", "success")
    return redirect(url_for("home"))

# ---------- Authed pages ----------
@app.get("/add-task")
@login_required_view
def add_task():
    return render_template("add_task.html", categories=sample_categories)

@app.get("/history")
@login_required_view
def history():
    uid = current_uid()
    if not uid:
        return redirect(url_for("login"))
    
    # Get user's categories
    cats = list(db["categories"].find({"user_id": uid}).sort("name", 1))
    categories = [{"id": str(c["_id"]), "name": c.get("name", "")} for c in cats]
    cat_map = {c["_id"]: c.get("name", "") for c in cats}
    
    # Get completed tasks
    completed_tasks_raw = list(db["tasks"].find({
        "user_id": uid,
        "status": "done"
    }).sort("updated_at", -1))
    
    # Add category names to tasks
    completed_tasks = []
    for t in completed_tasks_raw:
        cname = cat_map.get(t.get("category_id"), "")
        completed_tasks.append({
            "id": str(t["_id"]),
            "title": t.get("title", ""),
            "category": cname,
            "priority": t.get("priority", 2),
            "completed_date": t.get("updated_at", "")
        })
    
    return render_template("todo_history.html", tasks=completed_tasks, categories=categories)

@app.get("/dashboard")
@login_required_view
def dashboard():
    user = sample_user if g.current_user is None else {
        "username": g.current_user.get("name") or g.current_user.get("email")
    }
    return render_template(
        "dashboard.html",
        user=user,
        categories=sample_categories,
        tasks=sample_tasks
    )


# ---------- Forgot password ----------
def _mask(s: str) -> str:
    if not s:
        return ""
    at = s.find("@")
    return ("***" + s[at-2:]) if at > 2 else "***"

def send_reset_email(to: str, link: str):
    host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER", "")
    # Remove ANY whitespace (spaces, tabs, newlines, NBSP) from app password
    pwd_raw = os.getenv("SMTP_PASS", "") or ""
    pwd = re.sub(r"\s+", "", pwd_raw)
    frm = os.getenv("FROM_EMAIL") or user

    msg = EmailMessage()
    msg["Subject"] = "Reset your password"
    msg["From"] = frm
    msg["To"] = to
    msg.set_content(f"Click to reset your password:\n\n{link}\n\nThis link expires in 1 hour.")

    app.logger.info(f"SMTP connecting host={host} port={port} user=***{user[-4:] if user else ''}")
    with smtplib.SMTP(host, port, timeout=30) as s:
        s.ehlo()
        s.starttls()
        s.ehlo()
        s.login(user, pwd)
        s.send_message(msg)


@app.get("/forgot")
def forgot_password():
    return render_template("forgot.html")

@app.post("/forgot")
def forgot_password_post():
    email = (request.form.get("email") or "").strip().lower()
    user = db.users.find_one({"email": email})

    if user:
        raw, token_hash, exp = _new_reset_token()
        db.users.update_one(
            {"_id": user["_id"]},
            {"$set": {"reset_token_hash": token_hash, "reset_token_exp": exp}}
        )
        reset_link = url_for("reset_password", token=raw, _external=True)

        try:
            send_reset_email(to=email, link=reset_link)
        except Exception as e:
            app.logger.exception("Failed to send reset email")
            # DEV ONLY — remove before production
            flash(f"DEV: Email send failed: {e}", "error")

    flash("If that email exists, a reset link has been sent.", "success")
    return redirect(url_for("login"))


# ---------- Reset via token ----------
@app.get("/reset/<token>")
def reset_password(token):
    token_hash = _hash_token(token)
    now = datetime.now(timezone.utc)

    user = db.users.find_one({
        "reset_token_hash": token_hash,
        "reset_token_exp": {"$gt": now}
    })

    if not user:
        flash("This reset link is invalid or has expired.", "error")
        return redirect(url_for("forgot_password"))

    return render_template("reset.html", token=token)


@app.post("/reset/<token>")
def reset_password_post(token):
    token_hash = _hash_token(token)
    now = datetime.now(timezone.utc)

    user = db.users.find_one({
        "reset_token_hash": token_hash,
        "reset_token_exp": {"$gt": now}
    })

    if not user:
        flash("This reset link is invalid or has expired.", "error")
        return redirect(url_for("forgot_password"))

    pw1 = request.form.get("password") or ""
    pw2 = request.form.get("confirm_password") or ""

    # Basic validation
    if pw1 != pw2:
        flash("Passwords do not match.", "error")
        return redirect(url_for("reset_password", token=token))
    if len(pw1) < 8:
        flash("Password must be at least 8 characters.", "error")
        return redirect(url_for("reset_password", token=token))

    # Update password and clear token fields
    db.users.update_one(
    {"_id": user["_id"]},
    {"$set": {"password_hash": generate_password_hash(pw1)},
     "$unset": {"reset_token_hash": "", "reset_token_exp": ""}}
)

    # (Optional) log out all sessions by bumping a session version, if you store one.
    flash("Your password has been reset. Please log in.", "success")
    return redirect(url_for("login"))

# ---------- Health check ----------
@app.get("/test")
def health():
    return {"status": "ok", "db": "ok" if ping() else "down"}, 200

if __name__ == "__main__":
    app.run(debug=True, port=3000)


