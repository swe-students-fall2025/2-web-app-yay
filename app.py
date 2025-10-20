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
    
@app.route("/signup")
def signup():
    return render_template("signup.html")

@app.get("/logout")
def logout_page():
    session.clear()
    flash("You’ve been logged out.", "success")
    return redirect(url_for("home"))

# @app.route("/add-task")
# @login_required_view
# def add_task():
#     return render_template("add_task.html", categories=sample_categories)
@app.route("/add-task", methods=["GET", "POST"])
@login_required_view
def add_task():
    uid = current_uid()
    if not uid:
        return redirect(url_for("login"))
    if request.method == "POST":
        data = request.form
        title = (data.get("title") or "").strip()
        category_id = data.get("category_id")
        priority = (data.get("priority") or "medium").lower()
        status = (data.get("status") or "todo").lower()
        due_date_str = data.get("due_date")
        description = (data.get("description") or "").strip()

        if not title:
            return redirect(url_for("add_task"))
        cat_id = None
        if category_id and ObjectId.is_valid(category_id):
            cat_id = ObjectId(category_id)
        due_date = None
        if due_date_str:
            try:
                from datetime import datetime
                due_date = datetime.strptime(due_date_str, "%Y-%m-%d")
            except ValueError:
                pass
        priority_map = {"high": 1, "medium": 2, "low": 3}
        priority_val = priority_map.get(priority, 2)
        from datetime import datetime
        now = datetime.utcnow()
        task_doc = {
            "user_id": uid,
            "title": title,
            "category_id": cat_id,
            "priority": priority_val,
            "status": status,
            "due_date": due_date,
            "description": description,
            "created_at": now,
            "updated_at": now,
        }

        db.tasks.insert_one(task_doc)
        return redirect(url_for("dashboard"), code=303)
    cats = list(db["categories"].find({"user_id": uid}).sort("name", 1))
    categories = [{"id": str(c["_id"]), "name": c.get("name", "")} for c in cats]

    return render_template("add_task.html", categories=categories)

