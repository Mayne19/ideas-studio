from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.config import settings
from app.core.rate_limit import enforce_auth_rate_limit
from app.core.security import create_access_token
from app.schemas.auth import (
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginRequest,
    RegisterRequest,
    RegistrationSettingsUpdate,
    RegistrationStatus,
    ResetPasswordRequest,
    TokenResponse,
)
from app.schemas.user import UserPublic, UserUpdate, UsernameCheck, UsernameAvailable
from app.services.auth_service import create_user, authenticate_user, get_user_by_email, get_user_by_username, update_user
from app.services.password_reset_service import create_password_reset, reset_password
from app.services.invitation_service import accept_invitation, get_invitation_by_token, registration_invitation_error
from app.services.platform_settings_service import is_open_registration, set_open_registration
from app.dependencies.auth import get_current_user
from app.models.core import User

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserPublic, status_code=201)
def register(data: RegisterRequest, request: Request, db: Session = Depends(get_db)):
    enforce_auth_rate_limit(request, "register", str(data.email))
    # Inscription libre fermée par défaut : il faut une invitation valide,
    # sauf pour le tout premier compte (initialisation de l'instance) ou si
    # le staff a ouvert les inscriptions (Compte → Administration).
    invitation = None
    if data.invitation_token:
        invitation = get_invitation_by_token(db, data.invitation_token)
        error = registration_invitation_error(invitation, str(data.email))
        if error:
            raise HTTPException(status_code=403, detail=error)
    elif not _registration_open(db):
        raise HTTPException(
            status_code=403,
            detail="Les inscriptions sont fermées : demandez une invitation à un administrateur.",
        )
    if get_user_by_email(db, data.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    if data.username:
        clean = data.username.strip().lstrip("@").lower()
        existing = get_user_by_username(db, clean)
        if existing:
            raise HTTPException(status_code=409, detail="Ce nom d'utilisateur est déjà pris.")
    user = create_user(db, data)
    if invitation is not None:
        accept_invitation(db, invitation, user)
        db.commit()
        db.refresh(user)
    return user


def _registration_open(db: Session) -> bool:
    """Ouverte si le staff l'a activée, ou si l'instance n'a encore aucun
    compte (le premier inscrit devient staff, voir create_user)."""
    if is_open_registration(db):
        return True
    return db.execute(select(User.id).limit(1)).scalar_one_or_none() is None


@router.get("/registration-status", response_model=RegistrationStatus)
def registration_status(db: Session = Depends(get_db)):
    """Public : la page d'inscription affiche un message si c'est fermé."""
    return RegistrationStatus(open=_registration_open(db))


@router.get("/registration-settings", response_model=RegistrationStatus)
def get_registration_settings(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _require_staff(current_user)
    return RegistrationStatus(open=is_open_registration(db))


@router.put("/registration-settings", response_model=RegistrationStatus)
def update_registration_settings(
    data: RegistrationSettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_staff(current_user)
    return RegistrationStatus(open=set_open_registration(db, data.open, current_user.id))


def _require_staff(user: User) -> None:
    if not user.is_staff:
        raise HTTPException(status_code=403, detail="Réservé à l'administrateur de l'instance.")


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, request: Request, db: Session = Depends(get_db)):
    enforce_auth_rate_limit(request, "login", str(data.email))
    user = authenticate_user(db, data.email, data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token(
        {"sub": user.id},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return TokenResponse(access_token=token)


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
def forgot_password(data: ForgotPasswordRequest, request: Request, db: Session = Depends(get_db)):
    enforce_auth_rate_limit(request, "forgot-password", str(data.email))
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
