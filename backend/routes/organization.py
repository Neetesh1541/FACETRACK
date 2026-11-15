
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, Field
from pwdlib import PasswordHash

from database import engine
from models.models import Organization, OrganizationAdmin

router = APIRouter(prefix="/organizations", tags=["Organizations"])

password_hash = PasswordHash.recommended()


def get_db():
    db = Session(engine)
    try:
        yield db
    finally:
        db.close()


class OrganizationCreate(BaseModel):
    name: str
    email: EmailStr
    phone: str | None = None
    address: str | None = None

    admin_name: str
    admin_email: EmailStr
    admin_password: str = Field(min_length=8)


@router.post("/register-with-admin")
def register_organization(
    data: OrganizationCreate,
    db: Session = Depends(get_db)
):
    organization_email = data.email.lower()
    admin_email = data.admin_email.lower()

    existing = db.query(Organization).filter(
        Organization.email == organization_email
    ).first()

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Organization email already registered"
        )

    organization = Organization(
        name=data.name.strip(),
        email=organization_email,
        phone=data.phone,
        address=data.address
    )

    try:
        db.add(organization)
        db.flush()

        admin = OrganizationAdmin(
            organization_id=organization.id,
            name=data.admin_name.strip(),
            email=admin_email,
            password_hash=password_hash.hash(data.admin_password)
        )

        db.add(admin)
        db.commit()
        db.refresh(organization)

        return {
            "message": "Organization registered successfully",
            "organization_id": organization.id,
            "organization_name": organization.name,
            "admin_email": admin.email
        }

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Organization registration failed"
        )
