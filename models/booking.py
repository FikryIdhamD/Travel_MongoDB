# models/booking.py

from pydantic import BaseModel
from typing import Optional

class BookingCreate(BaseModel):
    user_id: str
    schedule_id: str
    passenger_name: str
    passenger_count: int