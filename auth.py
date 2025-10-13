import hashlib, os
from datetime import datetime
from flask import Blueprint, request, session, jsonify
from bson import ObjectId

from db import db

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

def _hash(pw: str) -> str:
    return hashlib.sha256((os.getenv("SECRET_KEY", "") + pw).encode()).hexdigest()

@auth_bp.post("/signup")
def api_signup():
    data = request.get_json(silent=True) or request.form
    email = (data.get("email") or "").strip().lower()
    name  = (data.get("name") or "").strip()
    pwd   = data.get("password") or ""

    if not email or not pwd:
        return jsonify({"ok": False, "error": "email and password are required"}), 400

    if db.users.find_one({"email": email}):
        return jsonify({"ok": False, "error": "email already registered"}), 409

    doc = {
        "email": email,
        "name": name,
        "password_hash": _hash(pwd),
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    res = db.users.insert_one(doc)

    session["user_id"] = str(res.inserted_id)

    return jsonify({
        "ok": True,
        "user": {"id": str(res.inserted_id), "email": email, "name": name}
    }), 201

@auth_bp.post("/login")
def api_login():
    data = request.get_json(silent=True) or request.form
    ident = (data.get("email") or data.get("username") or "").strip().lower()
    pwd   = data.get("password") or ""
    if not ident or not pwd:
        return jsonify({"ok": False, "error": "missing fields"}), 400

    u = db.users.find_one({"email": ident}) or db.users.find_one({"username": ident})
    if not u or u.get("password_hash") != _hash(pwd):
        return jsonify({"ok": False, "error": "invalid email or password"}), 401

    session["user_id"] = str(u["_id"])
    return jsonify({
        "ok": True,
        "user": {"id": str(u["_id"]), "email": u.get("email",""), "name": u.get("name","")}
    }), 200

@auth_bp.post("/logout")
def api_logout():
    session.clear()
    return jsonify({"ok": True}), 200

@auth_bp.get("/me")
def api_me():
    uid = session.get("user_id")
    if not uid:
        return jsonify({"error": "unauthorized"}), 401
    u = db.users.find_one({"_id": ObjectId(uid)}, {"password_hash": 0})
    return jsonify({
        "user": {"id": str(u["_id"]), "email": u.get("email",""), "name": u.get("name","")}
    }), 200
