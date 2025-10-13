# app.py
from flask import Flask, render_template, redirect, url_for, session, g, request, jsonify
from functools import wraps
from flask_login import login_required, current_user
from bson import ObjectId

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


def current_uid():
    uid = session.get("user_id")
    return ObjectId(uid) if uid and ObjectId.is_valid(uid) else None


# Global mock data
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

    cat_query = {"user_id": uid} if uid else {}
    cats = list(db["categories"].find(cat_query).sort("name", 1))
    categories = [{"id": str(c["_id"]), "name": c.get("name", "")} for c in cats]
    cat_map = {c["_id"]: c.get("name", "") for c in cats}

    q = {"user_id": uid} if uid else {}

    if category and category != "all":
        if ObjectId.is_valid(category):
            q["category_id"] = ObjectId(category)
        else:
            found = next((c for c in cats if c.get("name") == category), None)
            if found:
                q["category_id"] = found["_id"]

    tasks_cur = db["tasks"].find(q).sort("updated_at", -1)

    def pri_to_text(p):
        if isinstance(p, str): return p
        return {1: "High", 2: "Medium", 3: "Low"}.get(p, "Medium")

    tasks = []
    for t in tasks_cur:
        cname = cat_map.get(t.get("category_id")) or t.get("category", "")
        tasks.append({
            "id": str(t["_id"]),
            "title": t.get("title", ""),
            "category": cname,
            "status": t.get("status", "Pending"),
            "priority": pri_to_text(t.get("priority", "Medium")),
        })

    user = {"username": getattr(current_user, "username", "User")}

    return render_template("dashboard.html", user=user, categories=categories, tasks=tasks)

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


@app.get("/test")
def health():
    return {"status": "ok", "db": "ok" if ping() else "down"}, 200

if __name__ == "__main__":
    app.run(debug=True, port=3000)
