"""
models.py — Database table definitions

Each class here = one table in the database.
SQLAlchemy reads these and creates the actual tables automatically.

Tables:
  - User        → all users (admin, teacher, student)
  - Class       → a subject/course
  - Enrollment  → which students are in which class
  - Session     → a single class meeting with a QR code
  - Attendance  → a student's scan record for a session
  - Resource    → learning materials linked to a class
"""

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from database import Base


# ─────────────────────────────────────────────
# ENUMS — fixed set of allowed values
# ─────────────────────────────────────────────

class UserRole(str, enum.Enum):
    admin   = "admin"
    teacher = "teacher"
    student = "student"

class AttendanceStatus(str, enum.Enum):
    present = "present"
    late    = "late"
    absent  = "absent"


# ─────────────────────────────────────────────
# USER
# Stores all users regardless of role
# ─────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id              = Column(Integer, primary_key=True, index=True)
    username        = Column(String, unique=True, nullable=False)
    email           = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role            = Column(Enum(UserRole), nullable=False, default=UserRole.student)
    created_at      = Column(DateTime, default=datetime.utcnow)

    # Relationships
    taught_classes  = relationship("Class", back_populates="teacher")
    enrollments     = relationship("Enrollment", back_populates="student")
    attendance      = relationship("Attendance", back_populates="student")


# ─────────────────────────────────────────────
# CLASS
# A subject or course taught by a teacher
# ─────────────────────────────────────────────

class Class(Base):
    __tablename__ = "classes"

    id          = Column(Integer, primary_key=True, index=True)
    name        = Column(String, nullable=False)
    description = Column(String)
    teacher_id  = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at  = Column(DateTime, default=datetime.utcnow)

    # Relationships
    teacher     = relationship("User", back_populates="taught_classes")
    enrollments = relationship("Enrollment", back_populates="class_", cascade="all, delete-orphan")
    sessions    = relationship("Session", back_populates="class_", cascade="all, delete-orphan")
    resources   = relationship("Resource", back_populates="class_", cascade="all, delete-orphan")


# ─────────────────────────────────────────────
# ENROLLMENT
# Links students to classes they are enrolled in
# ─────────────────────────────────────────────

class Enrollment(Base):
    __tablename__ = "enrollments"

    id          = Column(Integer, primary_key=True, index=True)
    student_id  = Column(Integer, ForeignKey("users.id"), nullable=False)
    class_id    = Column(Integer, ForeignKey("classes.id"), nullable=False)
    enrolled_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    student     = relationship("User", back_populates="enrollments")
    class_      = relationship("Class", back_populates="enrollments")


# ─────────────────────────────────────────────
# SESSION
# A single class meeting started by a teacher
# Contains the temporary QR code for that meeting
# ─────────────────────────────────────────────

class Session(Base):
    __tablename__ = "sessions"

    id                      = Column(Integer, primary_key=True, index=True)
    class_id                = Column(Integer, ForeignKey("classes.id"), nullable=False)
    qr_token                = Column(String, unique=True, nullable=False)  # the token encoded in the QR
    qr_expires_at           = Column(DateTime, nullable=False)             # token expires every 60 seconds
    started_at              = Column(DateTime, default=datetime.utcnow)
    ended_at                = Column(DateTime, nullable=True)              # null = session still active
    late_threshold_minutes  = Column(Integer, default=10)                  # scans after this = late

    # Relationships
    class_      = relationship("Class", back_populates="sessions")
    attendance  = relationship("Attendance", back_populates="session", cascade="all, delete-orphan")


# ─────────────────────────────────────────────
# ATTENDANCE
# Records a student's attendance for a session
# ─────────────────────────────────────────────

class Attendance(Base):
    __tablename__ = "attendance"

    id                 = Column(Integer, primary_key=True, index=True)
    session_id         = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    student_id         = Column(Integer, ForeignKey("users.id"), nullable=False)
    scanned_at         = Column(DateTime, default=datetime.utcnow)
    status             = Column(Enum(AttendanceStatus), nullable=False, default=AttendanceStatus.present)
    is_manual_override = Column(Boolean, default=False)  # flagged if teacher marked manually

    # Relationships
    session = relationship("Session", back_populates="attendance")
    student = relationship("User", back_populates="attendance")


# ─────────────────────────────────────────────
# RESOURCE
# Learning materials linked to a class
# ─────────────────────────────────────────────

class Resource(Base):
    __tablename__ = "resources"

    id         = Column(Integer, primary_key=True, index=True)
    class_id   = Column(Integer, ForeignKey("classes.id"), nullable=False)
    title      = Column(String, nullable=False)
    url        = Column(String, nullable=False)
    added_by   = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    class_ = relationship("Class", back_populates="resources")
