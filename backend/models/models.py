
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime,
    Date, Time, ForeignKey, LargeBinary, Text,
    UniqueConstraint
)
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


# 1. Organizations
class Organization(Base):
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    email = Column(String(150), unique=True, nullable=False)
    phone = Column(String(20))
    address = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# 2. Organization Admins
class OrganizationAdmin(Base):
    __tablename__ = "organization_admins"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer, ForeignKey("organizations.id"), nullable=False
    )
    name = Column(String(100), nullable=False)
    email = Column(String(150), nullable=False)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("organization_id", "email"),
    )


# 3. Office Devices
class OfficeDevice(Base):
    __tablename__ = "office_devices"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer, ForeignKey("organizations.id"), nullable=False
    )
    device_name = Column(String(100), nullable=False)
    device_key_hash = Column(String(255), nullable=False, unique=True)
    location = Column(String(200))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# 4. Employees
class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer, ForeignKey("organizations.id"), nullable=False
    )
    employee_code = Column(String(50), nullable=False)
    name = Column(String(120), nullable=False)
    email = Column(String(150))
    phone = Column(String(20))
    department = Column(String(100))
    designation = Column(String(100))
    profile_photo = Column(String(500))
    joining_date = Column(Date)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("organization_id", "employee_code"),
    )


# 5. Face Profiles
class FaceProfile(Base):
    __tablename__ = "face_profiles"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer, ForeignKey("organizations.id"), nullable=False
    )
    employee_id = Column(
        Integer, ForeignKey("employees.id"), nullable=False, unique=True
    )
    encrypted_face_template = Column(LargeBinary, nullable=False)
    consent_given = Column(Boolean, default=False, nullable=False)
    enrolled_at = Column(DateTime(timezone=True), server_default=func.now())


# 6. Attendance Records
class AttendanceRecord(Base):
    __tablename__ = "attendance_records"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer, ForeignKey("organizations.id"), nullable=False
    )
    employee_id = Column(
        Integer, ForeignKey("employees.id"), nullable=False
    )
    attendance_date = Column(Date, nullable=False)
    check_in = Column(DateTime(timezone=True))
    check_out = Column(DateTime(timezone=True))
    total_working_minutes = Column(Integer, default=0)
    status = Column(String(30), default="present")

    __table_args__ = (
        UniqueConstraint("employee_id", "attendance_date"),
    )


# 7. Attendance Events
class AttendanceEvent(Base):
    __tablename__ = "attendance_events"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer, ForeignKey("organizations.id"), nullable=False
    )
    employee_id = Column(
        Integer, ForeignKey("employees.id"), nullable=False
    )
    device_id = Column(Integer, ForeignKey("office_devices.id"))
    event_type = Column(String(30), nullable=False)
    event_time = Column(DateTime(timezone=True), server_default=func.now())
    confidence_score = Column(String(20))


# 8. Audit Logs
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer, ForeignKey("organizations.id"), nullable=False
    )
    actor_type = Column(String(30))
    actor_id = Column(Integer)
    action = Column(String(150), nullable=False)
    details = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
