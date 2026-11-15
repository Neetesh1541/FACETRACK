
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

import cv2
import numpy as np

from database import engine
from models.models import Employee, OrganizationAdmin, FaceProfile
from routes.employees import get_current_admin
from services.face_engine import face_engine
from services.biometric_security import encrypt_embedding


router = APIRouter(prefix="/face", tags=["Face Recognition"])


def get_db():
    db = Session(engine)
    try:
        yield db
    finally:
        db.close()


@router.post("/enroll/{employee_id}")
async def enroll_employee_face(
    employee_id: int,
    consent_given: bool = Form(...),
    face_image: UploadFile = File(...),
    admin: OrganizationAdmin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    if not consent_given:
        raise HTTPException(
            status_code=400,
            detail="Employee consent is required"
        )

    employee = db.query(Employee).filter(
        Employee.id == employee_id,
        Employee.organization_id == admin.organization_id,
        Employee.is_active == True
    ).first()

    if not employee:
        raise HTTPException(
            status_code=404,
            detail="Employee not found"
        )

    if face_image.content_type not in [
        "image/jpeg",
        "image/png",
        "image/webp"
    ]:
        raise HTTPException(
            status_code=400,
            detail="Only JPG, PNG and WEBP images are allowed"
        )

    image_data = await face_image.read(5 * 1024 * 1024 + 1)

    if len(image_data) > 5 * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail="Image must be under 5 MB"
        )

    image_array = np.frombuffer(image_data, dtype=np.uint8)
    image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

    if image is None:
        raise HTTPException(
            status_code=400,
            detail="Invalid image file"
        )

    try:
        embedding = face_engine.generate_embedding(image)

        encrypted_template = encrypt_embedding(embedding)

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )

    existing_profile = db.query(FaceProfile).filter(
        FaceProfile.employee_id == employee.id,
        FaceProfile.organization_id == admin.organization_id
    ).first()

    try:
        if existing_profile:
            existing_profile.encrypted_face_template = encrypted_template
            existing_profile.consent_given = True
        else:
            profile = FaceProfile(
                organization_id=admin.organization_id,
                employee_id=employee.id,
                encrypted_face_template=encrypted_template,
                consent_given=True
            )
            db.add(profile)

        db.commit()

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Face enrollment could not be saved"
        )

    return {
        "message": "Employee face enrolled successfully",
        "employee_id": employee.id,
        "employee_name": employee.name,
        "face_detected": True,
        "embedding_dimensions": int(embedding.shape[0]),
        "consent_received": True,
        "template_encrypted": True,
        "template_saved": True
    }

from services.biometric_security import decrypt_embedding


@router.post("/recognize")
async def recognize_employee_face(
    face_image: UploadFile = File(...),
    admin: OrganizationAdmin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    if face_image.content_type not in [
        "image/jpeg", "image/png", "image/webp"
    ]:
        raise HTTPException(
            status_code=400,
            detail="Only JPG, PNG and WEBP images are allowed"
        )

    image_data = await face_image.read(5 * 1024 * 1024 + 1)

    if len(image_data) > 5 * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail="Image must be under 5 MB"
        )

    image_array = np.frombuffer(image_data, dtype=np.uint8)
    image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

    if image is None:
        raise HTTPException(status_code=400, detail="Invalid image")

    try:
        candidate_embedding = face_engine.generate_embedding(image)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))

    profiles = db.query(FaceProfile, Employee).join(
        Employee,
        FaceProfile.employee_id == Employee.id
    ).filter(
        FaceProfile.organization_id == admin.organization_id,
        Employee.organization_id == admin.organization_id,
        Employee.is_active == True,
        FaceProfile.consent_given == True
    ).all()

    if not profiles:
        raise HTTPException(
            status_code=404,
            detail="No enrolled employees found"
        )

    matches = []

    for profile, employee in profiles:
        try:
            saved_embedding = decrypt_embedding(
                profile.encrypted_face_template
            )

            similarity = face_engine.compare_faces(
                candidate_embedding,
                saved_embedding
            )

            matches.append({
                "employee_id": employee.id,
                "employee_code": employee.employee_code,
                "employee_name": employee.name,
                "similarity_score": round(similarity, 4)
            })

        except Exception:
            continue

    if not matches:
        raise HTTPException(
            status_code=500,
            detail="Could not compare saved face templates"
        )

    matches.sort(
        key=lambda item: item["similarity_score"],
        reverse=True
    )

    return {
        "message": "Face comparison completed",
        "organization_id": admin.organization_id,
        "best_match": matches[0],
        "other_matches": matches[1:3],
        "note": "Similarity score is not a verified identity decision. Threshold calibration is required."
    }
