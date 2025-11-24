# routes/review.py → GANTI SELURUH FILE DENGAN INI

from fastapi import APIRouter, HTTPException, Depends
from models.review import ReviewCreate, ReviewOut
from database import reviews, bookings, schedules, companies, users
from bson import ObjectId
from datetime import datetime
from typing import List
from utils.auth import get_current_user_admin

router = APIRouter()

# === CREATE REVIEW (untuk user biasa) ===
@router.post("/", response_model=ReviewOut)
async def create_review(review_in: ReviewCreate):
    if not ObjectId.is_valid(review_in.booking_id):
        raise HTTPException(400, "booking_id tidak valid")
    
    booking = bookings.find_one({"_id": ObjectId(review_in.booking_id)})
    if not booking:
        raise HTTPException(404, "Booking tidak ditemukan")
    if booking.get("status") != "completed":
        raise HTTPException(403, "Hanya booking completed yang bisa direview")
    if reviews.find_one({"booking_id": ObjectId(review_in.booking_id)}):
        raise HTTPException(400, "Sudah pernah mereview booking ini")

    schedule = schedules.find_one({"_id": booking["schedule_id"]})
    company = companies.find_one({"_id": schedule["company_id"]})
    user = users.find_one({"_id": booking["user_id"]})

    review_doc = {
        "booking_id": ObjectId(review_in.booking_id),
        "company_id": schedule["company_id"],
        "user_id": booking["user_id"],
        "rating": review_in.rating,
        "comment": review_in.comment,
        "created_at": datetime.utcnow()
    }
    result = reviews.insert_one(review_doc)

    # Update status_review di booking
    bookings.update_one({"_id": ObjectId(review_in.booking_id)}, {"$set": {"status_review": "done"}})

    # Update cached rating di company
    pipeline = [
        {"$match": {"company_id": schedule["company_id"]}},
        {"$group": {"_id": None, "avg": {"$avg": "$rating"}, "count": {"$sum": 1}}}
    ]
    agg = list(reviews.aggregate(pipeline))
    if agg:
        companies.update_one(
            {"_id": schedule["company_id"]},
            {"$set": {"cached_rating": round(agg[0]["avg"], 1), "cached_total_reviews": agg[0]["count"]}}
        )

    return ReviewOut(
        id=str(result.inserted_id),
        company_id=str(schedule["company_id"]),
        company_name=company["name"],
        user_name=user.get("name", "Anonymous"),
        rating=review_in.rating,
        comment=review_in.comment,
        created_at=review_doc["created_at"]
    )

# === GET ALL REVIEWS (UNTUK ADMIN PANEL) → INI YANG DIPAKE ADMIN ===
@router.get("/", response_model=List[ReviewOut])
async def get_all_reviews(current_admin=Depends(get_current_user_admin)):
    pipeline = [
        {"$lookup": {"from": "users", "localField": "user_id", "foreignField": "_id", "as": "user_info"}},
        {"$lookup": {"from": "companies", "localField": "company_id", "foreignField": "_id", "as": "company_info"}},
        {"$unwind": {"path": "$user_info", "preserveNullAndEmptyArrays": True}},
        {"$unwind": {"path": "$company_info", "preserveNullAndEmptyArrays": True}},
        {"$project": {
            "id": {"$toString": "$_id"},
            "company_id": {"$toString": "$company_id"},
            "company_name": "$company_info.name",
            "user_name": {"$ifNull": ["$user_info.name", "Anonymous"]},
            "rating": 1,
            "comment": 1,
            "created_at": 1
        }},
        {"$sort": {"created_at": -1}}
    ]
    result = list(reviews.aggregate(pipeline))
    return result

