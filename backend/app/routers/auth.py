from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas import LoginRequest, TokenResponse
from app.security import create_access_token, current_user, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.scalar(select(User).where(User.username == payload.username.strip().lower()))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Login yoki parol noto'g'ri",
        )

    return TokenResponse(
        access_token=create_access_token(user.username, user.role),
        username=user.username,
        full_name=user.full_name,
        role=user.role,
    )


@router.get("/me", response_model=TokenResponse)
def me(user: User = Depends(current_user)) -> TokenResponse:
    return TokenResponse(
        access_token="",
        username=user.username,
        full_name=user.full_name,
        role=user.role,
    )
