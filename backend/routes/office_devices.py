
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from pwdlib import PasswordHash

from database import SessionLocal
from models.models import OfficeDevice
from routes.employees import get_current_admin

router = APIRouter(
    prefix="/office-devices",
    tags=["Office Management"]
)

password_hash = PasswordHash.recommended()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/register")
def register_office(
    device_name: str = Query(..., min_length=2, max_length=100),
    pin: str = Query(..., min_length=4, max_length=12),
    location: str = Query("", max_length=200),
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin)
):
    if not pin.isdigit():
        raise HTTPException(
            status_code=400,
            detail="Office PIN must contain only digits"
        )

    office = OfficeDevice(
        organization_id=current_admin.organization_id,
        device_name=device_name.strip(),
        device_key_hash=password_hash.hash(pin),
        location=location.strip(),
        is_active=True
    )

    try:
        db.add(office)
        db.commit()
        db.refresh(office)

        return {
            "message": "Office registered successfully",
            "office": {
                "id": office.id,
                "office_id": office.id,
                "name": office.device_name,
                "location": office.location,
                "is_active": office.is_active
            }
        }

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Office registration failed"
        )


@router.get("/")
def get_offices(
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin)
):
    offices = (
        db.query(OfficeDevice)
        .filter(
            OfficeDevice.organization_id == current_admin.organization_id
        )
        .order_by(OfficeDevice.id.desc())
        .all()
    )

    return {
        "total_offices": len(offices),
        "offices": [
            {
                "id": office.id,
                "office_id": office.id,
                "name": office.device_name,
                "location": office.location,
                "is_active": office.is_active,
                "created_at": office.created_at
            }
            for office in offices
        ]
    }


@router.patch("/{office_id}/deactivate")
def deactivate_office(
    office_id: int,
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin)
):
    office = db.query(OfficeDevice).filter(
        OfficeDevice.id == office_id,
        OfficeDevice.organization_id == current_admin.organization_id
    ).first()

    if office is None:
        raise HTTPException(
            status_code=404,
            detail="Office not found"
        )

    office.is_active = False
    db.commit()

    return {
        "message": "Office deactivated successfully",
        "office_id": office.id,
        "is_active": False
    }
