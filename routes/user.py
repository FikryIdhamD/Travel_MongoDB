# routes/user.py (MODIFIKASI: Tambah register admin, CRUD lengkap)
from fastapi import APIRouter, HTTPException, Depends
from models.user import UserCreate, UserLogin, UserOut
from database import users
from passlib.context import CryptContext
from bson import ObjectId
from typing import List, Optional
from utils.auth import get_current_user_admin

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Register customer (asli)
@router.post("/register")
async def register(user_in: UserCreate):
    if users.find_one({"email": user_in.email}):
        raise HTTPException(400, "Email sudah digunakan")
    hashed = pwd_context.hash(user_in.password)
    user_doc = user_in.dict()
    user_doc["password"] = hashed
    user_doc["role"] = "customer"
    result = users.insert_one(user_doc)
    return {
        "msg": "User dibuat",
        "user": {
            "id": str(result.inserted_id),
            "name": user_doc["name"],
            "email": user_doc["email"],
            "role": "customer"
        }
    }

# Register admin (BARU: Khusus admin, mungkin panggil manual atau dari console)
@router.post("/register_admin")
async def register_admin(user_in: UserCreate, current_admin=Depends(get_current_user_admin)):
    if users.find_one({"email": user_in.email}):
        raise HTTPException(400, "Email sudah digunakan")
    hashed = pwd_context.hash(user_in.password)
    user_doc = user_in.dict()
    user_doc["password"] = hashed
    user_doc["role"] = "admin"
    result = users.insert_one(user_doc)
    return {
        "msg": "Admin dibuat",
        "user": {
            "id": str(result.inserted_id),
            "name": user_doc["name"],
            "email": user_doc["email"],
            "role": "admin"
        }
    }

# Login (asli, support admin/customer)
@router.post("/login")
async def login(user_in: UserLogin):
    user = users.find_one({"email": user_in.email})
    if not user or not pwd_context.verify(user_in.password, user["password"]):
        raise HTTPException(400, "Login gagal")
    return {
        "msg": "Login sukses",
        "user": {
            "id": str(user["_id"]),
            "name": user["name"],
            "email": user["email"],
            "role": user.get("role", "customer")
        }
    }

# Get all users (ADMIN ONLY)
@router.get("/", response_model=List[dict])
async def get_users(current_admin=Depends(get_current_user_admin)):
    user_list = []
    for u in users.find({}, {"password": 0}):
        u["id"] = str(u["_id"])
        del u["_id"]
        user_list.append(u)
    return user_list

# Get user by ID (ADMIN ONLY)
@router.get("/{user_id}", response_model=dict)
async def get_user(user_id: str, current_admin=Depends(get_current_user_admin)):
    if not ObjectId.is_valid(user_id):
        raise HTTPException(400, "ID tidak valid")
    user = users.find_one({"_id": ObjectId(user_id)}, {"password": 0})
    if not user:
        raise HTTPException(404, "User tidak ditemukan")
    user["id"] = str(user["_id"])
    del user["_id"]
    return user

# Update user (ADMIN ONLY)
@router.put("/{user_id}")
async def update_user(user_id: str, user_in: UserCreate, current_admin=Depends(get_current_user_admin)):
    if not ObjectId.is_valid(user_id):
        raise HTTPException(400, "ID tidak valid")
    update_data = user_in.dict(exclude_unset=True)
    if "password" in update_data:
        update_data["password"] = pwd_context.hash(update_data["password"])
    result = users.update_one({"_id": ObjectId(user_id)}, {"$set": update_data})
    if result.modified_count == 0:
        raise HTTPException(404, "User tidak ditemukan atau tidak ada perubahan")
    return {"message": "User diperbarui"}

# Delete user (ADMIN ONLY)
@router.delete("/{user_id}")
async def delete_user(user_id: str, current_admin=Depends(get_current_user_admin)):
    if not ObjectId.is_valid(user_id):
        raise HTTPException(400, "ID tidak valid")
    result = users.delete_one({"_id": ObjectId(user_id)})
    if result.deleted_count == 0:
        raise HTTPException(404, "User tidak ditemukan")
    return {"message": "User dihapus"}