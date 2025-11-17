# models/review.py
from pydantic import BaseModel
from typing import Optional

class ReviewCreate(BaseModel):
    booking_id: str
    rating: int  # 1-5
    comment: Optional[str] = None

class ReviewOut(BaseModel):
    booking_id: str
    user_name: str
    rating: int
    comment: Optional[str] = None
    created_at: str