
from datetime import date, datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database import SessionLocal
from models.models import AttendanceRecord, Employee
from routes.employees import get_current_admin


router = APIRouter(
    prefix="/attendance",
    tags=["Attendance Reports"]
)

INDIA_TIMEZONE = ZoneInfo("Asia/Kolkata")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/records")
def get_attendance_records(
    attendance_date: date | None = Query(default=None),
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin)
):
    if attendance_date is None:
        attendance_date = datetime.now(INDIA_TIMEZONE).date()

    records = (
        db.query(AttendanceRecord, Employee)
        .join(
            Employee,
            AttendanceRecord.employee_id == Employee.id
        )
        .filter(
            AttendanceRecord.organization_id == current_admin.organization_id,
            AttendanceRecord.attendance_date == attendance_date
        )
        .order_by(AttendanceRecord.check_in.desc())
        .all()
    )

    total_employees = (
        db.query(Employee)
        .filter(
            Employee.organization_id == current_admin.organization_id,
            Employee.is_active == True
        )
        .count()
    )

    attendance_list = []

    present_count = 0
    late_count = 0

    for record, employee in records:
        status = record.status or "Unknown"

        if status.lower() == "present":
            present_count += 1
        elif status.lower() == "late":
            late_count += 1

        attendance_list.append({
            "attendance_id": record.id,
            "employee_id": employee.id,
            "employee_name": employee.name,
            "employee_code": employee.employee_code,
            "department": employee.department,
            "date": record.attendance_date,
            "check_in": record.check_in,
            "check_out": record.check_out,
            "total_working_minutes": record.total_working_minutes,
            "status": status
        })

    absent_count = max(total_employees - len(records), 0)

    return {
        "organization_id": current_admin.organization_id,
        "attendance_date": attendance_date,
        "summary": {
            "total_employees": total_employees,
            "total_attendance": len(records),
            "present": present_count,
            "late": late_count,
            "absent": absent_count
        },
        "records": attendance_list
    }
