# routes/booking.py
from fastapi import APIRouter, HTTPException, Depends
from models.booking import BookingCreate
from database import bookings, schedules, users
from bson import ObjectId
from datetime import datetime
from typing import List

from utils.auth import get_current_user_admin

router = APIRouter()

# === POST: Buat Booking ===
@router.post("/")
async def create_booking(booking_in: BookingCreate):
    # Konversi ID ke ObjectId
    try:
        user_obj_id = ObjectId(booking_in.user_id)
        schedule_obj_id = ObjectId(booking_in.schedule_id)
    except Exception:
        raise HTTPException(400, "user_id atau schedule_id tidak valid (harus 24 karakter hex)")

    # Cek jadwal
    sched = schedules.find_one({"_id": schedule_obj_id})
    if not sched:
        raise HTTPException(404, f"Jadwal dengan ID {booking_in.schedule_id} tidak ditemukan")
    if sched["available_seats"] < booking_in.passenger_count:
        raise HTTPException(400, f"Kursi tidak cukup. Tersedia: {sched['available_seats']}, Diminta: {booking_in.passenger_count}")

    # Hitung total
    total = sched["price"] * booking_in.passenger_count
    code = f"TRAV-{datetime.now().strftime('%Y%m%d')}-{str(ObjectId())[-6:]}".upper()

    # Simpan booking
    booking_doc = {
        "user_id": user_obj_id,
        "schedule_id": schedule_obj_id,
        "passenger_name": booking_in.passenger_name,
        "passenger_count": booking_in.passenger_count,
        "total_price": total,
        "status": "pending",
        "booking_code": code,
        "booking_date": datetime.utcnow()
    }
    result = bookings.insert_one(booking_doc)

    # Kurangi stok
    schedules.update_one(
        {"_id": schedule_obj_id},
        {"$inc": {"available_seats": -booking_in.passenger_count}}
    )

    return {
        "id": str(result.inserted_id),
        "booking_code": code,
        "message": "Booking berhasil!"
    }


# === GET: Booking dengan Join (User + Schedule) ===
@router.get("/")
async def get_bookings():
    pipeline = [
        # Join dengan users
        {
            "$lookup": {
                "from": "users",
                "localField": "user_id",
                "foreignField": "_id",
                "as": "user_info"
            }
        },
        # Join dengan schedules
        {
            "$lookup": {
                "from": "schedules",
                "localField": "schedule_id",
                "foreignField": "_id",
                "as": "schedule_info"
            }
        },
        # Unwind (opsional, tapi lebih rapi)
        {"$unwind": {"path": "$user_info", "preserveNullAndEmptyArrays": True}},
        {"$unwind": {"path": "$schedule_info", "preserveNullAndEmptyArrays": True}},
        # Pilih field yang ditampilkan
        {
            "$project": {
                "_id": {"$toString": "$_id"},
                "booking_code": 1,
                "status": 1,
                "total_price": 1,
                "passenger_name": 1,
                "passenger_count": 1,
                "booking_date": 1,
                "user_info": {
                    "name": 1,
                    "email": 1
                },
                "schedule_info": {
                    "origin": 1,
                    "destination": 1,
                    "departure_date": 1,
                    "price": 1,
                    "type": 1
                }
            }
        }
    ]

    raw_result = list(bookings.aggregate(pipeline))

    # Konversi ObjectId ke string (jika masih ada)
    def convert_obj_id(obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        if isinstance(obj, dict):
            return {k: convert_obj_id(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [convert_obj_id(i) for i in obj]
        return obj

    return convert_obj_id(raw_result)


# === GET: Booking Mentah (untuk debug) ===
@router.get("/raw")
async def get_bookings_raw():
    raw = list(bookings.find())
    result = []
    for b in raw:
        b["id"] = str(b["_id"])
        b["user_id"] = str(b["user_id"])
        b["schedule_id"] = str(b["schedule_id"])
        del b["_id"]
        result.append(b)
    return result


# === PUT: Update Status Booking (opsional) ===
@router.put("/{booking_id}/status")
async def update_booking_status(booking_id: str, status: str):
    if status not in ["pending", "confirmed", "cancelled"]:
        raise HTTPException(400, "Status tidak valid")

    result = bookings.update_one(
        {"_id": ObjectId(booking_id)},
        {"$set": {"status": status}}
    )
    if result.modified_count == 0:
        raise HTTPException(404, "Booking tidak ditemukan")
    return {"message": f"Status diubah menjadi {status}"}


# === DELETE: Cancel Booking + Kembalikan Stok ===
@router.delete("/{booking_id}")
async def cancel_booking(booking_id: str):
    booking = bookings.find_one({"_id": ObjectId(booking_id)})
    if not booking:
        raise HTTPException(404, "Booking tidak ditemukan")

    # Kembalikan stok
    schedules.update_one(
        {"_id": booking["schedule_id"]},
        {"$inc": {"available_seats": booking["passenger_count"]}}
    )

    bookings.delete_one({"_id": ObjectId(booking_id)})
    return {"message": "Booking dibatalkan dan stok dikembalikan"}

# routes/booking.py → TAMBAH ROUTE BARU DI BAWAH

@router.put("/{booking_id}/complete")
async def complete_booking(
    booking_id: str,
    current_admin = Depends(get_current_user_admin)  # dari utils/auth.py
):
    if not ObjectId.is_valid(booking_id):
        raise HTTPException(400, "booking_id tidak valid")

    result = bookings.update_one(
        {"_id": ObjectId(booking_id)},
        {"$set": {"status": "completed", "completed_at": datetime.utcnow()}}
    )

    if result.modified_count == 0:
        raise HTTPException(404, "Booking tidak ditemukan atau gagal diupdate")

    return {"message": "Booking selesai! User sekarang bisa memberikan ulasan."}
