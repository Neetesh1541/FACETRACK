
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes.organization import router as organization_router
from routes.auth import router as auth_router
from routes.employees import router as employee_router
from routes.face import router as face_router
from routes.attendance import router as attendance_router
from routes.attendance_reports import router as attendance_reports_router
from routes.attendance_history import router as attendance_history_router
from routes.office_devices import router as office_devices_router

app = FastAPI(
    title="FACETRACK API",
    description="Multi-Organization Face Recognition Attendance System",
    version="1.0.0"
)

# Allow React frontend to communicate with FastAPI
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://facetrack-l444.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Existing API routes
app.include_router(organization_router)
app.include_router(auth_router)
app.include_router(employee_router)
app.include_router(face_router)
app.include_router(attendance_router)
app.include_router(attendance_reports_router)
app.include_router(attendance_history_router)
app.include_router(office_devices_router)


@app.get("/")
def home():
    return {
        "project": "FACETRACK",
        "message": "Welcome to FACETRACK Backend!",
        "status": "Running"
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "backend": "working"
    }
