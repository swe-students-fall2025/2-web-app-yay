from flask import Blueprint, jsonify

bp = Blueprint("todos_query", __name__)


@bp.get("/todos")
def list_todos():
    # 先返回一个占位结果，验证路由打通
    return jsonify(items=[{"id":"demo1","title":"Hello, API is wired up!"}]), 200