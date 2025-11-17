# routes/schedule.py
from fastapi import APIRouter, HTTPException, Query
from models.schedule import ScheduleCreate
from database import schedules, bookings
from bson import ObjectId
from typing import List, Optional
from datetime import datetime
import pymongo

router = APIRouter()

@router.post("/")
async def create_schedule(schedule_in: ScheduleCreate):
    result = schedules.insert_one(schedule_in.dict())
    return {"id": str(result.inserted_id)}

@router.get("/")
async def get_schedules(
    origin: Optional[str] = Query(None),
    destination: Optional[str] = Query(None),
    type: Optional[str] = Query(None),
    departure_date: Optional[str] = Query(None),  # format: YYYY-MM-DD
    price_min: Optional[int] = Query(None),
    price_max: Optional[int] = Query(None),
    sort_by: Optional[str] = Query("departure_date", regex="^(departure_date|price)$"),
    order: Optional[str] = Query("asc", regex="^(asc|desc)$")
):
    # Bangun filter
    query = {}
    if origin:
        query["origin"] = {"$regex": origin, "$options": "i"}
    if destination:
        query["destination"] = {"$regex": destination, "$options": "i"}
    if type:
        query["type"] = type.lower()
    if departure_date:
        try:
            date_obj = datetime.strptime(departure_date, "%Y-%m-%d")
            query["departure_date"] = {
                "$gte": date_obj.isoformat(),
                "$lt": (date_obj.replace(hour=23, minute=59, second=59)).isoformat()
            }
        except ValueError:
            raise HTTPException(400, "Format departure_date: YYYY-MM-DD")
    if price_min is not None:
        query["price"] = {**query.get("price", {}), "$gte": price_min}
    if price_max is not None:
        query["price"] = {**query.get("price", {}), "$lte": price_max}

    # Sort
    sort_order = pymongo.ASCENDING if order == "asc" else pymongo.DESCENDING
    sort_field = "departure_date" if sort_by == "departure_date" else "price"

    sched_list = list(schedules.find(query).sort(sort_field, sort_order))
    for s in sched_list:
        s["id"] = str(s["_id"])
        del s["_id"]
    return sched_list

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
async def update_schedule(id: str, schedule_in: ScheduleCreate):
    result = schedules.update_one({"_id": ObjectId(id)}, {"$set": schedule_in.dict()})
    if result.modified_count == 0:
        raise HTTPException(404, "Gagal update")
    return {"msg": "Updated"}

@router.delete("/{id}")
async def delete_schedule(id: str):
    result = schedules.delete_one({"_id": ObjectId(id)})
    if result.deleted_count == 0:
        raise HTTPException(404, "Tidak ditemukan")
    return {"msg": "Dihapus"}