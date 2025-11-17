# seed.py
from database import users, schedules
from passlib.context import CryptContext
pwd_context = CryptContext(schemes=["bcrypt"])

# Hapus dulu
users.delete_many({})
schedules.delete_many({})

# User
users.insert_one({
    "name": "Admin",
    "email": "admin@travel.com",
    "password": pwd_context.hash("admin123"),
    "role": "admin"
})

# Jadwal
schedules.insert_many([
    {
        "type": "train",
        "origin": "Jakarta",
        "destination": "Bandung",
        "departure_date": "2025-12-20T07:00:00",
        "price": 150000,
        "available_seats": 40,
        "operator": "KAI"
    },
    {
        "type": "flight",
        "origin": "Jakarta",
        "destination": "Bali",
        "departure_date": "2025-12-25T09:00:00",
        "price": 1200000,
        "available_seats": 100,
        "operator": "Garuda"
    }
])

print("Seed selesai!")