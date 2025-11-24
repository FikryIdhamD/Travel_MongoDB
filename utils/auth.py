# utils/auth.py
from fastapi import Header, HTTPException
from database import users
from bson import ObjectId

def get_current_user_admin(
    x_user_id: str = Header(None, alias="X-User-ID"),
    x_user_role: str = Header(None, alias="X-User-Role")
):
    if not x_user_id or not x_user_role:
        raise HTTPException(401, "Header X-User-ID dan X-User-Role wajib diisi")
    
    if x_user_role != "admin":
        raise HTTPException(403, "Akses hanya untuk admin")
    
    # Validasi user benar-benar ada dan role admin
    try:
        user_obj_id = ObjectId(x_user_id)
        user = users.find_one({"_id": user_obj_id})
        if not user or user.get("role") != "admin":
            raise HTTPException(403, "Admin tidak valid")
        return user
    except ValueError:
        raise HTTPException(400, "X-User-ID tidak valid (harus ObjectId hex)")
    except Exception:
        raise HTTPException(403, "User ID tidak valid")