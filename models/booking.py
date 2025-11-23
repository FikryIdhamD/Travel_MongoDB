# models/booking.py

from datetime import datetime
from pydantic import BaseModel
from typing import Optional

class BookingCreate(BaseModel):
    user_id: str
    schedule_id: str
    passenger_name: str
    passenger_count: int

class BookingOut(BaseModel):
    id: str
    booking_code: str
    status: str                     # pending, confirmed, completed, cancelled
    status_review: str = "pending"  # pending | done
    total_price: int
    passenger_name: str
    passenger_count: int
    booking_date: datetime
    has_review: bool = False        # kompatibilitas lama (opsional)

    # field join yang ingin ditampilkan ke user
    schedule_info: dict
    user_info: Optional[dict] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class BookingUpdate(BaseModel):
    passenger_name: Optional[str] = None
    passenger_count: Optional[int] = None
    status: Optional[str] = None          # pending, confirmed, completed, cancelled
    status_review: Optional[str] = None   # pending, done (jarang diubah manual)