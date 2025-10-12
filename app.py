# app.py
from flask import Flask, render_template, redirect, url_for, session, g
from functools import wraps

from config import settings  
from auth import auth_bp
from db import db, ping 

app = Flask(__name__)
app.config.from_object(settings)
app.register_blueprint(auth_bp)

def login_required_view(f):
    """Redirect to /login if not authenticated (for HTML page routes)."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper

@app.before_request
def load_current_user():
    """Attach current user (if any) to g and inject into templates."""
    g.current_user = None
    uid = session.get("user_id")
    if uid:
        from bson import ObjectId
        user = db.users.find_one({"_id": ObjectId(uid)}, {"password_hash": 0})
        g.current_user = user

@app.context_processor
def inject_globals():
    """Make current_user available in all Jinja templates."""
    def to_id(v):
        # convenience filter if you need str(ObjectId)
        return str(v) if v is not None else None
    return {"current_user": g.current_user, "to_id": to_id}


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

@app.route("/")
def home():
    return render_template("landing.html")

@app.route("/login")
def login():
    return render_template("login.html")

@app.route("/signup")
def signup():
    return render_template("signup.html")

@app.route("/logout")
def logout_page():
    session.clear()
    return redirect(url_for("home"))

@app.route("/add-task")
@login_required_view
def add_task():
    return render_template("add_task.html", categories=sample_categories)

@app.route("/history")
@login_required_view
def history():
    return render_template("todo_history.html")

@app.route("/dashboard")
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

@app.get("/test")
def health():
    from db import ping
    return {"status": "ok", "db": "ok" if ping() else "down"}, 200

if __name__ == "__main__":
    app.run(debug=True, port=3000)
