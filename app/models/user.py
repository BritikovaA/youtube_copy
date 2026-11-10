from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    Enum as SQLAlchemyEnum,
    ForeignKey,
    Integer,
    UniqueConstraint,
    func,
)
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
        Integer,
        primary_key=True,
        index=True,
    )

    email: Mapped[str] = mapped_column(
        nullable=False,
        unique=True,
        index=True,
    )

    hashed_password: Mapped[str] = mapped_column(
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

    # Подписки, оформленные этим пользователем.
    subscriptions: Mapped[list["Subscription"]] = relationship(
        "Subscription",
        foreign_keys="Subscription.subscriber_id",
        back_populates="subscriber",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    # Подписчики этого пользователя.
    subscribers: Mapped[list["Subscription"]] = relationship(
        "Subscription",
        foreign_keys="Subscription.channel_id",
        back_populates="channel",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class Subscription(Base):
    __tablename__ = "subscriptions"

    __table_args__ = (
        UniqueConstraint(
            "subscriber_id",
            "channel_id",
            name="uq_subscriptions_subscriber_channel",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    subscriber_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    channel_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    subscriber: Mapped["User"] = relationship(
        "User",
        foreign_keys=[subscriber_id],
        back_populates="subscriptions",
    )

    channel: Mapped["User"] = relationship(
        "User",
        foreign_keys=[channel_id],
        back_populates="subscribers",
    )