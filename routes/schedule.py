# routes/schedule.py
from fastapi import APIRouter, HTTPException, Query, Depends
from models.schedule import ScheduleCreate
from database import schedules, bookings
from bson import ObjectId
from typing import List, Optional
from datetime import datetime
import pymongo
from utils.auth import get_current_user_admin

router = APIRouter()

@router.post("/", response_model=dict)
async def create_schedule(
    schedule_in: ScheduleCreate,
    current_admin = Depends(get_current_user_admin)   # ADMIN ONLY
):
    if not ObjectId.is_valid(schedule_in.company_id):
        raise HTTPException(400, "company_id tidak valid")
    
    # Cek perusahaan ada
    from database import companies
    if not companies.find_one({"_id": ObjectId(schedule_in.company_id)}):
        raise HTTPException(404, "Perusahaan tidak ditemukan")

    doc = schedule_in.dict()
    doc["company_id"] = ObjectId(schedule_in.company_id)
    
    result = schedules.insert_one(doc)
    return {"id": str(result.inserted_id), "message": "Jadwal dibuat"}

# routes/schedule.py → GANTI SELURUH @router.get("/") dengan ini:

@router.get("/", response_model=List[dict])
async def get_schedules(
    origin: Optional[str] = Query(None),
    destination: Optional[str] = Query(None),
    type: Optional[str] = Query(None),
    departure_date: Optional[str] = Query(None),
    price_min: Optional[int] = Query(None),
    price_max: Optional[int] = Query(None),
    sort_by: Optional[str] = Query("departure_date", regex="^(departure_date|price)$"),
    order: Optional[str] = Query("asc", regex="^(asc|desc)$")
):
    # 1. Bangun filter (sama persis seperti sebelumnya)
    query = {}
    if origin:
        query["origin"] = {"$regex": origin, "$options": "i"}
    if destination:
        query["destination"] = {"$regex": destination, "$options": "i"}
    if type:
        query["type"] = {"$regex": f"^{type}$", "$options": "i"}  # lebih ketat
    if departure_date:
        try:
            date_obj = datetime.strptime(departure_date, "%Y-%m-%d")
            start = date_obj.replace(hour=0, minute=0, second=0)
            end = date_obj.replace(hour=23, minute=59, second=59)
            query["departure_date"] = {"$gte": start, "$lte": end}
        except ValueError:
            raise HTTPException(400, "Format departure_date: YYYY-MM-DD")
    if price_min is not None:
        query["price"] = {**query.get("price", {}), "$gte": price_min}
    if price_max is not None:
        query["price"] = {**query.get("price", {}), "$lte": price_max}

    # 2. Sort
    sort_order = pymongo.ASCENDING if order == "asc" else pymongo.DESCENDING
    sort_field = sort_by if sort_by == "price" else "departure_date"

    # 3. AGGREGATION PIPELINE → JOIN dengan companies
    pipeline = [
        {"$match": query},
        {"$sort": {sort_field: sort_order}},

        # Join dengan tabel companies
        {
            "$lookup": {
                "from": "companies",
                "localField": "company_id",
                "foreignField": "_id",
                "as": "company_info"
            }
        },
        {"$unwind": {"path": "$company_info", "preserveNullAndEmptyArrays": True}},

        # Pilih field yang mau ditampilkan
        {
            "$project": {
                "id": {"$toString": "$_id"},
                "_id": 0,
                "type": 1,
                "origin": 1,
                "destination": 1,
                "departure_date": 1,
                "arrival_date": 1,
                "price": 1,
                "available_seats": 1,
                "company": {
                    "id": {"$toString": "$company_info._id"},
                    "name": "$company_info.name",
                    "type": "$company_info.type"
                }
            }
        }
    ]

    result = list(schedules.aggregate(pipeline))

    # Jika company_info kosong (jadwal lama), beri nilai default
    for sched in result:
        if not sched.get("company"):
            sched["company"] = {"id": None, "name": "Unknown Operator", "type": "unknown"}

    return result

@router.get("/popular")
async def popular_schedules():
    pipeline = [
        {
            "$group": {
                "_id": "$schedule_id",
                "booking_count": {"$sum": 1},
                "total_revenue": {"$sum": "$total_price"}
            }
        },
        {"$sort": {"booking_count": -1}},
        {"$limit": 5},
        {
            "$lookup": {
                "from": "schedules",
                "localField": "_id",
                "foreignField": "_id",
                "as": "schedule"
            }
        },
        {"$unwind": "$schedule"},
        {
            "$project": {
                "schedule.origin": 1,
                "schedule.destination": 1,
                "schedule.type": 1,
                "booking_count": 1,
                "total_revenue": 1
            }
        }
    ]
    raw_result = list(bookings.aggregate(pipeline))

    def convert_obj_id(obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        if isinstance(obj, dict):
            return {k: convert_obj_id(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [convert_obj_id(i) for i in obj]
        return obj
    return convert_obj_id(raw_result)

@router.get("/{id}")
async def get_schedule(id: str):
    if not ObjectId.is_valid(id):
        raise HTTPException(400, f"ID tidak valid: {id}")
    sched = schedules.find_one({"_id": ObjectId(id)})
    if not sched:
        raise HTTPException(404, "Jadwal tidak ditemukan")
    sched["id"] = str(sched["_id"])
    del sched["_id"]
    return sched

@router.put("/{id}")
async def update_schedule(
    id: str,
    schedule_in: ScheduleCreate,
    current_admin = Depends(get_current_user_admin)
):
    if not ObjectId.is_valid(id) or not ObjectId.is_valid(schedule_in.company_id):
        raise HTTPException(400, "ID tidak valid")
    
    update_data = schedule_in.dict()
    update_data["company_id"] = ObjectId(schedule_in.company_id)
    
    result = schedules.update_one(
        {"_id": ObjectId(id)},
        {"$set": update_data}
    )
    if result.modified_count == 0:
        raise HTTPException(404, "Jadwal tidak ditemukan")
    return {"message": "Jadwal diperbarui"}

@router.delete("/{id}")
async def delete_schedule(
    id: str,
    current_admin = Depends(get_current_user_admin)
):
    # Cek apakah ada booking aktif
    if bookings.find_one({"schedule_id": ObjectId(id), "status": {"$ne": "cancelled"}}):
        raise HTTPException(400, "Jadwal masih punya booking aktif")
    
    schedules.delete_one({"_id": ObjectId(id)})
    return {"message": "Jadwal dihapus"}

@router.get("/{id}", response_model=dict)
async def get_schedule(id: str):
    if not ObjectId.is_valid(id):
        raise HTTPException(400, "ID tidak valid")
    pipeline = [
        {"$match": {"_id": ObjectId(id)}},
        {"$lookup": {
            "from": "companies",
            "localField": "company_id",
            "foreignField": "_id",
            "as": "company_info"
        }},
        {"$unwind": {"path": "$company_info", "preserveNullAndEmptyArrays": True}},
        {"$project": {
            "id": {"$toString": "$_id"},
            "_id": 0,
            "type": 1,
            "origin": 1,
            "destination": 1,
            "departure_date": 1,
            "arrival_date": 1,
            "price": 1,
            "available_seats": 1,
            "company": {
                "id": {"$toString": "$company_info._id"},
                "name": "$company_info.name",
                "type": "$company_info.type"
            }
        }}
    ]
    try:
        sched = next(schedules.aggregate(pipeline))
        if not sched.get("company"):
            sched["company"] = {"id": None, "name": "Unknown", "type": "unknown"}
        return sched
    except StopIteration:
        raise HTTPException(404, "Jadwal tidak ditemukan")