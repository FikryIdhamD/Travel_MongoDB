# models/schedule.py (GANTI SELURUH ISI)
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ScheduleCreate(BaseModel):
    company_id: str                    # BARU & WAJIB
    type: str                          # bus / flight / train
    origin: str
    destination: str
    departure_date: datetime
    arrival_date: Optional[datetime] = None
    price: int
    available_seats: int
    operator: Optional[str] = None     # boleh diisi atau kosong (redundan nanti)

class ScheduleOut(ScheduleCreate):
    id: str