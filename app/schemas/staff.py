import uuid
from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict


class DepartmentCreate(BaseModel):
    branch_id: uuid.UUID
    name: str


class DepartmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    branch_id: uuid.UUID
    name: str


class EmployeeCreate(BaseModel):
    department_id: uuid.UUID
    first_name: str
    last_name: str
    email: str
    phone: str | None = None
    role: str | None = None
    hire_date: date


class EmployeeUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    role: str | None = None
    department_id: uuid.UUID | None = None


class EmployeeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    department_id: uuid.UUID
    first_name: str
    last_name: str
    email: str
    phone: str | None
    role: str | None
    hire_date: date
    is_active: bool
    department: DepartmentResponse | None = None


class ScheduleCreate(BaseModel):
    employee_id: uuid.UUID
    shift_date: date
    shift_start: time
    shift_end: time
    notes: str | None = None


class ScheduleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    employee_id: uuid.UUID
    shift_date: date
    shift_start: time
    shift_end: time
    notes: str | None


class AttendanceClockIn(BaseModel):
    schedule_id: uuid.UUID
    employee_id: uuid.UUID
    clock_in: datetime


class AttendanceClockOut(BaseModel):
    clock_out: datetime


class AttendanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    schedule_id: uuid.UUID
    employee_id: uuid.UUID
    clock_in: datetime
    clock_out: datetime | None
    status: str
