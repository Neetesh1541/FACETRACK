
from getpass import getpass

from sqlalchemy.orm import Session
from pwdlib import PasswordHash

from database import engine
from models.models import Organization, OrganizationAdmin

password_hash = PasswordHash.recommended()


def create_admin():
    db = Session(engine)

    try:
        print("\n===== FACETRACK ADMIN SETUP =====")

        org_id = int(input("Organization ID: "))

        organization = db.query(Organization).filter(
            Organization.id == org_id,
            Organization.is_active == True
        ).first()

        if not organization:
            print("Organization not found or inactive!")
            return

        name = input("Admin Name: ").strip()
        email = input("Admin Email: ").strip().lower()
        password = getpass("Create Password: ")
        confirm_password = getpass("Confirm Password: ")

        if not name or not email or not password:
            print("All fields are required!")
            return

        if password != confirm_password:
            print("Passwords do not match!")
            return

        if len(password) < 8:
            print("Password must be at least 8 characters!")
            return

        existing = db.query(OrganizationAdmin).filter(
            OrganizationAdmin.organization_id == org_id,
            OrganizationAdmin.email == email
        ).first()

        if existing:
            print("Admin already exists!")
            return

        admin = OrganizationAdmin(
            organization_id=org_id,
            name=name,
            email=email,
            password_hash=password_hash.hash(password)
        )

        db.add(admin)
        db.commit()

        print("\nAdmin account created successfully!")
        print("Organization:", organization.name)
        print("Admin:", name)
        print("Email:", email)

    except ValueError:
        print("Please enter a valid Organization ID.")

    finally:
        db.close()


if __name__ == "__main__":
    create_admin()
