# routes/review.py
from fastapi import APIRouter, HTTPException
from models.review import ReviewCreate, ReviewOut
from database import reviews, bookings, users
from bson import ObjectId
from datetime import datetime

router = APIRouter()

@router.post("/", response_model=ReviewOut)
async def create_review(review_in: ReviewCreate):
    # Validasi booking_id
    try:
        booking_obj_id = ObjectId(review_in.booking_id)
    except:
        raise HTTPException(400, "booking_id tidak valid")

    booking = bookings.find_one({"_id": booking_obj_id})
    if not booking:
        raise HTTPException(404, "Booking tidak ditemukan")
    if booking["status"] != "confirmed":
        raise HTTPException(400, "Hanya booking confirmed yang bisa direview")

    # Cek sudah review?
    if reviews.find_one({"booking_id": booking_obj_id}):
        raise HTTPException(400, "Booking ini sudah direview")

    # Ambil user
    user = users.find_one({"_id": booking["user_id"]})
    if not user:
        raise HTTPException(404, "User tidak ditemukan")

    # Simpan review
    review_doc = {
        "booking_id": booking_obj_id,
        "user_id": booking["user_id"],
        "rating": review_in.rating,
        "comment": review_in.comment,
        "created_at": datetime.utcnow()
    }
    result = reviews.insert_one(review_doc)

    return ReviewOut(
        booking_id=str(booking_obj_id),
        user_name=user["name"],
        rating=review_in.rating,
        comment=review_in.comment,
        created_at=review_doc["created_at"].isoformat()
    )

@router.get("/schedule/{schedule_id}")
async def get_reviews_by_schedule(schedule_id: str):
    if not ObjectId.is_valid(schedule_id):
        raise HTTPException(400, "schedule_id tidak valid")

    pipeline = [
        {"$match": {"schedule_id": ObjectId(schedule_id)}},
        {"$lookup": {"from": "reviews", "localField": "_id", "foreignField": "booking_id", "as": "review"}},
        {"$unwind": {"path": "$review", "preserveNullAndEmptyArrays": True}},
        {"$lookup": {"from": "users", "localField": "user_id", "foreignField": "_id", "as": "user"}},
        {"$unwind": {"path": "$user", "preserveNullAndEmptyArrays": True}},
        {
            "$project": {
                "user_name": "$user.name",
                "rating": "$review.rating",
                "comment": "$review.comment",
                "created_at": "$review.created_at"
            }
        }
    ]
    results = list(bookings.aggregate(pipeline))
    return results
