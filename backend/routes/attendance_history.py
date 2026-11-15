
from datetime import date
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from database import SessionLocal
from models.models import AttendanceRecord, Employee
from routes.employees import get_current_admin

router = APIRouter(
    prefix="/attendance",
    tags=["Attendance History"]
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/employee/{employee_id}/history")
def get_employee_attendance_history(
    employee_id: int,
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin)
):
    employee = (
        db.query(Employee)
        .filter(
            Employee.id == employee_id,
            Employee.organization_id == current_admin.organization_id
        )
        .first()
    )

    if employee is None:
        raise HTTPException(
            status_code=404,
            detail="Employee not found"
        )

    query = db.query(AttendanceRecord).filter(
        AttendanceRecord.employee_id == employee_id,
        AttendanceRecord.organization_id == current_admin.organization_id
    )

    if start_date:
        query = query.filter(
            AttendanceRecord.attendance_date >= start_date
        )

    if end_date:
        query = query.filter(
            AttendanceRecord.attendance_date <= end_date
        )

    records = query.order_by(
        AttendanceRecord.attendance_date.desc()
    ).all()

    total_present = sum(
        1 for record in records
        if (record.status or "").lower() == "present"
    )

    total_late = sum(
        1 for record in records
        if (record.status or "").lower() == "late"
    )

    total_working_minutes = sum(
        record.total_working_minutes or 0
        for record in records
    )

    return {
        "employee": {
            "id": employee.id,
            "name": employee.name,
            "employee_code": employee.employee_code,
            "department": employee.department
        },
        "summary": {
            "total_attendance_days": len(records),
            "present_days": total_present,
            "late_days": total_late,
            "total_working_minutes": total_working_minutes,
            "total_working_hours": round(
                total_working_minutes / 60, 2
            )
        },
        "history": [
            {
                "date": record.attendance_date,
                "check_in": record.check_in,
                "check_out": record.check_out,
                "working_minutes": record.total_working_minutes,
                "status": record.status
            }
            for record in records
        ]
    }
