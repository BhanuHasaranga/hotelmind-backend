import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_dependencies import get_current_user, require_roles
from app.db.session import get_db
from app.repositories.staff import (
    AttendanceRepository,
    DepartmentRepository,
    EmployeeRepository,
    ScheduleRepository,
)
from app.schemas.staff import (
    AttendanceClockIn,
    AttendanceClockOut,
    AttendanceResponse,
    DepartmentCreate,
    DepartmentResponse,
    EmployeeCreate,
    EmployeeResponse,
    EmployeeUpdate,
    ScheduleCreate,
    ScheduleResponse,
)
from app.services.staff import StaffService

router = APIRouter(prefix="/staff", tags=["Staff"], dependencies=[Depends(get_current_user)])

# Mutating department/employee/schedule management restricted to OWNER and OPS_MANAGER.
# NOTE: clock_in/clock_out/list_attendance/GETs remain coarse (any authenticated role) —
# a kiosk-style clock-in flow may need broader access; revisit in a later phase.
manage_roles = Depends(require_roles("OWNER", "OPS_MANAGER"))


def get_staff_service(db: AsyncSession = Depends(get_db)) -> StaffService:
    return StaffService(
        dept_repo=DepartmentRepository(db),
        employee_repo=EmployeeRepository(db),
        schedule_repo=ScheduleRepository(db),
        attendance_repo=AttendanceRepository(db),
    )


ServiceDep = Annotated[StaffService, Depends(get_staff_service)]


@router.get("/departments", response_model=list[DepartmentResponse])
async def list_departments(branch_id: uuid.UUID, svc: ServiceDep):
    return await svc.list_departments(branch_id)


@router.post(
    "/departments", response_model=DepartmentResponse, status_code=status.HTTP_201_CREATED, dependencies=[manage_roles]
)
async def create_department(payload: DepartmentCreate, svc: ServiceDep):
    return await svc.create_department(payload)


@router.get("/employees", response_model=list[EmployeeResponse])
async def list_employees(
    svc: ServiceDep,
    department_id: uuid.UUID | None = None,
    skip: int = 0,
    limit: int = 100,
):
    return await svc.list_employees(department_id, skip, limit)


@router.post(
    "/employees", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED, dependencies=[manage_roles]
)
async def create_employee(payload: EmployeeCreate, svc: ServiceDep):
    return await svc.create_employee(payload)


@router.get("/employees/{employee_id}", response_model=EmployeeResponse)
async def get_employee(employee_id: uuid.UUID, svc: ServiceDep):
    return await svc.get_employee(employee_id)


@router.put("/employees/{employee_id}", response_model=EmployeeResponse, dependencies=[manage_roles])
async def update_employee(employee_id: uuid.UUID, payload: EmployeeUpdate, svc: ServiceDep):
    return await svc.update_employee(employee_id, payload)


@router.patch("/employees/{employee_id}/deactivate", status_code=status.HTTP_204_NO_CONTENT, dependencies=[manage_roles])
async def deactivate_employee(employee_id: uuid.UUID, svc: ServiceDep):
    await svc.deactivate_employee(employee_id)


@router.get("/schedules", response_model=list[ScheduleResponse])
async def list_schedules(
    employee_id: uuid.UUID,
    svc: ServiceDep,
    from_date: date | None = None,
    skip: int = 0,
    limit: int = 100,
):
    return await svc.list_schedules(employee_id, from_date, skip=skip, limit=limit)


@router.post(
    "/schedules", response_model=ScheduleResponse, status_code=status.HTTP_201_CREATED, dependencies=[manage_roles]
)
async def create_schedule(payload: ScheduleCreate, svc: ServiceDep):
    return await svc.create_schedule(payload)


@router.post("/attendance/clock-in", response_model=AttendanceResponse, status_code=status.HTTP_201_CREATED)
async def clock_in(payload: AttendanceClockIn, svc: ServiceDep):
    return await svc.clock_in(payload)


@router.patch("/attendance/{attendance_id}/clock-out", response_model=AttendanceResponse)
async def clock_out(attendance_id: uuid.UUID, payload: AttendanceClockOut, svc: ServiceDep):
    return await svc.clock_out(attendance_id, payload)


@router.get("/attendance", response_model=list[AttendanceResponse])
async def list_attendance(employee_id: uuid.UUID, svc: ServiceDep, skip: int = 0, limit: int = 100):
    return await svc.list_attendance(employee_id, skip=skip, limit=limit)
