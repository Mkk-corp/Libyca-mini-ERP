"""
JWT token creation and verification utilities.
Reads JWT_SECRET_KEY from the environment (required in production).
Falls back to a dev-only default — Railway sets this via an environment variable.
"""
import os
import uuid
from datetime import datetime, timedelta, timezone

from jose import jwt, JWTError
from passlib.context import CryptContext

# ── Configuration ────────────────────────────────────────────

SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "CHANGE_ME_IN_PRODUCTION_USE_A_LONG_RANDOM_STRING")
ALGORITHM  = "HS256"

ACCESS_TOKEN_EXPIRE_MINUTES  = 60        # 1 hour
REFRESH_TOKEN_EXPIRE_DAYS    = 7         # 7 days

# ── Password hashing ─────────────────────────────────────────

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ── Token creation ───────────────────────────────────────────

def _make_token(data: dict, expire_delta: timedelta, token_type: str) -> str:
    payload = data.copy()
    payload.update({
        "type": token_type,
        "jti":  str(uuid.uuid4()),   # unique ID — used for blacklisting
        "exp":  datetime.now(timezone.utc) + expire_delta,
        "iat":  datetime.now(timezone.utc),
    })
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_access_token(user_id: int, role: str) -> str:
    return _make_token(
        {"sub": str(user_id), "role": role},
        timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        "access",
    )


def create_refresh_token(user_id: int) -> str:
    return _make_token(
        {"sub": str(user_id)},
        timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        "refresh",
    )


def decode_access_token(token: str) -> dict:
    """Decode and verify; raises jose.JWTError on any failure."""
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
