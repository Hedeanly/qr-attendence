"""
routers/auth.py — Authentication endpoints

Handles:
  POST /auth/register  → create a new user (admin only)
  POST /auth/login     → login and get JWT token
  GET  /auth/me        → get current logged in user
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os

import models
import schemas
from database import get_db

load_dotenv()

router = APIRouter(prefix="/auth", tags=["Auth"])

# ─────────────────────────────────────────────
# PASSWORD HASHING
# Never store plain text passwords — always hash them
# bcrypt turns "admin123" into a long scrambled string
# ─────────────────────────────────────────────

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """Turn a plain password into a hashed string"""
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    """Check if a plain password matches the stored hash"""
    return pwd_context.verify(plain, hashed)


# ─────────────────────────────────────────────
# JWT TOKEN
# After login, we give the user a token
# They send this token with every future request
# so we know who they are without logging in again
# ─────────────────────────────────────────────

SECRET_KEY = os.getenv("SECRET_KEY", "change-this")
ALGORITHM  = "HS256"
EXPIRE_MIN = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60))

def create_token(data: dict) -> str:
    """Generate a JWT token with an expiry time"""
    payload = data.copy()
    payload["exp"] = datetime.utcnow() + timedelta(minutes=EXPIRE_MIN)
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> dict:
    """Decode and verify a JWT token — raises error if invalid or expired"""
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )


# ─────────────────────────────────────────────
# AUTH DEPENDENCY
# Used in other routers to protect endpoints
# Example: admin = Depends(get_current_user)
# ─────────────────────────────────────────────

from fastapi.security import OAuth2PasswordBearer
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> models.User:
    """Decode the token and return the logged in user from the database"""
    payload = decode_token(token)
    username = payload.get("sub")  # "sub" is standard JWT field for the subject (username)

    if not username:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(models.User).filter(models.User.username == username).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user

def require_admin(current_user: models.User = Depends(get_current_user)) -> models.User:
    """Only allow admin users — raises 403 if not admin"""
    if current_user.role != models.UserRole.admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

def require_teacher(current_user: models.User = Depends(get_current_user)) -> models.User:
    """Only allow teachers and admins"""
    if current_user.role not in [models.UserRole.teacher, models.UserRole.admin]:
        raise HTTPException(status_code=403, detail="Teacher access required")
    return current_user


# ─────────────────────────────────────────────
# ENDPOINTS
# ─────────────────────────────────────────────

@router.post("/register", response_model=schemas.UserResponse, status_code=201)
def register(
    data: schemas.UserCreate,
    db: Session = Depends(get_db),
    admin: models.User = Depends(require_admin)  # only admin can create users
):
    """
    Register a new user. Admin only.
    Admin creates accounts for teachers and students.
    """
    # Check if username or email already exists
    existing = db.query(models.User).filter(
        (models.User.username == data.username) |
        (models.User.email == data.email)
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Username or email already exists")

    user = models.User(
        username=data.username,
        email=data.email,
        hashed_password=hash_password(data.password),
        role=data.role
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=schemas.TokenResponse)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Login with username and password.
    Returns a JWT token to use in future requests.
    """
    user = db.query(models.User).filter(models.User.username == form_data.username).first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = create_token({"sub": user.username, "role": user.role})
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me", response_model=schemas.UserResponse)
def get_me(current_user: models.User = Depends(get_current_user)):
    """
    Return the currently logged in user's info.
    Useful for the frontend to know who is logged in and their role.
    """
    return current_user


@router.get("/users", response_model=list[schemas.UserResponse])
def get_users(
    db: Session = Depends(get_db),
    admin: models.User = Depends(require_admin)
):
    """Return all users — admin only"""
    return db.query(models.User).order_by(models.User.role, models.User.username).all()
