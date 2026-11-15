
import os
import uuid
from datetime import date
from pathlib import Path

import jwt
from dotenv import load_dotenv
from fastapi import (
    APIRouter, Depends, HTTPException,
    UploadFile, File, Form
)
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from database import engine
from models.models import Employee, OrganizationAdmin, Organization

load_dotenv()

router = APIRouter(prefix="/employees", tags=["Employees"])

security = HTTPBearer()

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

UPLOAD_DIR = Path("uploads/employees")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp"
}


# Database connection
def get_db():
    db = Session(engine)
    try:
        yield db
    finally:
        db.close()


# Verify Admin JWT Token
def get_current_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    if not JWT_SECRET_KEY:
        raise HTTPException(status_code=500, detail="JWT configuration missing")

    try:
        payload = jwt.decode(
            credentials.credentials,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM]
        )

        admin_id = int(payload["sub"])
        organization_id = int(payload["organization_id"])

        if payload.get("role") != "organization_admin":
            raise HTTPException(status_code=403, detail="Admin access required")

    except (jwt.InvalidTokenError, KeyError, TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    admin = db.query(OrganizationAdmin).filter(
        OrganizationAdmin.id == admin_id,
        OrganizationAdmin.organization_id == organization_id,
        OrganizationAdmin.is_active == True
    ).first()

    organization = db.query(Organization).filter(
        Organization.id == organization_id,
        Organization.is_active == True
    ).first()

    if not admin or not organization:
        raise HTTPException(status_code=401, detail="Admin account unavailable")

    return admin


# Add Employee
@router.post("/add")
async def add_employee(
    employee_code: str = Form(...),
    name: str = Form(...),
    email: str | None = Form(None),
    phone: str | None = Form(None),
    department: str | None = Form(None),
    designation: str | None = Form(None),
    joining_date: date | None = Form(None),
    profile_photo: UploadFile | None = File(None),
    admin: OrganizationAdmin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):

    employee_code = employee_code.strip()
    name = name.strip()

    if not employee_code or not name:
        raise HTTPException(
            status_code=400,
            detail="Employee code and name are required"
        )

    existing = db.query(Employee).filter(
        Employee.organization_id == admin.organization_id,
        Employee.employee_code == employee_code
    ).first()

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Employee code already exists"
        )

    photo_path = None

    if profile_photo and profile_photo.filename:
        if profile_photo.content_type not in ALLOWED_TYPES:
            raise HTTPException(
                status_code=400,
                detail="Only JPG, PNG and WEBP images are allowed"
            )

        image_data = await profile_photo.read(5 * 1024 * 1024 + 1)

        if len(image_data) > 5 * 1024 * 1024:
            raise HTTPException(
                status_code=400,
                detail="Image size must be under 5 MB"
            )

        extension = ALLOWED_TYPES[profile_photo.content_type]
        filename = f"{uuid.uuid4().hex}{extension}"

        photo_path = str(UPLOAD_DIR / filename)

        with open(photo_path, "wb") as image_file:
            image_file.write(image_data)

    employee = Employee(
        organization_id=admin.organization_id,
        employee_code=employee_code,
        name=name,
        email=email,
        phone=phone,
        department=department,
        designation=designation,
        joining_date=joining_date,
        profile_photo=photo_path
    )

    try:
        db.add(employee)
        db.commit()
        db.refresh(employee)
    except Exception:
        db.rollback()
        if photo_path and os.path.exists(photo_path):
            os.remove(photo_path)
        raise HTTPException(status_code=500, detail="Employee creation failed")

    return {
        "message": "Employee created successfully",
        "employee": {
            "id": employee.id,
            "employee_code": employee.employee_code,
            "name": employee.name,
            "email": employee.email,
            "department": employee.department,
            "designation": employee.designation,
            "profile_photo": employee.profile_photo
        }
    }


# Get Employees of Logged-in Organization
@router.get("/")
def get_employees(
    admin: OrganizationAdmin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):

    employees = db.query(Employee).filter(
        Employee.organization_id == admin.organization_id
    ).order_by(Employee.id.desc()).all()

    return {
        "total_employees": len(employees),
        "employees": [
            {
                "id": emp.id,
                "employee_code": emp.employee_code,
                "name": emp.name,
                "email": emp.email,
                "phone": emp.phone,
                "department": emp.department,
                "designation": emp.designation,
                "joining_date": emp.joining_date,
                "profile_photo": emp.profile_photo,
                "is_active": emp.is_active
            }
            for emp in employees
        ]
    }
