# routes/booking.py
from fastapi import APIRouter, HTTPException, Depends
from models.booking import BookingCreate, BookingUpdate
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
        "status_review": "pending",
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
# routes/booking.py → TAMBAH ROUTE BARU DI BAWAH

# === GET: Booking per User (dengan Join) ===
@router.get("/user/{user_id}", response_model=List[dict])
async def get_user_bookings(user_id: str):
    # Pastikan user_id valid dan konversi ke ObjectId
    try:
        user_obj_id = ObjectId(user_id)
    except Exception:
        raise HTTPException(400, "user_id tidak valid (harus 24 karakter hex)")

    pipeline = [
        # 1. Filter hanya booking milik user ini
        {"$match": {"user_id": user_obj_id}},

        # Join users (opsional, karena kita sudah tahu user-nya)
        {"$lookup": {
            "from": "users",
            "localField": "user_id",
            "foreignField": "_id",
            "as": "user_info"
        }},
        # Join schedules + company
        {"$lookup": {
            "from": "schedules",
            "localField": "schedule_id",
            "foreignField": "_id",
            "as": "schedule_info"
        }},
        {"$unwind": {"path": "$user_info", "preserveNullAndEmptyArrays": True}},
        {"$unwind": {"path": "$schedule_info", "preserveNullAndEmptyArrays": True}},
        # Join company di dalam schedule_info
        {"$lookup": {
            "from": "companies",
            "localField": "schedule_info.company_id",
            "foreignField": "_id",
            "as": "schedule_info.company"
        }},
        {"$unwind": {"path": "$schedule_info.company", "preserveNullAndEmptyArrays": True}},

        {"$project": {
            # Field utama
            "_id": {"$toString": "$_id"},
            "booking_code": 1,
            "status": 1,
            "status_review": 1,
            "total_price": 1,
            "passenger_name": 1,
            "passenger_count": 1,
            "booking_date": 1,

            # User info
            "user_info._id": {"$toString": "$user_info._id"}, # Perbaikan: Gunakan user_info._id
            "user_info.name": 1,
            "user_info.email": 1,

            # Schedule info
            "schedule_info._id": {"$toString": "$schedule_info._id"}, # Tambahkan Schedule ID
            "schedule_info.origin": 1,
            "schedule_info.destination": 1,
            "schedule_info.departure_date": 1,
            "schedule_info.price": 1,
            "schedule_info.type": 1,
            "schedule_info.company.name": 1,
        }}
    ]

    result = list(bookings.aggregate(pipeline))

    if not result:
        # Opsional: Jika tidak ada booking ditemukan untuk user_id ini
        # raise HTTPException(404, "Tidak ada booking ditemukan untuk user ini") 
        # Lebih baik mengembalikan list kosong []
        pass 

    # Pastikan semua booking punya status_review (default "pending")
    for booking in result:
        if "status_review" not in booking or booking["status_review"] is None:
            booking["status_review"] = "pending"

    return result

@router.get("/", response_model=List[dict])
async def get_bookings():
    pipeline = [
        # Join users
        {"$lookup": {
            "from": "users",
            "localField": "user_id",
            "foreignField": "_id",
            "as": "user_info"
        }},
        # Join schedules + company
        {"$lookup": {
            "from": "schedules",
            "localField": "schedule_id",
            "foreignField": "_id",
            "as": "schedule_info"
        }},
        {"$unwind": {"path": "$user_info", "preserveNullAndEmptyArrays": True}},
        {"$unwind": {"path": "$schedule_info", "preserveNullAndEmptyArrays": True}},
        # Join company di dalam schedule_info (biar company name langsung ada)
        {"$lookup": {
            "from": "companies",
            "localField": "schedule_info.company_id",
            "foreignField": "_id",
            "as": "schedule_info.company"
        }},
        {"$unwind": {"path": "$schedule_info.company", "preserveNullAndEmptyArrays": True}},

        {"$project": {
            # Field utama
            "_id": {"$toString": "$_id"},                  # ← jadi string, nama field tetap "_id"
            "booking_code": 1,
            "status": 1,
            "status_review": 1,                            # ← WAJIB ADA!!!
            "total_price": 1,
            "passenger_name": 1,
            "passenger_count": 1,
            "booking_date": 1,

            # User info
            "user_info.name": 1,
            "user_info.email": 1,

            # Schedule info
            "schedule_info.origin": 1,
            "schedule_info.destination": 1,
            "schedule_info.departure_date": 1,
            "schedule_info.price": 1,
            "schedule_info.type": 1,
            "schedule_info.company.name": 1,               # ← company name langsung ada
        }}
    ]

    result = list(bookings.aggregate(pipeline))

    # Pastikan semua booking punya status_review (default "pending")
    for booking in result:
        if "status_review" not in booking or booking["status_review"] is None:
            booking["status_review"] = "pending"

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

