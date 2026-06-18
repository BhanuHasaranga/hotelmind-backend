import uuid
from datetime import date
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.staff import Attendance, Department, Employee, Schedule
from app.repositories.base import BaseRepository


class DepartmentRepository(BaseRepository[Department]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Department, db)

    async def get_by_branch(self, branch_id: uuid.UUID) -> Sequence[Department]:
        result = await self.db.execute(
            select(Department).where(Department.branch_id == branch_id)
        )
        return result.scalars().all()


class EmployeeRepository(BaseRepository[Employee]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Employee, db)

    async def get_with_department(self, employee_id: uuid.UUID) -> Employee | None:
        result = await self.db.execute(
            select(Employee)
            .options(selectinload(Employee.department))
            .where(Employee.id == employee_id)
        )
        return result.scalar_one_or_none()

    async def get_active(
        self, department_id: uuid.UUID | None = None, skip: int = 0, limit: int = 100
    ) -> Sequence[Employee]:
        query = (
            select(Employee)
            .options(selectinload(Employee.department))
            .where(Employee.is_active == True)  # noqa: E712
            .offset(skip)
            .limit(limit)
        )
        if department_id:
            query = query.where(Employee.department_id == department_id)
        result = await self.db.execute(query)
        return result.scalars().all()


class ScheduleRepository(BaseRepository[Schedule]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Schedule, db)

    async def get_by_employee(
        self, employee_id: uuid.UUID, from_date: date | None = None, skip: int = 0, limit: int = 100
    ) -> Sequence[Schedule]:
        query = select(Schedule).where(Schedule.employee_id == employee_id).offset(skip).limit(limit)
        if from_date:
            query = query.where(Schedule.shift_date >= from_date)
        result = await self.db.execute(query)
        return result.scalars().all()


class AttendanceRepository(BaseRepository[Attendance]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Attendance, db)

    async def get_by_employee(
        self, employee_id: uuid.UUID, skip: int = 0, limit: int = 100
    ) -> Sequence[Attendance]:
        result = await self.db.execute(
            select(Attendance)
            .where(Attendance.employee_id == employee_id)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()
