from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.config import settings
from app.core.security import create_access_token
from app.schemas.auth import (
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
)
from app.schemas.user import UserPublic, UserUpdate, UsernameCheck, UsernameAvailable
from app.services.auth_service import create_user, authenticate_user, get_user_by_email, get_user_by_username, update_user
from app.services.password_reset_service import create_password_reset, reset_password
from app.dependencies.auth import get_current_user
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserPublic, status_code=201)
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    if get_user_by_email(db, data.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    if data.username:
        clean = data.username.strip().lstrip("@").lower()
        existing = get_user_by_username(db, clean)
        if existing:
            raise HTTPException(status_code=409, detail="Ce nom d'utilisateur est déjà pris.")
    return create_user(db, data)


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = authenticate_user(db, data.email, data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token(
        {"sub": user.id},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return TokenResponse(access_token=token)


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
def forgot_password(data: ForgotPasswordRequest, db: Session = Depends(get_db)):
    email_sent, dev_reset_url = create_password_reset(db, str(data.email))
    message = (
        "Si un compte existe pour cet email, un lien de réinitialisation a été préparé."
        if email_sent
        else "Si un compte existe pour cet email, la demande a été prise en compte. En local/dev, le lien est affiché ci-dessous et dans les logs serveur."
    )
    return ForgotPasswordResponse(
        message=message,
        email_sent=email_sent,
        dev_reset_url=dev_reset_url if settings.APP_ENV != "production" else None,
    )


@router.post("/reset-password")
def reset_password_route(data: ResetPasswordRequest, db: Session = Depends(get_db)):
    if len(data.password) < 8:
        raise HTTPException(status_code=400, detail="Le mot de passe doit contenir au moins 8 caractères.")
    if data.password != data.password_confirm:
        raise HTTPException(status_code=400, detail="Les mots de passe ne correspondent pas.")
    if not reset_password(db, data.token, data.password):
        raise HTTPException(status_code=400, detail="Lien de réinitialisation invalide ou expiré.")
    return {"message": "Mot de passe mis à jour."}


@router.get("/me", response_model=UserPublic)
def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch("/me", response_model=UserPublic)
def patch_me(
    data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return update_user(db, current_user, data)


@router.post("/username/check", response_model=UsernameAvailable)
def check_username(data: UsernameCheck, db: Session = Depends(get_db)):
    clean = data.username.strip().lstrip("@").lower()
    existing = get_user_by_username(db, clean)
    return UsernameAvailable(available=existing is None)


@router.post("/logout")
def logout():
    return {"message": "Logged out. Discard your token client-side."}
