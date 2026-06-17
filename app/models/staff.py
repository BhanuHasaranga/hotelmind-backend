import uuid
from datetime import date, datetime, time
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, String, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.hotel import Branch


class Department(Base):
    __tablename__ = "departments"

    branch_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("branches.id", ondelete="CASCADE"), nullable=False)
    # e.g. HOUSEKEEPING | RECEPTION | KITCHEN | MANAGEMENT | SECURITY
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    branch: Mapped["Branch"] = relationship("Branch", back_populates="departments")
    employees: Mapped[list["Employee"]] = relationship("Employee", back_populates="department")


class Employee(Base):
    __tablename__ = "employees"

    department_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("departments.id"), nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    phone: Mapped[str | None] = mapped_column(String(30))
    role: Mapped[str | None] = mapped_column(String(100))
    hire_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    department: Mapped["Department"] = relationship("Department", back_populates="employees")
    schedules: Mapped[list["Schedule"]] = relationship("Schedule", back_populates="employee")
    attendance_records: Mapped[list["Attendance"]] = relationship("Attendance", back_populates="employee")


class Schedule(Base):
    __tablename__ = "schedules"

    employee_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)
    shift_date: Mapped[date] = mapped_column(Date, nullable=False)
    shift_start: Mapped[time] = mapped_column(Time, nullable=False)
    shift_end: Mapped[time] = mapped_column(Time, nullable=False)
    notes: Mapped[str | None] = mapped_column(String(500))

    employee: Mapped["Employee"] = relationship("Employee", back_populates="schedules")
    attendance: Mapped[list["Attendance"]] = relationship("Attendance", back_populates="schedule")


class Attendance(Base):
    __tablename__ = "attendance"

    schedule_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("schedules.id"), nullable=False)
    employee_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("employees.id"), nullable=False)
    clock_in: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    clock_out: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # PRESENT | ABSENT | LATE | HALF_DAY
    status: Mapped[str] = mapped_column(String(20), default="PRESENT", nullable=False)

    schedule: Mapped["Schedule"] = relationship("Schedule", back_populates="attendance")
    employee: Mapped["Employee"] = relationship("Employee", back_populates="attendance_records")
