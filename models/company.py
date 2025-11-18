# models/company.py
from pydantic import BaseModel
from typing import Optional

class CompanyCreate(BaseModel):
    name: str                   # Nama perusahaan (wajib)
    type: str                   # contoh: bus, travel, airline, train
    description: Optional[str] = None
    logo: Optional[str] = None          # URL logo nanti
    contact_email: Optional[str] = None
    phone: Optional[str] = None

class CompanyOut(CompanyCreate):
    id: str
    average_rating: Optional[float] = 0.0
    total_reviews: Optional[int] = 0