# === GET REVIEWS BY COMPANY (untuk halaman publik perusahaan) ===
@router.get("/company/{company_id}", response_model=List[ReviewOut])
async def get_reviews_by_company(company_id: str):
    if not ObjectId.is_valid(company_id):
        raise HTTPException(400, "company_id tidak valid")

    pipeline = [
        {"$match": {"company_id": ObjectId(company_id)}},
        {"$lookup": {"from": "users", "localField": "user_id", "foreignField": "_id", "as": "user_info"}},
        {"$lookup": {"from": "companies", "localField": "company_id", "foreignField": "_id", "as": "company_info"}},
        {"$unwind": {"path": "$user_info", "preserveNullAndEmptyArrays": True}},
        {"$unwind": {"path": "$company_info", "preserveNullAndEmptyArrays": True}},
        {"$project": {
            "id": {"$toString": "$_id"},
            "company_id": {"$toString": "$company_id"},
            "company_name": "$company_info.name",
            "user_name": {"$ifNull": ["$user_info.name", "Anonymous"]},
            "rating": 1,
            "comment": 1,
            "created_at": 1
        }},
        {"$sort": {"created_at": -1}}
    ]
    result = list(reviews.aggregate(pipeline))
    return result

# === UPDATE REVIEW (Admin only) ===
@router.put("/{review_id}", response_model=ReviewOut)
async def update_review(review_id: str, review_in: ReviewCreate, current_admin=Depends(get_current_user_admin)):
    if not ObjectId.is_valid(review_id):
        raise HTTPException(400, "ID tidak valid")
    
    update_data = review_in.dict(exclude_unset=True)
    result = reviews.update_one(
        {"_id": ObjectId(review_id)},
        {"$set": update_data}
    )
    if result.modified_count == 0:
        raise HTTPException(404, "Review tidak ditemukan")

    # Refresh cached rating
    updated = reviews.find_one({"_id": ObjectId(review_id)})
    pipeline = [{"$match": {"company_id": updated["company_id"]}}, {"$group": {"_id": None, "avg": {"$avg": "$rating"}, "count": {"$sum": 1}}}]
    agg = list(reviews.aggregate(pipeline))
    if agg:
        companies.update_one(
            {"_id": updated["company_id"]},
            {"$set": {"cached_rating": round(agg[0]["avg"], 1), "cached_total_reviews": agg[0]["count"]}}
        )

    # Return dalam format ReviewOut
    company = companies.find_one({"_id": updated["company_id"]})
    user = users.find_one({"_id": updated["user_id"]})
    return ReviewOut(
        id=review_id,
        company_id=str(updated["company_id"]),
        company_name=company["name"],
        user_name=user.get("name", "Anonymous"),
        rating=updated["rating"],
        comment=updated.get("comment"),
        created_at=updated["created_at"]
    )

# === DELETE REVIEW (Admin only) ===
@router.delete("/{review_id}")
async def delete_review(review_id: str, current_admin=Depends(get_current_user_admin)):
    if not ObjectId.is_valid(review_id):
        raise HTTPException(400, "ID tidak valid")
    
    review = reviews.find_one({"_id": ObjectId(review_id)})
    if not review:
        raise HTTPException(404, "Review tidak ditemukan")

    # Update status_review booking jadi pending lagi
    bookings.update_one(
        {"_id": review["booking_id"]},
        {"$set": {"status_review": "pending"}}
    )

    reviews.delete_one({"_id": ObjectId(review_id)})

    # Refresh cached rating
    pipeline = [{"$match": {"company_id": review["company_id"]}}, {"$group": {"_id": None, "avg": {"$avg": "$rating"}, "count": {"$sum": 1}}}]
    agg = list(reviews.aggregate(pipeline))
    if agg:
        companies.update_one(
            {"_id": review["company_id"]},
            {"$set": {"cached_rating": round(agg[0]["avg"], 1), "cached_total_reviews": agg[0]["count"]}}
        )
    else:
        companies.update_one(
            {"_id": review["company_id"]},
            {"$unset": {"cached_rating": "", "cached_total_reviews": ""}}
        )

    return {"message": "Review dihapus"}