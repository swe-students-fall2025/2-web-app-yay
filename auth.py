from flask import Blueprint, request, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from bson import ObjectId
from functools import wraps

from db import db

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"error": "unauthorized"}), 401
        return f(*args, **kwargs)
    return wrapper

def public_user(user_doc):
    """Return safe fields only."""
    return {
        "id": str(user_doc["_id"]),
        "email": user_doc["email"],
        "name": user_doc.get("name", "")
    }

@auth_bp.post("/signup")
def signup():
    data = request.get_json(silent=True) or request.form
    email = (data.get("email") or "").strip().lower()
    name  = (data.get("name") or "").strip()
    pwd   = data.get("password") or ""

    if not email or not pwd:
        return jsonify({"error": "email and password are required"}), 400

    if db.users.find_one({"email": email}):
        return jsonify({"error": "email already registered"}), 409

    pwd_hash = generate_password_hash(pwd)  # salted hash
    doc = {
        "email": email,
        "name": name,
        "password_hash": pwd_hash,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    res = db.users.insert_one(doc)

    session["user_id"] = str(res.inserted_id)  # log the user in immediately
    user = db.users.find_one({"_id": res.inserted_id})
    return jsonify({"ok": True, "user": public_user(user)}), 201


@auth_bp.post("/login")
def login():
    data = request.get_json(silent=True) or request.form
    email = (data.get("email") or "").strip().lower()
    pwd   = data.get("password") or ""

    user = db.users.find_one({"email": email})
    if not user or not check_password_hash(user["password_hash"], pwd):
        return jsonify({"error": "invalid email or password"}), 401

    session["user_id"] = str(user["_id"])
    return jsonify({"ok": True, "user": public_user(user)}), 200

@auth_bp.post("/logout")
def logout():
    session.clear()
    return jsonify({"ok": True}), 200


@auth_bp.get("/me")
@login_required
def me():
    user = db.users.find_one({"_id": ObjectId(session["user_id"])})
    return jsonify({"user": public_user(user)}), 200
