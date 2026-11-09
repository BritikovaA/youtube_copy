from fastapi import APIRouter

from app.core.dependencies import CurrentUser
from app.schemas.user import UserResponse


router = APIRouter(
    prefix="/users",
    tags=["Users"],
)


@router.get(
    "/me",
    response_model=UserResponse,
)
async def get_my_profile(
    current_user: CurrentUser,
) -> UserResponse:
    return UserResponse.model_validate(current_user)