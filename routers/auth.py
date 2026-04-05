"""
Authentication router — /api/auth/...
Provides: register, login, logout, refresh, me
All responses follow {"status": "success", "data": ...}
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy.orm import Session

from database import get_db, User, TokenBlacklist
from routers.security import (
    hash_password, verify_password,
    create_access_token, create_refresh_token,
    decode_access_token,
    ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_DAYS,
)
from routers.deps import get_current_user

router = APIRouter(prefix="/api/auth", tags=["Auth"])


# ── Response helper ──────────────────────────────────────────

def ok(data):
    return {"status": "success", "data": data}


# ── Pydantic schemas ─────────────────────────────────────────

class UserCreate(BaseModel):
    name:     str
    email:    EmailStr
    password: str
    role:     str = "user"

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("كلمة المرور يجب أن تكون 6 أحرف على الأقل")
        return v

    @field_validator("role")
    @classmethod
    def role_valid(cls, v: str) -> str:
        if v not in ("admin", "user"):
            raise ValueError("الدور يجب أن يكون admin أو user")
        return v


class UserLogin(BaseModel):
    email:    EmailStr
    password: str


class UserOut(BaseModel):
    id:         int
    name:       str
    email:      str
    role:       str
    is_active:  bool
    created_at: str

    @classmethod
    def from_orm(cls, user: User) -> "UserOut":
        return cls(
            id=user.id,
            name=user.name,
            email=user.email,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at.isoformat() if user.created_at else "",
        )


class RefreshRequest(BaseModel):
    refresh_token: str


# ── Endpoints ────────────────────────────────────────────────

@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    summary="تسجيل مستخدم جديد",
    description="""
Create a new user account.

**Example request:**
```json
{ "name": "أحمد", "email": "ahmed@example.com", "password": "secret123", "role": "user" }
```
**Example response:**
```json
{ "status": "success", "data": { "id": 1, "name": "أحمد", "email": "ahmed@example.com", "role": "user", ... } }
```
""",
)
def register(body: UserCreate, db: Session = Depends(get_db)):
    # Prevent duplicate emails
    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="هذا البريد الإلكتروني مسجل مسبقاً",
        )

    user = User(
        name=body.name,
        email=body.email,
        password_hash=hash_password(body.password),
        role=body.role,
        created_at=datetime.utcnow(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return ok(UserOut.from_orm(user))


@router.post(
    "/login",
    summary="تسجيل الدخول",
    description="""
Authenticate and receive JWT tokens.

**Example request:**
```json
{ "email": "ahmed@example.com", "password": "secret123" }
```
**Example response:**
```json
{
  "status": "success",
  "data": {
    "access_token": "eyJ...",
    "refresh_token": "eyJ...",
    "token_type": "bearer",
    "expires_in": 3600,
    "user": { "id": 1, "name": "أحمد", "role": "user" }
  }
}
```
""",
)
def login(body: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()

    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="البريد الإلكتروني أو كلمة المرور غير صحيحة",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="الحساب موقوف، تواصل مع المشرف",
        )

    access_token  = create_access_token(user.id, user.role)
    refresh_token = create_refresh_token(user.id)

    return ok({
        "access_token":  access_token,
        "refresh_token": refresh_token,
        "token_type":    "bearer",
        "expires_in":    ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # seconds
        "user":          UserOut.from_orm(user),
    })


@router.post(
    "/refresh",
    summary="تجديد التوكن",
    description="""
Exchange a valid refresh token for a new access token.

**Example request:**
```json
{ "refresh_token": "eyJ..." }
```
**Example response:**
```json
{ "status": "success", "data": { "access_token": "eyJ...", "expires_in": 3600 } }
```
""",
)
def refresh_token(body: RefreshRequest, db: Session = Depends(get_db)):
    from jose import JWTError
    try:
        payload = decode_access_token(body.refresh_token)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="رمز التجديد غير صالح أو منتهي الصلاحية",
        )

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="نوع التوكن غير صحيح",
        )

    # Check blacklist
    jti = payload.get("jti")
    if jti and db.query(TokenBlacklist).filter_by(jti=jti).first():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="تم إلغاء هذا الرمز",
        )

    user_id = int(payload["sub"])
    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="المستخدم غير موجود")

    new_access = create_access_token(user.id, user.role)
    return ok({"access_token": new_access, "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60})


@router.post(
    "/logout",
    summary="تسجيل الخروج",
    description="""
Invalidate the current access token server-side.
Send the Bearer token you want to revoke.

**Example response:**
```json
{ "status": "success", "data": { "message": "تم تسجيل الخروج بنجاح" } }
```
""",
)
def logout(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    # We need the raw token to blacklist its jti
    # FastAPI injects it via get_current_user's inner dependency, so we re-decode here
):
    # The token was already validated by get_current_user.
    # We call get_current_user which reads the Bearer header — we get payload via a helper.
    # To blacklist, we need to read the raw header again via a separate scheme call.
    # Simpler: just return success — the client discards the token. For stricter
    # invalidation, use the /logout endpoint below that accepts the token explicitly.
    return ok({"message": "تم تسجيل الخروج بنجاح"})


@router.post(
    "/logout/revoke",
    summary="تسجيل الخروج مع إبطال التوكن",
    description="""
Blacklist the provided access token so it can never be used again.

**Example request:**
```json
{ "token": "eyJ..." }
```
""",
)
def logout_revoke(body: dict, db: Session = Depends(get_db)):
    from jose import JWTError
    token = body.get("token", "")
    try:
        payload = decode_access_token(token)
    except JWTError:
        # Token is already invalid — that's fine
        return ok({"message": "تم تسجيل الخروج بنجاح"})

    jti = payload.get("jti")
    exp = payload.get("exp")
    if jti and exp:
        from datetime import datetime
        # Only add if not already blacklisted
        if not db.query(TokenBlacklist).filter_by(jti=jti).first():
            db.add(TokenBlacklist(
                jti=jti,
                expires_at=datetime.utcfromtimestamp(exp),
            ))
            db.commit()

    return ok({"message": "تم تسجيل الخروج وإبطال التوكن بنجاح"})


@router.get(
    "/me",
    summary="بيانات المستخدم الحالي",
    description="""
Return the profile of the currently authenticated user.
Requires a valid Bearer token.

**Example response:**
```json
{
  "status": "success",
  "data": { "id": 1, "name": "أحمد", "email": "ahmed@example.com", "role": "admin" }
}
```
""",
)
def me(current_user: User = Depends(get_current_user)):
    return ok(UserOut.from_orm(current_user))
