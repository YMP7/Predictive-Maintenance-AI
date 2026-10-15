import os
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import Depends, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from jose import JWTError, jwt
from pydantic import BaseModel
import bcrypt

# Security configurations
# Generate a secret with:  openssl rand -hex 32
_secret = os.environ.get("JWT_SECRET_KEY")
if not _secret:
    raise RuntimeError(
        "FATAL: JWT_SECRET_KEY environment variable is not set. "
        "Generate one with: openssl rand -hex 32  "
        "and add it to your .env file."
    )
SECRET_KEY = _secret
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 1 day

class Token(BaseModel):
    access_token: str
    token_type: str
    role: str

class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None

class User(BaseModel):
    username: str
    role: str

def get_password_hash(password: str) -> str:
    """Hash password, truncating to 72 bytes (bcrypt limit)."""
    # Truncate to 72 bytes to comply with bcrypt limitation
    truncated_password = password.encode('utf-8')[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(truncated_password, salt).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash."""
    # Also truncate here for consistency
    truncated_password = plain_password.encode('utf-8')[:72]
    hashed_password_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(truncated_password, hashed_password_bytes)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# User lookup via TimescaleDB (replaces the old fake_users_db in-memory dict)
def get_user_from_db(username: str) -> dict | None:
    """Query the users table for a single user by username."""
    from server.database import pool  # lazy: keeps auth importable without DATABASE_URL
    with pool.connection() as conn:
        row = conn.execute(
            "SELECT username, hashed_password, role FROM users WHERE username = %s",
            (username,)
        ).fetchone()
        if row:
            return {"username": row[0], "hashed_password": row[1], "role": row[2]}
    return None

async def get_current_user(request: Request) -> User:
    # Already verified by the login middleware for this request (backend_api.py).
    cached = getattr(request.state, "user", None)
    if cached is not None:
        return cached

    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
    )
    
    # CSRF Protection: Require custom header
    if request.headers.get("X-API-Request") != "true":
        raise HTTPException(
            status_code=403, 
            detail="Missing CSRF protection header (X-API-Request)"
        )

    token = request.cookies.get("access_token")
    if not token:
        raise credentials_exception

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username, role=payload.get("role"))
    except JWTError:
        raise credentials_exception
        
    # Blocking DB call: run it off the event loop.
    user_dict = await run_in_threadpool(get_user_from_db, token_data.username)
    if user_dict is None:
        raise credentials_exception
    return User(**user_dict)

async def require_admin(current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not enough privileges")
    return current_user

async def require_operator_or_admin(current_user: User = Depends(get_current_user)):
    if current_user.role not in ["admin", "operator"]:
        raise HTTPException(status_code=403, detail="Not enough privileges")
    return current_user
