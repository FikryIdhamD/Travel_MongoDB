# routes/company.py (UPDATE SELURUH FILE)

from fastapi import APIRouter, HTTPException, Depends
from models.company import CompanyCreate, CompanyOut
from database import companies
from utils.auth import get_current_user_admin
from bson import ObjectId
from typing import List

router = APIRouter()

# === CREATE Perusahaan (ADMIN ONLY) ===
@router.post("/", response_model=CompanyOut)
async def create_company(
    company_in: CompanyCreate,
    current_admin = Depends(get_current_user_admin)
):
    if companies.find_one({"name": {"$regex": f"^{company_in.name}$", "$options": "i"}}):
        raise HTTPException(400, "Nama perusahaan sudah ada")
    
    doc = company_in.dict()
    result = companies.insert_one(doc)
    created = companies.find_one({"_id": result.inserted_id})
    
    return CompanyOut(
        id=str(created["_id"]),
        **created,
        average_rating=0.0,
        total_reviews=0
    )

# === UPDATE Perusahaan (ADMIN ONLY) ===
@router.put("/{company_id}", response_model=CompanyOut)
async def update_company(
    company_id: str,
    company_in: CompanyCreate,
    current_admin = Depends(get_current_user_admin)
):
    if not ObjectId.is_valid(company_id):
        raise HTTPException(400, "ID tidak valid")
    
    result = companies.update_one(
        {"_id": ObjectId(company_id)},
        {"$set": company_in.dict()}
    )
    if result.modified_count == 0:
        raise HTTPException(404, "Perusahaan tidak ditemukan atau tidak ada perubahan")
    
    updated = companies.find_one({"_id": ObjectId(company_id)})
    return CompanyOut(
        id=str(updated["_id"]),
        **updated,
        average_rating=0.0,
        total_reviews=0
    )

# === DELETE Perusahaan (ADMIN ONLY) ===
@router.delete("/{company_id}")
async def delete_company(
    company_id: str,
    current_admin = Depends(get_current_user_admin)
):
    if not ObjectId.is_valid(company_id):
        raise HTTPException(400, "ID tidak valid")
    
    # Cek apakah ada jadwal yang pakai perusahaan ini (opsional)
    from database import schedules
    if schedules.find_one({"company_id": ObjectId(company_id)}):
        raise HTTPException(400, "Tidak bisa hapus: perusahaan masih punya jadwal")
    
    result = companies.delete_one({"_id": ObjectId(company_id)})
    if result.deleted_count == 0:
        raise HTTPException(404, "Perusahaan tidak ditemukan")
    
    return {"message": "Perusahaan dihapus"}

# === GET Semua Perusahaan (Publik) ===
@router.get("/", response_model=List[CompanyOut])
async def get_companies():
    pipeline = [
        {"$lookup": {
            "from": "reviews",
            "localField": "_id",
            "foreignField": "company_id",
            "as": "company_reviews"
        }},
        {"$addFields": {
            "average_rating": {"$round": [{"$ifNull": [{"$avg": "$company_reviews.rating"}, 0]}, 1]},
            "total_reviews": {"$size": "$company_reviews"}
        }},
        {"$project": {
            "name": 1, "type": 1, "description": 1, "logo": 1,
            "contact_email": 1, "phone": 1, "average_rating": {"$ifNull": ["$cached_rating", 0]}, "total_reviews": {"$ifNull": ["$cached_total_reviews", 0]}
        }}
    ]
    result = list(companies.aggregate(pipeline))
    for item in result:
        item["id"] = str(item["_id"])
        item.pop("_id", None)
        item["average_rating"] = item.get("average_rating") or 0.0
    return result

# === GET Detail Perusahaan (Publik) ===
@router.get("/{company_id}", response_model=CompanyOut)
async def get_company(company_id: str):
    if not ObjectId.is_valid(company_id):
        raise HTTPException(400, "ID tidak valid")
    
    pipeline = [
        {"$match": {"_id": ObjectId(company_id)}},
        {"$lookup": {
            "from": "reviews",
            "localField": "_id",
            "foreignField": "company_id",
            "as": "company_reviews"
        }},
        {"$addFields": {
            "average_rating": {"$round": [{"$ifNull": [{"$avg": "$company_reviews.rating"}, 0]}, 1]},
            "total_reviews": {"$size": "$company_reviews"}
        }},
        {"$project": {"company_reviews": 0}}
    ]
    
    try:
        company = next(companies.aggregate(pipeline))
        company["id"] = str(company["_id"])
        company.pop("_id", None)
        company["average_rating"] = company.get("average_rating") or 0.0
        return company
    except StopIteration:
        raise HTTPException(404, "Perusahaan tidak ditemukan")