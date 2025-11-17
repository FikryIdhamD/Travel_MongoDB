# utils/auth.py
from fastapi import Depends, HTTPException, Header
import json

def get_current_user(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token diperlukan")
    try:
        token = authorization.split("Bearer ")[1]
        user = json.loads(token)
        if not user.get("id"):
            raise ValueError
        return user
    except Exception:
        raise HTTPException(status_code=401, detail="Token tidak valid")