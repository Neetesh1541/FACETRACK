
import os
import jwt

from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from pwdlib import PasswordHash
from sqlalchemy.orm import Session

from database import engine
from models.models import Organization, OrganizationAdmin, OfficeDevice

load_dotenv()

router = APIRouter(prefix="/auth", tags=["Authentication"])

password_hash = PasswordHash.recommended()

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")


def get_db():
    db = Session(engine)
    try:
        yield db
    finally:
        db.close()


class AdminLoginRequest(BaseModel):
    organization_id: int
    email: EmailStr
    password: str


class OfficeLoginRequest(BaseModel):
    office_id: int
    pin: str


def create_access_token(payload: dict):
    if not JWT_SECRET_KEY:
        raise HTTPException(
            status_code=500,
            detail="JWT secret key is not configured"
        )

    token_payload = {
        **payload,
        "exp": datetime.now(timezone.utc) + timedelta(hours=8)
    }

    return jwt.encode(
        token_payload,
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM
    )


@router.post("/admin/login")
def admin_login(data: AdminLoginRequest, db: Session = Depends(get_db)):

    organization = db.query(Organization).filter(
        Organization.id == data.organization_id,
        Organization.is_active == True
    ).first()

    if not organization:
        raise HTTPException(
            status_code=401,
            detail="Invalid login credentials"
        )

    admin = db.query(OrganizationAdmin).filter(
        OrganizationAdmin.organization_id == organization.id,
        OrganizationAdmin.email == data.email.lower(),
        OrganizationAdmin.is_active == True
    ).first()

    if not admin or not password_hash.verify(
        data.password, admin.password_hash
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid login credentials"
        )

    access_token = create_access_token({
        "sub": str(admin.id),
        "organization_id": organization.id,
        "role": "organization_admin"
    })

    return {
        "message": "Admin login successful",
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": 28800,
        "admin": {
            "id": admin.id,
            "name": admin.name,
            "email": admin.email,
            "organization_id": organization.id,
            "organization_name": organization.name
        }
    }


@router.post("/office/login")
def office_login(
    data: OfficeLoginRequest,
    db: Session = Depends(get_db)
):
    office = db.query(OfficeDevice).filter(
        OfficeDevice.id == data.office_id,
        OfficeDevice.is_active == True
    ).first()

    if not office:
        raise HTTPException(
            status_code=401,
            detail="Invalid Office ID or PIN"
        )

    organization = db.query(Organization).filter(
        Organization.id == office.organization_id,
        Organization.is_active == True
    ).first()

    if not organization:
        raise HTTPException(
            status_code=401,
            detail="Office organization is inactive"
        )

    try:
        pin_valid = password_hash.verify(
            data.pin,
            office.device_key_hash
        )
    except Exception:
        pin_valid = False

    if not pin_valid:
        raise HTTPException(
            status_code=401,
            detail="Invalid Office ID or PIN"
        )

    access_token = create_access_token({
        "sub": str(office.id),
        "office_id": office.id,
        "organization_id": office.organization_id,
        "role": "office"
    })

    return {
        "message": "Office login successful",
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": 28800,
        "office": {
            "id": office.id,
            "name": office.device_name,
            "location": office.location,
            "organization_id": organization.id,
            "organization_name": organization.name
        }
    }
