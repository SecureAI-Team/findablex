"""Security utilities for password hashing and JWT tokens."""
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import bcrypt
from jose import JWTError, jwt

from app.config import settings


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return bcrypt.checkpw(
        plain_password.encode('utf-8'),
        hashed_password.encode('utf-8')
    )


def hash_password(password: str) -> str:
    """Hash a password."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    
    return encoded_jwt


def decode_token(token: str) -> Dict[str, Any]:
    """Decode and verify a JWT token."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
        return payload
    except JWTError as e:
        raise ValueError(f"Invalid token: {e}")


def create_refresh_token(user_id: str) -> str:
    """Create a refresh token with longer expiry."""
    expire = datetime.now(timezone.utc) + timedelta(days=7)
    to_encode = {"sub": user_id, "exp": expire, "type": "refresh"}
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_password_reset_token(user_id: str) -> str:
    """Create a password reset token with 24 hour expiry."""
    expire = datetime.now(timezone.utc) + timedelta(hours=24)
    to_encode = {"sub": user_id, "exp": expire, "type": "password_reset"}
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def verify_password_reset_token(token: str) -> Optional[str]:
    """Verify a password reset token and return user_id if valid."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
        
        # Verify token type
        if payload.get("type") != "password_reset":
            return None
        
        return payload.get("sub")
    except JWTError:
        return None


def verify_refresh_token(token: str) -> Optional[str]:
    """Verify a refresh token and return user_id if valid."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
        
        # Verify token type
        if payload.get("type") != "refresh":
            return None
        
        return payload.get("sub")
    except JWTError:
        return None
