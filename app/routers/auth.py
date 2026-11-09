from fastapi import APIRouter, HTTPException, status

from sqlalchemy.exc import IntegrityError

from app.core.dependencies import DatabaseSession
from app.core.security import create_access_token
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
)
from app.schemas.user import UserResponse
from app.services.auth import authenticate_user, create_user, get_user_by_email


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    data: RegisterRequest,
    db: DatabaseSession,
) -> UserResponse:
    existing_user = await get_user_by_email(
        db,
        str(data.email),
    )

    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email already exists",
        )

    try:
        user = await create_user(
            db,
            data,
        )

    except IntegrityError:
        await db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email already exists",
        ) from None

    return UserResponse.model_validate(user)


@router.post(
    "/login",
    response_model=TokenResponse,
)
async def login(
    data: LoginRequest,
    db: DatabaseSession,
) -> TokenResponse:
    user = await authenticate_user(
        db,
        str(data.email),
        data.password,
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        subject=str(user.id),
    )

    return TokenResponse(
        access_token=access_token,
    )