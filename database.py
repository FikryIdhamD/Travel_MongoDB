# database.py
from pymongo import MongoClient
from dotenv import load_dotenv
import os

load_dotenv()
MONGODB_URI = os.getenv("MONGODB_URI")
client = MongoClient(MONGODB_URI)
db = client.travel_agency

# Koleksi
users = db.users
schedules = db.schedules
bookings = db.bookings
reviews = db.reviews 