# seed.py → GANTI SELURUH ISI DENGAN INI

from database import users, schedules, companies, bookings, reviews
from passlib.context import CryptContext
from datetime import datetime, timedelta
from bson import ObjectId
import random

pwd_context = CryptContext(schemes=["bcrypt"])

# === HAPUS SEMUA DATA LAMA ===
users.delete_many({})
companies.delete_many({})
schedules.delete_many({})
bookings.delete_many({})
reviews.delete_many({})

print("Semua data lama dihapus!\n")

# ================== 1. ADMIN & USER BIASA ==================
users.insert_many([
    {
        "name": "Admin TravelGo",
        "email": "admin@travelgo.com",
        "password": pwd_context.hash("admin123"),
        "role": "admin"
    },
    {
        "name": "Budi Santoso",
        "email": "budi@gmail.com",
        "password": pwd_context.hash("123456"),
        "role": "customer"
    },
    {
        "name": "Siti Nurhaliza",
        "email": "siti@gmail.com",
        "password": pwd_context.hash("123456"),
        "role": "customer"
    }
])
print("Admin + 2 user dibuat")

# ================== 2. PERUSAHAAN ==================
company_docs = [
    {"name": "Sinar Jaya",       "type": "bus",    "description": "Travel premium Jakarta-Bandung", "phone": "021-888888"},
    {"name": "Primajasa",        "type": "bus",    "description": "Jakarta-Bandung-Cirebon",         "phone": "021-777777"},
    {"name": "Garuda Indonesia", "type": "flight", "description": "Maskapai nasional terbaik",      "phone": "0804-1807"},
    {"name": "Kereta Api Indonesia", "type": "train", "description": "KA Eksekutif & Ekonomi",         "phone": "121"}
]

inserted_companies = companies.insert_many(company_docs)
company_ids = inserted_companies.inserted_ids

# Buat mapping nama → ObjectId
company_map = {doc["name"]: obj_id for doc, obj_id in zip(company_docs, company_ids)}

print(f"4 perusahaan dibuat:")
for name in company_map:
    print(f"  → {name}: {company_map[name]}")

# ================== 3. JADWAL (Schedules) ==================
now = datetime.utcnow()
schedules_data = [
    # Sinar Jaya (bus)
    {"company_id": company_map["Sinar Jaya"], "type": "bus", "origin": "Jakarta", "destination": "Bandung", "departure_date": now + timedelta(days=1, hours=7), "price": 150000, "available_seats": 40},
    {"company_id": company_map["Sinar Jaya"], "type": "bus", "origin": "Bandung", "destination": "Jakarta", "departure_date": now + timedelta(days=2, hours=14), "price": 150000, "available_seats": 38},

    # Primajasa (bus)
    {"company_id": company_map["Primajasa"], "type": "bus", "origin": "Jakarta", "destination": "Cirebon", "departure_date": now + timedelta(days=3, hours=9), "price": 180000, "available_seats": 35},

    # Garuda (flight)
    {"company_id": company_map["Garuda Indonesia"], "type": "flight", "origin": "Jakarta", "destination": "Bali", "departure_date": now + timedelta(days=5, hours=8), "price": 1250000, "available_seats": 120},

    # KAI (train)
    {"company_id": company_map["Kereta Api Indonesia"], "type": "train", "origin": "Jakarta", "destination": "Surabaya", "departure_date": now + timedelta(days=4, hours=10), "price": 450000, "available_seats": 200},
]

inserted_schedules = schedules.insert_many(schedules_data)
schedule_ids = inserted_schedules.inserted_ids

print(f"{len(schedule_ids)} jadwal dibuat\n")

# ================== 4. BOOKING (Beberapa status berbeda) ==================
budi = users.find_one({"email": "budi@gmail.com"})
siti = users.find_one({"email": "siti@gmail.com"})

bookings_data = [
    {
        "user_id": budi["_id"],
        "schedule_id": schedule_ids[0],  # Sinar Jaya Jakarta-Bandung
        "passenger_name": "Budi Santoso",
        "passenger_count": 2,
        "total_price": 300000,
        "status": "completed",           # sudah selesai → bisa direview
        "booking_code": "TRAV-20251119-ABC123",
        "booking_date": datetime.utcnow() - timedelta(days=5)
    },
    {
        "user_id": budi["_id"],
        "schedule_id": schedule_ids[1],  # Sinar Jaya Bandung-Jakarta
        "passenger_name": "Budi Santoso",
        "passenger_count": 1,
        "total_price": 150000,
        "status": "pending",
        "booking_code": "TRAV-20251120-DEF456",
        "booking_date": datetime.utcnow()
    },
    {
        "user_id": siti["_id"],
        "schedule_id": schedule_ids[3],  # Garuda ke Bali
        "passenger_name": "Siti Nurhaliza",
        "passenger_count": 1,
        "total_price": 1250000,
        "status": "completed",
        "booking_code": "TRAV-20251121-GHI789",
        "booking_date": datetime.utcnow() - timedelta(days=10)
    }
]

inserted_bookings = bookings.insert_many(bookings_data)
booking_ids = inserted_bookings.inserted_ids

print(f"{len(booking_ids)} booking dibuat (ada yang completed, ada yang pending)\n")

# ================== 5. REVIEW (Hanya untuk booking completed) ==================
reviews_data = [
    {
        "booking_id": booking_ids[0],
        "company_id": company_map["Sinar Jaya"],
        "user_id": budi["_id"],
        "rating": 5,
        "comment": "Sopir ramah, tepat waktu, recommended!",
        "created_at": datetime.utcnow() - timedelta(days=4)
    },
    {
        "booking_id": booking_ids[2],
        "company_id": company_map["Garuda Indonesia"],
        "user_id": siti["_id"],
        "rating": 4,
        "comment": "Pelayanan bagus, tapi delay 30 menit",
        "created_at": datetime.utcnow() - timedelta(days=9)
    }
]

reviews.insert_many(reviews_data)
print("2 review dibuat (Sinar Jaya = 5.0, Garuda = 4.0)\n")

# ================== UPDATE CACHED RATING DI COMPANIES ==================
def update_company_rating(company_id):
    pipeline = [
        {"$match": {"company_id": company_id}},
        {"$group": {"_id": None, "avg": {"$avg": "$rating"}, "total": {"$sum": 1}}}
    ]
    result = list(reviews.aggregate(pipeline))
    if result:
        avg = round(result[0]["avg"], 1)
        total = result[0]["total"]
        companies.update_one(
            {"_id": company_id},
            {"$set": {"cached_rating": avg, "cached_total_reviews": total}}
        )

update_company_rating(company_map["Sinar Jaya"])
update_company_rating(company_map["Garuda Indonesia"])

print("Rating perusahaan sudah di-cache!")
print("\nSEED SELESAI! SEMUA DATA SIAP UNTUK DEMO!")
print("Login user: budi@gmail.com / 123456")
print("Login admin: admin@travelgo.com / admin123")