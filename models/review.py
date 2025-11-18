# models/review.py (GANTI SELURUH ISI)
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ReviewCreate(BaseModel):
    booking_id: str
    rating: int        # 1-5
    comment: Optional[str] = None

class ReviewOut(BaseModel):
    id: str
    company_id: str
    company_name: str
    user_name: str
    rating: int
    comment: Optional[str] = None
    created_at: datetime

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }