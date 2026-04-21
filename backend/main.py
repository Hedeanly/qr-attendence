"""
main.py — Entry point for the QR Attendance backend API

to start the server:
  cd backend
  venv/Scripts/activate
  uvicorn main:app --reload

Then visit:
  http://localhost:8000/docs  ← Interactive API explorer
  http://localhost:8000       ← Health check
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import engine, Base, SessionLocal
import models



app = FastAPI(
    title="QR Attendance API",
    description="Secure QR-Based Attendance Verification System",
    version="1.0.0"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



Base.metadata.create_all(bind=engine)


def seed_admin():
    from routers.auth import hash_password
    from dotenv import load_dotenv
    import os
    load_dotenv()

    db = SessionLocal()

    if db.query(models.User).count() > 0:
        db.close()
        return

    print("Seeding default admin user...")

    admin = models.User(
        username=os.getenv("ADMIN_USERNAME", "admin"),
        email=os.getenv("ADMIN_EMAIL", "admin@qrattendance.com"),
        hashed_password=hash_password(os.getenv("ADMIN_PASSWORD", "admin123")),
        role=models.UserRole.admin
    )
    db.add(admin)
    db.commit()
    db.close()
    print("Admin user created.")

seed_admin()



from routers import auth, classes, sessions, attendance, resources
app.include_router(auth.router)
app.include_router(classes.router)
app.include_router(sessions.router)
app.include_router(attendance.router)
app.include_router(resources.router)

# ─────────────────────────────────────────────
# ROOT ENDPOINT — health check
# ─────────────────────────────────────────────

@app.get("/")
def root():
    return {"message": "QR Attendance API is running", "docs": "/docs"}
