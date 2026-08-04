import uuid

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    # OWNER | REVENUE_MANAGER | OPS_MANAGER | RESTAURANT_MANAGER | GUEST_EXPERIENCE_MANAGER
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    # null == OWNER (all-branch access); every other role is scoped to one branch
    branch_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("branches.id"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