@router.put("/{booking_id}", response_model=dict)
async def update_booking(
    booking_id: str,
    update_data: BookingUpdate,
    current_admin = Depends(get_current_user_admin)  # pastikan hanya admin
):
    if not ObjectId.is_valid(booking_id):
        raise HTTPException(400, "booking_id tidak valid")

    booking_obj_id = ObjectId(booking_id)
    booking = bookings.find_one({"_id": booking_obj_id})
    if not booking:
        raise HTTPException(404, "Booking tidak ditemukan")

    update_fields = {}

    # 1. Update nama penumpang
    if update_data.passenger_name is not None:
        if not update_data.passenger_name.strip():
            raise HTTPException(400, "Nama penumpang tidak boleh kosong")
        update_fields["passenger_name"] = update_data.passenger_name.strip()

    # 2. Update jumlah penumpang + sesuaikan stok kursi
    if update_data.passenger_count is not None:
        if update_data.passenger_count < 1:
            raise HTTPException(400, "Jumlah penumpang minimal 1")
        
        old_count = booking["passenger_count"]
        diff = update_data.passenger_count - old_count

        # Cek ketersediaan kursi jika ditambah
        if diff > 0:
            schedule = schedules.find_one({"_id": booking["schedule_id"]})
            if schedule["available_seats"] < diff:
                raise HTTPException(400, 
                    f"Kursi tidak cukup. Tersedia: {schedule['available_seats']}, dibutuhkan: {diff}")

        update_fields["passenger_count"] = update_data.passenger_count
        update_fields["total_price"] = schedule["price"] * update_data.passenger_count

        # Update stok kursi
        schedules.update_one(
            {"_id": booking["schedule_id"]},
            {"$inc": {"available_seats": -diff}}  # + jika kurang, - jika lebih
        )

    # 3. Update status booking
    if update_data.status is not None:
        allowed_status = ["pending", "confirmed", "completed", "cancelled"]
        if update_data.status not in allowed_status:
            raise HTTPException(400, f"Status tidak valid. Pilih dari: {', '.join(allowed_status)}")
        update_fields["status"] = update_data.status

        # Jika di-cancel, kembalikan stok
        if update_data.status == "cancelled" and booking["status"] != "cancelled":
            schedules.update_one(
                {"_id": booking["schedule_id"]},
                {"$inc": {"available_seats": booking["passenger_count"]}}
            )

    # 4. Update status_review (jarang dipakai manual, tapi tersedia)
    if update_data.status_review is not None:
        if update_data.status_review not in ["pending", "done"]:
            raise HTTPException(400, "status_review hanya boleh 'pending' atau 'done'")
        update_fields["status_review"] = update_data.status_review

    # Jika tidak ada yang diubah
    if not update_fields:
        raise HTTPException(400, "Tidak ada data yang dikirim untuk diupdate")

    # Terapkan update
    result = bookings.update_one(
        {"_id": booking_obj_id},
        {"$set": update_fields}
    )

    if result.modified_count == 0:
        raise HTTPException(500, "Gagal memperbarui booking")

    return {
        "message": "Booking berhasil diperbarui",
        "updated_fields": list(update_fields.keys())
    }