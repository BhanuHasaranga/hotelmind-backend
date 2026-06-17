import uuid
from datetime import date
from typing import Sequence

from fastapi import HTTPException, status

from app.models.staff import Attendance, Department, Employee, Schedule
from app.repositories.staff import (
    AttendanceRepository,
    DepartmentRepository,
    EmployeeRepository,
    ScheduleRepository,
)
from app.schemas.staff import (
    AttendanceClockIn,
    AttendanceClockOut,
    DepartmentCreate,
    EmployeeCreate,
    EmployeeUpdate,
    ScheduleCreate,
)


class StaffService:
    def __init__(
        self,
        dept_repo: DepartmentRepository,
        employee_repo: EmployeeRepository,
        schedule_repo: ScheduleRepository,
        attendance_repo: AttendanceRepository,
    ) -> None:
        self.dept_repo = dept_repo
        self.employee_repo = employee_repo
        self.schedule_repo = schedule_repo
        self.attendance_repo = attendance_repo

    # ── Departments ───────────────────────────────────────────────────────────

    async def list_departments(self, branch_id: uuid.UUID) -> Sequence[Department]:
        return await self.dept_repo.get_by_branch(branch_id)

    async def create_department(self, payload: DepartmentCreate) -> Department:
        return await self.dept_repo.create(payload.model_dump())

    # ── Employees ─────────────────────────────────────────────────────────────

    async def list_employees(
        self, department_id: uuid.UUID | None, skip: int, limit: int
    ) -> Sequence[Employee]:
        return await self.employee_repo.get_active(department_id=department_id, skip=skip, limit=limit)

    async def get_employee(self, employee_id: uuid.UUID) -> Employee:
        emp = await self.employee_repo.get(employee_id)
        if not emp:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
        return emp

    async def create_employee(self, payload: EmployeeCreate) -> Employee:
        return await self.employee_repo.create(payload.model_dump())

    async def update_employee(self, employee_id: uuid.UUID, payload: EmployeeUpdate) -> Employee:
        emp = await self.employee_repo.get(employee_id)
        if not emp:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
        return await self.employee_repo.update(emp, payload.model_dump(exclude_none=True))

    async def deactivate_employee(self, employee_id: uuid.UUID) -> None:
        emp = await self.employee_repo.get(employee_id)
        if not emp:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
        await self.employee_repo.update(emp, {"is_active": False})

    # ── Schedules ─────────────────────────────────────────────────────────────

    async def list_schedules(self, employee_id: uuid.UUID, from_date: date | None) -> Sequence[Schedule]:
        return await self.schedule_repo.get_by_employee(employee_id, from_date=from_date)

    async def create_schedule(self, payload: ScheduleCreate) -> Schedule:
        return await self.schedule_repo.create(payload.model_dump())

    # ── Attendance ────────────────────────────────────────────────────────────

    async def clock_in(self, payload: AttendanceClockIn) -> Attendance:
        return await self.attendance_repo.create(payload.model_dump())

    async def clock_out(self, attendance_id: uuid.UUID, payload: AttendanceClockOut) -> Attendance:
        record = await self.attendance_repo.get(attendance_id)
        if not record:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attendance record not found")
        if record.clock_out:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Already clocked out")
        return await self.attendance_repo.update(record, {"clock_out": payload.clock_out})

    async def list_attendance(self, employee_id: uuid.UUID) -> Sequence[Attendance]:
        return await self.attendance_repo.get_by_employee(employee_id)
