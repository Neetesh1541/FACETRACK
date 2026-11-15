
import os
import traceback
from datetime import datetime
from zoneinfo import ZoneInfo

import cv2
import jwt
import numpy as np

from dotenv import load_dotenv
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    UploadFile,
    File
)
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from database import engine
from models.models import (
    Employee,
    FaceProfile,
    AttendanceRecord,
    AttendanceEvent,
    OrganizationAdmin,
    Organization,
    OfficeDevice
)
from services.face_engine import face_engine
from services.biometric_security import decrypt_embedding
from services.attendance_engine import process_attendance_action


load_dotenv()

router = APIRouter(
    prefix="/attendance",
    tags=["Attendance"]
)

INDIA_TIMEZONE = ZoneInfo("Asia/Kolkata")

FACE_MATCH_THRESHOLD = 0.60

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

security = HTTPBearer()


def get_db():
    db = Session(engine)
    try:
        yield db
    finally:
        db.close()


def get_attendance_actor(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    if not JWT_SECRET_KEY:
        raise HTTPException(
            status_code=500,
            detail="JWT configuration missing"
        )

    try:
        payload = jwt.decode(
            credentials.credentials,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM]
        )

        role = payload.get("role")
        organization_id = int(payload["organization_id"])
        user_id = int(payload["sub"])

    except (jwt.InvalidTokenError, KeyError, TypeError, ValueError):
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token"
        )

    organization = db.query(Organization).filter(
        Organization.id == organization_id,
        Organization.is_active == True
    ).first()

    if not organization:
        raise HTTPException(
            status_code=401,
            detail="Organization unavailable"
        )

    if role == "organization_admin":
        admin = db.query(OrganizationAdmin).filter(
            OrganizationAdmin.id == user_id,
            OrganizationAdmin.organization_id == organization_id,
            OrganizationAdmin.is_active == True
        ).first()

        if not admin:
            raise HTTPException(
                status_code=401,
                detail="Admin account unavailable"
            )

        return {
            "role": "organization_admin",
            "organization_id": organization_id,
            "device_id": None
        }

    elif role == "office":
        office_id = int(payload.get("office_id", 0))

        office = db.query(OfficeDevice).filter(
            OfficeDevice.id == office_id,
            OfficeDevice.id == user_id,
            OfficeDevice.organization_id == organization_id,
            OfficeDevice.is_active == True
        ).first()

        if not office:
            raise HTTPException(
                status_code=401,
                detail="Office is inactive or unavailable"
            )

        return {
            "role": "office",
            "organization_id": organization_id,
            "device_id": office.id,
            "office_name": office.device_name
        }

    raise HTTPException(
        status_code=403,
        detail="Attendance access denied"
    )


@router.post("/scan")
async def scan_attendance(
    face_image: UploadFile = File(...),
    actor: dict = Depends(get_attendance_actor),
    db: Session = Depends(get_db)
):
    organization_id = actor["organization_id"]
    device_id = actor["device_id"]

    # 1. Validate image
    if face_image.content_type not in [
        "image/jpeg",
        "image/png",
        "image/webp"
    ]:
        raise HTTPException(
            status_code=400,
            detail="Only JPG, PNG and WEBP images are allowed"
        )

    image_data = await face_image.read(
        5 * 1024 * 1024 + 1
    )

    if len(image_data) > 5 * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail="Image must be under 5 MB"
        )

    image_array = np.frombuffer(
        image_data,
        dtype=np.uint8
    )

    image = cv2.imdecode(
        image_array,
        cv2.IMREAD_COLOR
    )

    if image is None:
        raise HTTPException(
            status_code=400,
            detail="Invalid image file"
        )

    # 2. Generate face embedding
    try:
        candidate_embedding = face_engine.generate_embedding(
            image
        )
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )

    # 3. Find enrolled employees in this organization
    profiles = db.query(
        FaceProfile,
        Employee
    ).join(
        Employee,
        FaceProfile.employee_id == Employee.id
    ).filter(
        FaceProfile.organization_id == organization_id,
        Employee.organization_id == organization_id,
        Employee.is_active == True,
        FaceProfile.consent_given == True
    ).all()

    if not profiles:
        raise HTTPException(
            status_code=404,
            detail="No enrolled employees found"
        )

    # 4. Compare faces
    best_match = None
    best_score = -1.0

    for profile, employee in profiles:
        try:
            saved_embedding = decrypt_embedding(
                profile.encrypted_face_template
            )

            score = face_engine.compare_faces(
                candidate_embedding,
                saved_embedding
            )

            if score > best_score:
                best_score = score
                best_match = employee

        except Exception:
            traceback.print_exc()
            continue

    if best_match is None:
        raise HTTPException(
            status_code=500,
            detail="Face comparison failed"
        )

    if best_score < FACE_MATCH_THRESHOLD:
        raise HTTPException(
            status_code=404,
            detail="No matching employee found"
        )

    try:
        # 5. Lock employee row
        employee = db.query(Employee).filter(
            Employee.id == best_match.id,
            Employee.organization_id == organization_id,
            Employee.is_active == True
        ).with_for_update().first()

        if not employee:
            raise HTTPException(
                status_code=404,
                detail="Employee not found"
            )

        current_time = datetime.now(INDIA_TIMEZONE)
        today = current_time.date()

        # 6. Find today's attendance
        record = db.query(AttendanceRecord).filter(
            AttendanceRecord.organization_id == organization_id,
            AttendanceRecord.employee_id == employee.id,
            AttendanceRecord.attendance_date == today
        ).with_for_update().first()

        # 7. Calculate attendance action
        result = process_attendance_action(
            record,
            current_time
        )

        if result["action"] == "blocked":
            db.rollback()

            return {
                "message": result["message"],
                "employee_name": employee.name,
                "attendance_status": "Already completed"
            }

        if result["action"] == "check_in":
            record = AttendanceRecord(
                organization_id=organization_id,
                employee_id=employee.id,
                attendance_date=today,
                check_in=current_time,
                status=result["status"],
                total_working_minutes=0
            )

            db.add(record)

        elif result["action"] == "check_out":
            record.check_out = current_time
            record.total_working_minutes = (
                result["total_working_minutes"]
            )

        # 8. Save attendance event with office ID
        event = AttendanceEvent(
            organization_id=organization_id,
            employee_id=employee.id,
            device_id=device_id,
            event_type=result["action"],
            event_time=current_time,
            confidence_score=str(round(best_score, 4))
        )

        db.add(event)

        db.flush()
        db.commit()
        db.refresh(record)

        response = {
            "message": result["message"],
            "employee": {
                "id": employee.id,
                "name": employee.name,
                "employee_code": employee.employee_code
            },
            "attendance": {
                "action": result["action"],
                "date": today.isoformat(),
                "time": current_time.isoformat(),
                "status": record.status,
                "total_working_minutes": record.total_working_minutes
            },
            "face_similarity_score": round(best_score, 4),
            "office_id": device_id
        }

        if actor["role"] == "office":
            response["office_name"] = actor["office_name"]

        return response

    except HTTPException:
        db.rollback()
        raise

    except IntegrityError:
        db.rollback()
        traceback.print_exc()

        raise HTTPException(
            status_code=409,
            detail="Attendance record conflict. Please retry."
        )

    except Exception:
        db.rollback()

        print("\n========== FACETRACK ATTENDANCE ERROR ==========")
        traceback.print_exc()
        print("================================================\n")

        raise HTTPException(
            status_code=500,
            detail="Attendance could not be saved. Check backend CMD."
        )
