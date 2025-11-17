# models/schedule.py

from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ScheduleCreate(BaseModel):
    type: str
    origin: str
    destination: str
    departure_date: datetime
    arrival_date: Optional[datetime] = None
    price: int
    available_seats: int
    operator: Optional[str] = None