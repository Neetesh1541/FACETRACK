
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from database import engine
from models.models import Organization, Base

router = APIRouter(prefix="/organizations", tags=["Organizations"])


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


@router.post("/register")
def register_organization(data: OrganizationCreate, db: Session = Depends(get_db)):

    existing = db.query(Organization).filter(
        Organization.email == data.email
    ).first()

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Organization already registered"
        )

    organization = Organization(
        name=data.name,
        email=data.email,
        phone=data.phone,
        address=data.address
    )

    db.add(organization)
    db.commit()
    db.refresh(organization)

    return {
        "message": "Organization registered successfully",
        "organization_id": organization.id,
        "organization_name": organization.name
    }
