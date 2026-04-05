"""
Shared FastAPI dependencies for authentication.
Import `get_current_user` or `require_admin` in any route that needs protection.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import JWTError

from database import get_db, User, TokenBlacklist
from routers.security import decode_access_token

bearer_scheme = HTTPBearer(auto_error=True)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Validate the Bearer JWT and return the matching User row.
    Raises HTTP 401 on any failure (missing token, expired, blacklisted, unknown user).
    """
    token = credentials.credentials
    try:
        payload = decode_access_token(token)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="توكن غير صالح أو منتهي الصلاحية",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check token type
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="نوع التوكن غير صحيح",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check blacklist (logout)
    jti = payload.get("jti")
    if jti and db.query(TokenBlacklist).filter_by(jti=jti).first():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="تم تسجيل الخروج بالفعل، يرجى تسجيل الدخول من جديد",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="توكن غير صالح")

    user = db.query(User).filter(User.id == int(user_id), User.is_active == True).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="المستخدم غير موجود أو محظور",
        )
    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Raises HTTP 403 unless the user has the 'admin' role."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="هذه العملية تتطلب صلاحيات المشرف",
        )
    return current_user
