# main.py
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from routes import user, schedule, booking, review, company
from database import client
import uvicorn

app = FastAPI(title="Travel Agency API")

app.include_router(user.router, prefix="/api/users")
app.include_router(schedule.router, prefix="/api/schedules")
app.include_router(booking.router, prefix="/api/bookings")
app.include_router(review.router, prefix="/api/reviews") 
app.include_router(company.router, prefix="/api/companies")

# Serve static files (HTML, CSS, JS)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    return FileResponse("static/index.html")

@app.on_event("shutdown")
def shutdown_db_client():
    client.close()

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)