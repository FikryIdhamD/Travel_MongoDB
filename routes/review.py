# routes/review.py (GANTI SELURUH FILE)

from fastapi import APIRouter, HTTPException, Depends
from models.review import ReviewCreate, ReviewOut
from database import reviews, bookings, schedules, companies, users
from bson import ObjectId
from datetime import datetime
from typing import List

router = APIRouter()

@router.post("/", response_model=ReviewOut)
async def create_review(review_in: ReviewCreate):
    # 1. Validasi booking_id
    if not ObjectId.is_valid(review_in.booking_id):
        raise HTTPException(400, "booking_id tidak valid")
    
    booking = bookings.find_one({"_id": ObjectId(review_in.booking_id)})
    if not booking:
        raise HTTPException(404, "Booking tidak ditemukan")

    # 2. HANYA jika status = completed
    if booking.get("status") != "completed":
        raise HTTPException(403, "Hanya booking yang sudah selesai (completed) yang bisa direview")

    # 3. Cek sudah pernah review belum (1 booking = 1 review)
    if reviews.find_one({"booking_id": ObjectId(review_in.booking_id)}):
        raise HTTPException(400, "Anda sudah memberikan ulasan untuk booking ini")

    # 4. Ambil company_id dari schedule
    schedule = schedules.find_one({"_id": booking["schedule_id"]})
    if not schedule or "company_id" not in schedule:
        raise HTTPException(400, "Jadwal tidak valid")
    
    company_id = schedule["company_id"]
    company = companies.find_one({"_id": company_id})
    if not company:
        raise HTTPException(404, "Perusahaan tidak ditemukan")

    # 5. Ambil user
    user = users.find_one({"_id": booking["user_id"]})
    user_name = user["name"] if user else "Anonymous"

    # 6. Simpan review
    review_doc = {
        "booking_id": ObjectId(review_in.booking_id),
        "company_id": company_id,
        "user_id": booking["user_id"],
        "rating": review_in.rating,
        "comment": review_in.comment,
        "created_at": datetime.utcnow()
    }
    result = reviews.insert_one(review_doc)
    # UPDATE RATING CACHED DI COLLECTION COMPANIES
    avg_pipeline = [
        {"$match": {"company_id": company_id}},
        {"$group": {
            "_id": None,
            "avg_rating": {"$avg": "$rating"},
            "total_reviews": {"$sum": 1}
        }}
    ]
    avg_result = list(reviews.aggregate(avg_pipeline))

    if avg_result:
        avg_rating = round(avg_result[0]["avg_rating"], 1)
        total_reviews = avg_result[0]["total_reviews"]
        companies.update_one(
            {"_id": company_id},
            {"$set": {
                "cached_rating": avg_rating,
                "cached_total_reviews": total_reviews
            }}
        )
    return ReviewOut(
        id=str(result.inserted_id),
        company_id=str(company_id),
        company_name=company["name"],
        user_name=user_name,
        rating=review_in.rating,
        comment=review_in.comment,
        created_at=review_doc["created_at"]
    )

# === GET Semua Review Perusahaan ===
@router.get("/company/{company_id}", response_model=List[ReviewOut])
async def get_reviews_by_company(company_id: str):
    if not ObjectId.is_valid(company_id):
        raise HTTPException(400, "company_id tidak valid")

    pipeline = [
        {"$match": {"company_id": ObjectId(company_id)}},
        {"$lookup": {
            "from": "users",
            "localField": "user_id",
            "foreignField": "_id",
            "as": "user_info"
        }},
        {"$lookup": {
            "from": "companies",
            "localField": "company_id",
            "foreignField": "_id",
            "as": "company_info"
        }},
        {"$unwind": {"path": "$user_info", "preserveNullAndEmptyArrays": True}},
        {"$unwind": {"path": "$company_info", "preserveNullAndEmptyArrays": True}},
        {
            "$project": {
                "id": {"$toString": "$_id"},                    # BARU: konversi _id → id
                "_id": 0,                                       # sembunyikan _id asli
                "company_id": {"$toString": "$company_id"},
                "company_name": "$company_info.name",
                "user_name": "$user_info.name",
                "rating": 1,
                "comment": 1,
                "created_at": 1
            }
        },
        {"$sort": {"created_at": -1}}
    ]

    result = list(reviews.aggregate(pipeline))

    # Jika ada user/company tidak ditemukan, beri default
    for item in result:
        item["user_name"] = item.get("user_name") or "Anonymous"
        item["company_name"] = item.get("company_name") or "Unknown Company"

    return result