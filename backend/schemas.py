"""
schemas.py — Data validation rules for the API

Schemas define what data is allowed IN (requests) and OUT (responses).
Built with Pydantic — it automatically validates and rejects bad data.

Rule of thumb:
  - Create schemas  → what the client sends to create something
  - Response schemas → what the API sends back (never include passwords)
  - Update schemas  → what the client sends to edit something (all optional)
"""

from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from models import UserRole, AttendanceStatus


# ─────────────────────────────────────────────
# USER SCHEMAS
# ─────────────────────────────────────────────

class UserCreate(BaseModel):
    """Data required to register a new user"""
    username: str
    email:    EmailStr  # automatically validates email format
    password: str
    role:     UserRole = UserRole.student  # default role is student


class UserResponse(BaseModel):
    """What we send back — never include the password"""
    id:         int
    username:   str
    email:      str
    role:       UserRole
    created_at: datetime

    class Config:
        from_attributes = True  # allows SQLAlchemy models to be converted to this schema


class LoginRequest(BaseModel):
    """Data required to log in"""
    username: str
    password: str


class TokenResponse(BaseModel):
    """What we send back after a successful login"""
    access_token: str
    token_type:   str = "bearer"


# ─────────────────────────────────────────────
# CLASS SCHEMAS
# ─────────────────────────────────────────────

class ClassCreate(BaseModel):
    """Data required to create a new class"""
    name:        str
    description: Optional[str] = None
    teacher_id:  Optional[int] = None  # admin can assign a teacher, otherwise defaults to self


class ClassResponse(BaseModel):
    """What we send back for a class"""
    id:          int
    name:        str
    description: Optional[str]
    teacher_id:  int
    created_at:  datetime

    class Config:
        from_attributes = True


class ClassUpdate(BaseModel):
    """All fields optional — only update what is sent"""
    name:        Optional[str] = None
    description: Optional[str] = None


# ─────────────────────────────────────────────
# ENROLLMENT SCHEMAS
# ─────────────────────────────────────────────

class EnrollmentCreate(BaseModel):
    """Data required to enroll a student in a class"""
    student_id: int
    class_id:   int


class EnrollmentResponse(BaseModel):
    id:          int
    student_id:  int
    class_id:    int
    enrolled_at: datetime

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────
# SESSION SCHEMAS
# ─────────────────────────────────────────────

class SessionCreate(BaseModel):
    """Data required to start a new session"""
    class_id:               int
    late_threshold_minutes: Optional[int] = 10  # default 10 minutes grace period


class SessionResponse(BaseModel):
    """What we send back for a session"""
    id:                     int
    class_id:               int
    qr_token:               str
    qr_expires_at:          datetime
    started_at:             datetime
    ended_at:               Optional[datetime]
    late_threshold_minutes: int

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────
# ATTENDANCE SCHEMAS
# ─────────────────────────────────────────────

class ScanRequest(BaseModel):
    """Data sent when a student scans a QR code"""
    qr_token: str  # the token encoded inside the QR code


class ManualAttendanceRequest(BaseModel):
    """Data required for teacher to manually mark a student"""
    student_id: int
    session_id: int
    status:     AttendanceStatus


class AttendanceResponse(BaseModel):
    id:                 int
    session_id:         int
    student_id:         int
    scanned_at:         datetime
    status:             AttendanceStatus
    is_manual_override: bool

    class Config:
        from_attributes = True


class AttendanceSessionResponse(BaseModel):
    """Richer response for session attendance — includes student username for display"""
    id:                 int
    session_id:         int
    student_id:         int
    student_username:   str
    scanned_at:         datetime
    status:             AttendanceStatus
    is_manual_override: bool

    class Config:
        from_attributes = True


class AttendanceHistoryResponse(BaseModel):
    """Richer response for student attendance history — includes class name for display"""
    id:                 int
    session_id:         int
    student_id:         int
    class_name:         str
    scanned_at:         datetime
    status:             AttendanceStatus
    is_manual_override: bool

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────
# RESOURCE SCHEMAS
# ─────────────────────────────────────────────

class ResourceCreate(BaseModel):
    """Data required to add a learning resource to a class"""
    class_id: int
    title:    str
    url:      str


class ResourceResponse(BaseModel):
    id:         int
    class_id:   int
    title:      str
    url:        str
    added_by:   int
    created_at: datetime

    class Config:
        from_attributes = True
