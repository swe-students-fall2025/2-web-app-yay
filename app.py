# app.py
from flask import Flask, render_template, redirect, url_for, session, g, request, jsonify
from functools import wraps
from flask_login import login_required, current_user
from bson import ObjectId

from config import settings  
from auth import auth_bp
from db import db, ping 

from todo_AddDelete import register_task_routes

app = Flask(__name__)
app.config.from_object(settings)
app.register_blueprint(auth_bp)
register_task_routes(app)

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

@app.route("/logout", methods=["GET", "POST"])
def logout_page():
    session.clear()
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

    user = {"username": getattr(current_user, "username", "User")}

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


@app.get("/test")
def health():
    return {"status": "ok", "db": "ok" if ping() else "down"}, 200

if __name__ == "__main__":
    app.run(debug=True, port=3000)
