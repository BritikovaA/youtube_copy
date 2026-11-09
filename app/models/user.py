from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum as SQLAlchemyEnum
from sqlalchemy import String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


if TYPE_CHECKING:
    from app.models.video import Video


class UserRole(str, Enum):
    USER = "user"
    MODERATOR = "moderator"
    ADMIN = "admin"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )

    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    role: Mapped[UserRole] = mapped_column(
        SQLAlchemyEnum(
            UserRole,
            name="user_role",
            native_enum=False,
            create_constraint=False,
            values_callable=lambda enum_cls: [
                member.value for member in enum_cls
            ],
            length=20,
        ),
        nullable=False,
        default=UserRole.USER,
        server_default=UserRole.USER.value,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    videos: Mapped[list["Video"]] = relationship(
        "Video",
        back_populates="owner",
        cascade="all, delete-orphan",
    )