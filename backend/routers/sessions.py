"""
routers/sessions.py — Class session and QR code management

Handles:
  POST  /sessions/start                  → start a session + generate QR (teacher)
  POST  /sessions/{id}/refresh-qr        → regenerate QR token (teacher)
  POST  /sessions/{id}/end               → end the session (teacher)
  GET   /sessions/{id}                   → get session details (teacher/admin)
  GET   /sessions/class/{class_id}       → get all sessions for a class (teacher/admin)

How QR works:
  1. Teacher starts a session
  2. System generates a unique token and encodes it into a QR image
  3. QR token expires every 60 seconds — teacher refreshes it
  4. Students scan the QR → token is sent to the attendance endpoint
  5. System validates token and records attendance
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List
import secrets
import qrcode
import io

import models
import schemas
from database import get_db
from routers.auth import get_current_user, require_teacher

router = APIRouter(prefix="/sessions", tags=["Sessions"])

QR_EXPIRY_SECONDS = 60  # QR token refreshes every 60 seconds


def generate_qr_token() -> str:
    """Generate a cryptographically secure random token"""
    return secrets.token_urlsafe(32)  # 32 bytes = very hard to guess


def generate_qr_image(token: str) -> bytes:
    """
    Turn a token string into a QR code image.
    Returns the image as bytes so we can send it directly or upload to Cloudinary.
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(token)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    # Save image to memory buffer instead of a file
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer.getvalue()


# ─────────────────────────────────────────────
# ENDPOINTS
# ─────────────────────────────────────────────

@router.post("/start", response_model=schemas.SessionResponse, status_code=201)
def start_session(
    data: schemas.SessionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_teacher)
):
    """
    Start a new class session. Teacher/Admin only.

    How it works:
      1. Check the class exists and belongs to this teacher
      2. Check no session is already active for this class
      3. Generate a QR token with a 60 second expiry
      4. Save the session to the database
      5. Return the session with the QR token
    """
    # Check class exists
    class_ = db.query(models.Class).filter(models.Class.id == data.class_id).first()
    if not class_:
        raise HTTPException(status_code=404, detail="Class not found")

    # Teachers can only start sessions for their own classes
    if current_user.role == models.UserRole.teacher and class_.teacher_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only start sessions for your own classes")

    # Check no active session already running for this class
    active = db.query(models.Session).filter(
        models.Session.class_id == data.class_id,
        models.Session.ended_at == None  # ended_at is null = still active
    ).first()
    if active:
        raise HTTPException(status_code=400, detail="A session is already active for this class")

    # Generate token and expiry
    token      = generate_qr_token()
    expires_at = datetime.utcnow() + timedelta(seconds=QR_EXPIRY_SECONDS)

    session = models.Session(
        class_id=data.class_id,
        qr_token=token,
        qr_expires_at=expires_at,
        late_threshold_minutes=data.late_threshold_minutes
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.post("/{session_id}/refresh-qr", response_model=schemas.SessionResponse)
def refresh_qr(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_teacher)
):
    """
    Generate a new QR token for an active session.
    Called every 60 seconds to prevent QR screenshot sharing.
    """
    session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.ended_at:
        raise HTTPException(status_code=400, detail="Session has already ended")

    # Generate fresh token and reset expiry
    session.qr_token      = generate_qr_token()
    session.qr_expires_at = datetime.utcnow() + timedelta(seconds=QR_EXPIRY_SECONDS)

    db.commit()
    db.refresh(session)
    return session


@router.post("/{session_id}/end", response_model=schemas.SessionResponse)
def end_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_teacher)
):
    """
    End an active session. Teacher/Admin only.
    Once ended, no more scans are accepted for this session.
    """
    session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.ended_at:
        raise HTTPException(status_code=400, detail="Session has already ended")

    session.ended_at = datetime.utcnow()
    db.commit()
    db.refresh(session)
    return session


@router.get("/class/{class_id}", response_model=List[schemas.SessionResponse])
def get_sessions_for_class(
    class_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_teacher)
):
    """Get all sessions for a class — newest first"""
    sessions = db.query(models.Session).filter(
        models.Session.class_id == class_id
    ).order_by(models.Session.started_at.desc()).all()
    return sessions


@router.get("/{session_id}", response_model=schemas.SessionResponse)
def get_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_teacher)
):
    """Get one session by ID"""
    session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.get("/{session_id}/qr-image")
def get_qr_image(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_teacher)
):
    """
    Return the QR code as a PNG image.
    The frontend displays this image for students to scan.
    Returns 410 Gone if the token has expired — frontend should call refresh-qr first.
    """
    session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.ended_at:
        raise HTTPException(status_code=400, detail="Session has ended")

    if datetime.utcnow() > session.qr_expires_at:
        raise HTTPException(status_code=410, detail="QR code has expired — call /refresh-qr first")

    image_bytes = generate_qr_image(session.qr_token)
    return Response(content=image_bytes, media_type="image/png")
