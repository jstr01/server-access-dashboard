"""
Authentication module: password hashing (bcrypt), JWT token creation/verification,
FastAPI dependencies for securing routes, and admin-user seeding.
"""

import os
import secrets
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

import bcrypt
import jwt
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .models import User, UserRead
from .database import SessionLocal

logger = logging.getLogger(__name__)

# --- Load .env early so env vars are available regardless of import order ---
_dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(_dotenv_path):
    load_dotenv(dotenv_path=_dotenv_path)

# --- Configuration --------------------------------------------------------

JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET:
    JWT_SECRET = secrets.token_urlsafe(48)
    logger.warning(
        "JWT_SECRET env var not set. Using a random ephemeral secret — "
        "all tokens will be invalidated on restart. Set JWT_SECRET for production."
    )

JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

_bearer_scheme = HTTPBearer(auto_error=False)


# --- Password hashing -----------------------------------------------------

def hash_password(plain: str) -> str:
    """Hash a password with bcrypt."""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(plain.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plain-text password against a stored bcrypt hash."""
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


_dummy_hash: Optional[str] = None


def _dummy_password_hash() -> str:
    """A bcrypt hash of a random value, lazily computed once and reused to
    equalize the response time of login attempts against existing vs.
    non-existing usernames (preventing user enumeration via timing)."""
    global _dummy_hash
    if _dummy_hash is None:
        _dummy_hash = hash_password(secrets.token_urlsafe(32))
    return _dummy_hash


def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    """Look up a user and verify the password.

    A bcrypt verification is always run — even when the username does not
    exist — so response timing does not leak which usernames are registered.
    """
    user = db.query(User).filter(User.username == username).first()
    password_hash = user.password_hash if user else _dummy_password_hash()
    password_ok = verify_password(password, password_hash)
    if not user or not password_ok:
        return None
    return user


# --- JWT token helpers ----------------------------------------------------

def _create_token(subject: str, token_type: str, expires_delta: timedelta) -> str:
    now = datetime.now(tz=timezone.utc)
    payload = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def create_access_token(username: str) -> str:
    return _create_token(username, "access", timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))


def create_refresh_token(username: str) -> str:
    return _create_token(username, "refresh", timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS))


def _decode_token(token: str, expected_type: str) -> dict:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token_type = payload.get("type")
    if token_type != expected_type:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token must be of type '{expected_type}'",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload


# --- FastAPI dependencies -------------------------------------------------

def get_db() -> Session:
    """
    FastAPI dependency that provides a database session for each request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _get_user_from_token(
    credentials: Optional[HTTPAuthorizationCredentials],
    expected_type: str,
    db: Session,
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = _decode_token(credentials.credentials, expected_type)
    username = payload.get("sub")
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload missing subject",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = db.query(User).filter(User.username == username).first()
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Dependency that requires a valid **access** token."""
    return _get_user_from_token(credentials, "access", db)


def get_current_refresh_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Dependency that requires a valid **refresh** token."""
    return _get_user_from_token(credentials, "refresh", db)


# --- Admin seeding --------------------------------------------------------

def seed_admin_user(db: Session) -> None:
    """
    Create or update the bootstrap admin user from env vars at startup.
    """
    if not ADMIN_PASSWORD:
        logger.warning(
            "ADMIN_PASSWORD env var not set — no admin user seeded. "
            "Login will be unavailable until one is created."
        )
        return

    admin = db.query(User).filter(User.username == ADMIN_USERNAME).first()
    password_hash = hash_password(ADMIN_PASSWORD)
    if admin:
        admin.password_hash = password_hash
        admin.is_active = True
        logger.info(f"Admin user '{ADMIN_USERNAME}' updated.")
    else:
        admin = User(
            username=ADMIN_USERNAME,
            password_hash=password_hash,
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )
        db.add(admin)
        logger.info(f"Admin user '{ADMIN_USERNAME}' created.")
    db.commit()


def get_user_read(user: User) -> UserRead:
    return UserRead(id=user.id, username=user.username, is_active=user.is_active)
