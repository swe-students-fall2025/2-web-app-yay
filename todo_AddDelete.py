from flask import request, jsonify, redirect, url_for, session
from bson import ObjectId
from datetime import datetime
from functools import wraps

from db import db


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            if not request.is_json:
                return redirect(url_for("login"))
            return jsonify({"error": "unauthorized"}), 401
        return f(*args, **kwargs)
    return wrapper


def current_uid():
    uid = session.get("user_id")
    return ObjectId(uid) if uid and ObjectId.is_valid(uid) else None


def register_task_routes(app):
    
    @app.post("/api/tasks")
    @login_required
    def api_add_task():
        data = request.form or request.get_json(silent=True) or {}
        
        title = (data.get("title") or "").strip()
        if not title:
            return redirect(url_for("dashboard"), code=303) if not request.is_json else (jsonify({"error": "title required"}), 400)
        
        uid = current_uid()
        category_id = data.get("category_id")
        priority = (data.get("priority") or "medium").lower()
        status = (data.get("status") or "todo").lower()
        due_date_str = data.get("due_date")
        description = (data.get("description") or "").strip()
        
        cat_id = None
        if category_id and ObjectId.is_valid(category_id):
            cat_id = ObjectId(category_id)
        
        due_date = None
        if due_date_str:
            try:
                due_date = datetime.strptime(due_date_str, "%Y-%m-%d")
            except ValueError:
                pass
        
        priority_map = {"high": 1, "medium": 2, "low": 3}
        priority_val = priority_map.get(priority, 2)
        
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
        
        result = db.tasks.insert_one(task_doc)
        
        if not request.is_json:
            return redirect(url_for("dashboard"), code=303)
        
        return jsonify({"created": True, "task_id": str(result.inserted_id)}), 201
    
    
    @app.post("/api/tasks/<task_id>/delete")
    @login_required
    def api_delete_task(task_id):
        if not ObjectId.is_valid(task_id):
            return redirect(url_for("dashboard"), code=303) if not request.is_json else (jsonify({"error": "invalid task id"}), 400)
        
        uid = current_uid()
        
        result = db.tasks.delete_one({"_id": ObjectId(task_id), "user_id": uid})
        
        if not request.is_json:
            return redirect(url_for("dashboard"), code=303)
        
        if result.deleted_count == 0:
            return jsonify({"error": "task not found"}), 404
        
        return jsonify({"deleted": True, "task_id": task_id}), 200
    
    
    @app.post("/api/tasks/<task_id>/update")
    @login_required
    def api_update_task(task_id):
        if not ObjectId.is_valid(task_id):
            return jsonify({"error": "invalid task id"}), 400
        
        uid = current_uid()
        data = request.form or request.get_json(silent=True) or {}
        update_fields = {}
        
        if "title" in data and data["title"].strip():
            update_fields["title"] = data["title"].strip()
        
        if "status" in data:
            update_fields["status"] = data["status"].lower()
        
        if "priority" in data:
            priority_map = {"high": 1, "medium": 2, "low": 3}
            update_fields["priority"] = priority_map.get(data["priority"].lower(), 2)
        
        if "category_id" in data and data["category_id"] and ObjectId.is_valid(data["category_id"]):
            update_fields["category_id"] = ObjectId(data["category_id"])
        
        if "due_date" in data and data["due_date"]:
            try:
                update_fields["due_date"] = datetime.strptime(data["due_date"], "%Y-%m-%d")
            except ValueError:
                pass
        
        if "description" in data:
            update_fields["description"] = data["description"].strip()
        
        if not update_fields:
            return jsonify({"error": "no fields to update"}), 400
        
        update_fields["updated_at"] = datetime.utcnow()
        
        result = db.tasks.update_one(
            {"_id": ObjectId(task_id), "user_id": uid},
            {"$set": update_fields}
        )
        
        if result.matched_count == 0:
            return jsonify({"error": "task not found"}), 404
        
        return jsonify({"updated": True, "task_id": task_id}), 200
    
    
    @app.post("/api/tasks/<task_id>/complete")
    @login_required
    def api_complete_task(task_id):
        if not ObjectId.is_valid(task_id):
            return jsonify({"error": "invalid task id"}), 400
        
        uid = current_uid()
        
        result = db.tasks.update_one(
            {"_id": ObjectId(task_id), "user_id": uid},
            {"$set": {
                "status": "done",
                "completed_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }}
        )
        
        if result.matched_count == 0:
            return jsonify({"error": "task not found"}), 404
        
        return jsonify({"completed": True, "task_id": task_id}), 200