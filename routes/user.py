# routes/user.py
from fastapi import APIRouter, HTTPException
from models.user import UserCreate, UserLogin, UserOut
from database import users
from passlib.context import CryptContext
from bson import ObjectId

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

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

@router.get("/")
async def get_users():
    user_list = []
    for u in users.find({}, {"password": 0}):
        u["id"] = str(u["_id"])
        del u["_id"]
        user_list.append(u)
    return user_list