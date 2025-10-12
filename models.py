from typing import Optional, Dict, Any
from datetime import datetime, timezone
from bson import ObjectId
from bson.errors import InvalidId
from pydantic import BaseModel, Field

from config import settings
from pymongo import MongoClient

_client = MongoClient(settings.MONGO_URI)
_db = _client[settings.MONGO_DB]

def users():
    return _db.users

def categories():
    return _db.categories

def tasks():
    return _db.tasks

def parse_oid(s: str) -> ObjectId:
    try:
        return ObjectId(s)
    except (InvalidId, TypeError):
        raise ValueError("invalid id")

def to_doc_id(doc: Dict[str, Any]) -> Dict[str, Any]:
    """_id -> id（返回给前端用）"""
    if not doc:
        return doc
    doc["id"] = str(doc.pop("_id"))
    if "user_id" in doc and isinstance(doc["user_id"], ObjectId):
        doc["user_id"] = str(doc["user_id"])
    if "category_id" in doc and isinstance(doc["category_id"], ObjectId):
        doc["category_id"] = str(doc["category_id"])
    return doc

class UserLogin(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)

class TaskIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    category_id: Optional[str] = None
    priority: str = Field(default="low")   
    status: str = Field(default="todo") 
    description: Optional[str] = None

def new_task_doc(user_id: str, payload: TaskIn) -> Dict[str, Any]:
    now = datetime.now(timezone.utc)
    return {
        "user_id": parse_oid(user_id),
        "title": payload.title.strip(),
        "category_id": parse_oid(payload.category_id) if payload.category_id else None,
        "priority": payload.priority,
        "status": payload.status,
        "due_date": payload.due_date,
        "description": payload.description or "",
        "created_at": now,
        "updated_at": now,
    }