@app.route("/tasks/<task_id>/complete", methods=["POST"])
@login_required_view
def complete_task(task_id):
    uid = current_uid()
    if not uid:
        return redirect(url_for("login"))

    if not ObjectId.is_valid(task_id):
        return redirect(url_for("dashboard"))

    from datetime import datetime
    db.tasks.update_one(
        {"_id": ObjectId(task_id), "user_id": uid},
        {"$set": {
            "status": "done",
            "completed_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }}
    )

    return redirect(url_for("dashboard"))

# @app.route("/history")
# @login_required_view
# def history():
#     return render_template("todo_history.html")
@app.route("/edit-task/<task_id>", methods=["GET", "POST"])
@login_required_view
def edit_task(task_id):
    uid = current_uid()
    if not uid:
        return redirect(url_for("login"))

    if not ObjectId.is_valid(task_id):
        return redirect(url_for("dashboard"))

    task = db.tasks.find_one({"_id": ObjectId(task_id), "user_id": uid})
    if not task:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        data = request.form
        title = (data.get("title") or "").strip()
        category_id = data.get("category_id")
        priority = (data.get("priority") or "medium").lower()
        status = (data.get("status") or "todo").lower()
        due_date_str = data.get("due_date")
        description = (data.get("description") or "").strip()

        if not title:
            return redirect(url_for("edit_task", task_id=task_id))

        cat_id = None
        if category_id and ObjectId.is_valid(category_id):
            cat_id = ObjectId(category_id)

        due_date = None
        if due_date_str:
            try:
                from datetime import datetime
                due_date = datetime.strptime(due_date_str, "%Y-%m-%d")
            except ValueError:
                pass

        priority_map = {"high": 1, "medium": 2, "low": 3}
        priority_val = priority_map.get(priority, 2)

        from datetime import datetime
        db.tasks.update_one(
            {"_id": ObjectId(task_id)},
            {"$set": {
                "title": title,
                "category_id": cat_id,
                "priority": priority_val,
                "status": status,
                "due_date": due_date,
                "description": description,
                "updated_at": datetime.utcnow()
            }}
        )
        return redirect(url_for("dashboard"), code=303)

    # GET request - show edit form
    cats = list(db["categories"].find({"user_id": uid}).sort("name", 1))
    categories = [{"id": str(c["_id"]), "name": c.get("name", "")} for c in cats]

    def pri_to_text(p):
        if isinstance(p, str): return p
        return {1: "High", 2: "Medium", 3: "Low"}.get(p, "Medium")

    # Format task data for template
    task_data = {
        "id": str(task["_id"]),
        "title": task.get("title", ""),
        "category_id": str(task.get("category_id", "")),
        "priority": pri_to_text(task.get("priority", "Medium")),
        "status": task.get("status", "todo"),
        "due_date": task.get("due_date").strftime("%Y-%m-%d") if task.get("due_date") else "",
        "description": task.get("description", "")
    }

    return render_template("edit_task.html", task=task_data, categories=categories)

@app.route("/history")
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
# 解释一下：上面被注释掉的代码都是我原来实现用url取userid的逻辑，下面新的代码都是需要登陆后从user session里面取id。目前全部实现代码我都改成了要求登陆，
# 如果有问题可以把下面的代码注释了，把上面代码取消注释就可以看我原来的代码实现逻辑。
# AAA: 把上面取消注释下面注释起来
# @app.route('/dashboard')
# def dashboard():
#     # Read User's ID for display dashboard
#     user_id_str = request.args.get('user_id')
#     category = request.args.get('category', 'all')
#
#     uid = None
#     if user_id_str:
#         try:
#             uid = ObjectId(user_id_str)
#         except Exception:
#             uid = None
#
#     # categories
#     cat_query = {"user_id": uid} if uid else {}
#     cats = list(db["categories"].find(cat_query).sort("name", 1))
#     categories = [{"id": str(c["_id"]), "name": c.get("name", "")} for c in cats]
#     cat_map = {c["_id"]: c.get("name", "") for c in cats}
#
#     q = {"user_id": uid} if uid else {}
#
#     if category and category != "all":
#         if ObjectId.is_valid(category):
#             # search by id
#             q["category_id"] = ObjectId(category)
#         else:
#             found = next((c for c in cats if c.get("name") == category), None)
#             if found:
#                 q["category_id"] = found["_id"]
#
#     tasks_cur = db["tasks"].find(q).sort("updated_at", -1)
#
#     def pri_to_text(p):
#         if isinstance(p, str): return p
#         return {1: "High", 2: "Medium", 3: "Low"}.get(p, "Medium")
#
#     tasks = []
#     for t in tasks_cur:
#         cname = cat_map.get(t.get("category_id")) or t.get("category", "")
#         tasks.append({
#             "id": str(t["_id"]),
#             "title": t.get("title", ""),
#             "category": cname,
#             "status": t.get("status", "Pending"),
#             "priority": pri_to_text(t.get("priority", "Medium")),
#         })
#
#     user = {"username": "JohnDoe"}
#
#     return render_template(
#         "dashboard.html",
#         user=user,
#         categories=categories,
#         tasks=tasks,
#     )


@app.route('/dashboard')
@login_required_view
def dashboard():
        # NOTE: 登录后不再从 URL 拿 user_id；直接从 session 取
    uid = current_uid()

    category = request.args.get('category', 'all')
    sort_type = request.args.get('sort', 'default')
    search_query = request.args.get('search', '').strip()

    cat_query = {"user_id": uid} if uid else {}
    cats = list(db["categories"].find(cat_query).sort("name", 1))
    categories = [{"id": str(c["_id"]), "name": c.get("name", "")} for c in cats]
    cat_map = {c["_id"]: c.get("name", "") for c in cats}

    q = {"user_id": uid} if uid else {}

    # Exclude completed tasks from dashboard (they should only appear in history)
    q["status"] = {"$ne": "done"}

    if category and category != "all":
        if ObjectId.is_valid(category):
            q["category_id"] = ObjectId(category)
        else:
            found = next((c for c in cats if c.get("name") == category), None)
            if found:
                q["category_id"] = found["_id"]

    # Add search functionality
    if search_query:
        # Search in title and description using regex 
        q["$or"] = [
            {"title": {"$regex": search_query, "$options": "i"}},
            {"description": {"$regex": search_query, "$options": "i"}}
        ]

    # Determine sorting based on sort_type parameter
    if sort_type == 'priority':
        # Sort by priority (1=high, 2=medium, 3=low) then by due_date (closer first)
        tasks_cur = db["tasks"].find(q).sort([
            ("priority", 1),  # Priority ascending (high=1 first)
            ("due_date", 1)   # Due date ascending (closer dates first)
        ])
    elif sort_type == 'due_date':
        # Sort by due_date (closer first), then by priority
        tasks_cur = db["tasks"].find(q).sort([
            ("due_date", 1),  # Due date ascending (closer dates first)
            ("priority", 1)   # Priority ascending (high=1 first)
        ])
    else:
        # Default sorting by updated_at
        tasks_cur = db["tasks"].find(q).sort("updated_at", -1)

    def pri_to_text(p):
        if isinstance(p, str): return p
        return {1: "High", 2: "Medium", 3: "Low"}.get(p, "Medium")

    tasks = []
    upcoming_deadlines = []  # For notification section

    for t in tasks_cur:
        cname = cat_map.get(t.get("category_id")) or t.get("category", "")
        due_date = t.get("due_date")
        due_date_str = due_date.strftime("%Y-%m-%d") if due_date else None

        tasks.append({
            "id": str(t["_id"]),
            "title": t.get("title", ""),
            "category": cname,
            "status": t.get("status", "Pending"),
            "priority": pri_to_text(t.get("priority", "Medium")),
            "due_date": due_date_str,
        })

        # Calculate days until deadline for upcoming tasks
        if t.get("due_date") and t.get("status") != "done":
            from datetime import datetime
            due_date = t.get("due_date")
            today = datetime.utcnow()
            days_left = (due_date - today).days

            # Only show tasks due within 7 days
            if days_left >= 0 and days_left <= 7:
                upcoming_deadlines.append({
                    "title": t.get("title", ""),
                    "days_left": days_left,
                    "priority": pri_to_text(t.get("priority", "Medium"))
                })

    # Sort by days_left (most urgent first)
    upcoming_deadlines.sort(key=lambda x: x["days_left"])

    user = {"username": g.current_user.get("name", "User") if g.current_user else "User"}

    return render_template("dashboard.html", user=user, categories=categories, tasks=tasks, upcoming_deadlines=upcoming_deadlines, search_query=search_query)

# AAA: 把上面取消注释下面注释起来
# @app.post("/api/categories")
# def api_add_category():
#     data = request.form or request.get_json(silent=True) or {}
#     name = (data.get("name") or "").strip()
#     user_id = data.get("user_id") or request.args.get("user_id")
#
#     if not name:
#         if request.form:
#             return redirect(url_for("dashboard", category="all", user_id=user_id))
#         return jsonify({"error": "name required"}), 400
#
#     try:
#         uid = ObjectId(user_id)
#     except Exception:
#         if request.form:
#             return redirect(url_for("dashboard", category="all"))
#         return jsonify({"error": "user required"}), 401
#
#     q = {"user_id": uid, "name": name}
#     if db["categories"].find_one(q):
#         return (redirect(url_for("dashboard", category="all", user_id=user_id))
#                 if request.form else jsonify({"created": False, "reason": "exists"}), 200)
#
#     db["categories"].insert_one({"user_id": uid, "name": name})
#
#     if request.form:
#         return redirect(url_for("dashboard", category="all", user_id=user_id), code=303)
#     return jsonify({"created": True, "name": name}), 201


@app.post("/api/categories")
@login_required_view
def api_add_category():
    data = request.form or request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()

    if not name:
        if request.form:
            return redirect(url_for("dashboard", category="all"))
        return jsonify({"error": "name required"}), 400

    uid = current_uid()
    if not uid:
        if request.form:
            return redirect(url_for("login"))
        return jsonify({"error": "user required"}), 401

    if db["categories"].find_one({"user_id": uid, "name": name}):
        return (redirect(url_for("dashboard", category="all"))
                if request.form else jsonify({"created": False, "reason": "exists"}), 200)

    db["categories"].insert_one({"user_id": uid, "name": name})

    if request.form:
        return redirect(url_for("dashboard", category="all"), code=303)
    return jsonify({"created": True, "name": name}), 201


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


