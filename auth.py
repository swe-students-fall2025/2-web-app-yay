import hashlib, os
from flask import Blueprint, request, session, jsonify

from db import db

auth_bp = Blueprint("auth_bp", __name__)

def _hash(pw: str) -> str:
    return hashlib.sha256((os.getenv("SECRET_KEY", "") + pw).encode()).hexdigest()

@auth_bp.post("/api/login")
def api_login():
    data = request.get_json(force=True, silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    if not username or not password:
        return jsonify({"ok": False, "error": "missing fields"}), 400

    u = db.users.find_one({"username": username})
    if not u or u.get("password_hash") != _hash(password):
        return jsonify({"ok": False, "error": "bad credentials"}), 401

    session["user"] = {"id": str(u["_id"]), "username": u["username"]}
    return jsonify({"ok": True})

@auth_bp.post("/logout")
def logout():
    session.clear()
    return jsonify({"ok": True})
