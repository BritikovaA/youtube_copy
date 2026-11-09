from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.database import get_db
from app.models.user import User, UserRole
from app.services.auth import get_user_by_email


security = HTTPBearer(
    auto_error=False,
)


async def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(security),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    unauthorized_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired authentication token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credentials is None:
        raise unauthorized_exception

    try:
        payload = decode_access_token(
            credentials.credentials,
        )

        subject = payload.get("sub")
        token_type = payload.get("type")

        if (
            not isinstance(subject, str)
            or not subject.isdigit()
            or token_type != "access"
        ):
            raise unauthorized_exception

        user_id = int(subject)

    except (JWTError, ValueError):
        raise unauthorized_exception from None

    from sqlalchemy import select

    result = await db.execute(
        select(User).where(User.id == user_id),
    )

    user = result.scalar_one_or_none()

    if user is None:
        raise unauthorized_exception

    return user


def require_roles(
    *allowed_roles: UserRole,
) -> Callable[..., User]:
    def role_checker(
        current_user: Annotated[
            User,
            Depends(get_current_user),
        ],
    ) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action",
            )

        return current_user

    return role_checker


CurrentUser = Annotated[
    User,
    Depends(get_current_user),
]

DatabaseSession = Annotated[
    AsyncSession,
    Depends(get_db),
]