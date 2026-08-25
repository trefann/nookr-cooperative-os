"""Authentication: register, sign in, one-click demo access."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_current_user
from app.core.errors import ConflictError, NotFoundError, UnauthorizedError
from app.core.security import create_access_token, hash_password, token_expires_in_seconds, verify_password
from app.db.session import get_db
from app.models import Cooperative, User, UserRole, Worker, Zone
from app.schemas.auth import (
    AuthResponse,
    DemoAccount,
    DemoLoginRequest,
    LoginRequest,
    RegisterRequest,
    UserOut,
)

router = APIRouter(prefix="/auth", tags=["auth"])

DEMO_ACCOUNTS: dict[UserRole, dict[str, str]] = {
    UserRole.CUSTOMER: {
        "email": "customer@demo.com",
        "label": "Customer Demo",
        "description": "Request a service in your own words and follow it to completion.",
    },
    UserRole.WORKER: {
        "email": "worker@demo.com",
        "label": "Worker Demo",
        "description": "Kumar Selvan, plumber. Accept jobs, run them, track earnings.",
    },
    UserRole.ADMIN: {
        "email": "admin@demo.com",
        "label": "Cooperative Admin Demo",
        "description": "The cooperative intelligence dashboard, forecasting and planning.",
    },
}


def _auth_response(db: Session, user: User) -> AuthResponse:
    worker = db.execute(
        select(Worker).where(Worker.user_id == user.id)
    ).scalar_one_or_none()
    payload = UserOut.model_validate(user).model_copy(
        update={"worker_id": worker.id if worker else None}
    )
    token = create_access_token(user.id, user.role)
    return AuthResponse(
        access_token=token,
        expires_in=token_expires_in_seconds(),
        user=payload,
    )


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> AuthResponse:
    existing = db.execute(
        select(User).where(User.email == payload.email.lower())
    ).scalar_one_or_none()
    if existing is not None:
        raise ConflictError("An account with that email already exists. Try signing in.")

    cooperative = db.execute(select(Cooperative)).scalars().first()
    zone = None
    if payload.zone_id is not None:
        zone = db.get(Zone, payload.zone_id)
        if zone is None:
            raise NotFoundError("That service zone does not exist.")
    if zone is None and cooperative is not None:
        zone = db.execute(
            select(Zone).where(Zone.cooperative_id == cooperative.id).order_by(Zone.id)
        ).scalars().first()

    user = User(
        email=payload.email.lower(),
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role=str(payload.role),
        phone=payload.phone,
        address=payload.address,
        language=payload.language,
        cooperative_id=cooperative.id if cooperative else None,
        zone_id=zone.id if zone else None,
        lat=zone.center_lat if zone else 0.0,
        lng=zone.center_lng if zone else 0.0,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _auth_response(db, user)


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> AuthResponse:
    user = db.execute(
        select(User).where(User.email == payload.email.lower())
    ).scalar_one_or_none()
    # Same message either way: never reveal whether an email is registered.
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise UnauthorizedError("That email and password combination is not recognised.")
    if not user.is_active:
        raise UnauthorizedError("This account has been deactivated.")
    return _auth_response(db, user)


@router.get("/demo-accounts", response_model=list[DemoAccount])
def demo_accounts() -> list[DemoAccount]:
    """Credentials for the three judging personas. Clearly labelled on purpose."""
    return [
        DemoAccount(
            role=str(role),
            label=meta["label"],
            email=meta["email"],
            password=settings.demo_password,
            description=meta["description"],
        )
        for role, meta in DEMO_ACCOUNTS.items()
    ]


@router.post("/demo-login", response_model=AuthResponse)
def demo_login(payload: DemoLoginRequest, db: Session = Depends(get_db)) -> AuthResponse:
    """One click into a demo persona. No registration, no typing credentials."""
    meta = DEMO_ACCOUNTS.get(payload.role)
    if meta is None:
        raise NotFoundError("No demo account exists for that role.")
    user = db.execute(
        select(User).where(User.email == meta["email"])
    ).scalar_one_or_none()
    if user is None:
        raise NotFoundError(
            "Demo accounts are missing. Seed the database with "
            "'python -m app.db.seed --reset'."
        )
    return _auth_response(db, user)


@router.get("/me", response_model=UserOut)
def me(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> UserOut:
    worker = db.execute(
        select(Worker).where(Worker.user_id == current_user.id)
    ).scalar_one_or_none()
    return UserOut.model_validate(current_user).model_copy(
        update={"worker_id": worker.id if worker else None}
    )
