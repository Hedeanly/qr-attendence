"""
routers/attendance.py — Attendance scanning and recording

Handles:
  POST  /attendance/scan              → student scans QR code
  POST  /attendance/manual            → teacher manually marks a student
  GET   /attendance/session/{id}      → get all attendance for a session
  GET   /attendance/student/{id}      → get a student's attendance history
  GET   /attendance/summary/{class_id} → get attendance % per student for a class
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List


import models
import schemas
from database import get_db
from routers.auth import get_current_user, require_teacher

router = APIRouter(prefix="/attendance", tags=["Attendance"])


@router.post("/scan", response_model=schemas.AttendanceResponse, status_code=201)
def scan_qr(
    data: schemas.ScanRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)  # any logged in user
):
    """
    Record attendance by scanning a QR code.

    Anti-cheat checks in order:
      1. Token must exist in an active session
      2. Session must not be ended
      3. Token must not be expired (60 second window)
      4. Student must be enrolled in this class
      5. Student must not have already scanned this session
    """

    # ── CHECK 1: Find the session with this token ──
    session = db.query(models.Session).filter(
        models.Session.qr_token == data.qr_token
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Invalid QR code")

    # ── CHECK 2: Session must still be active ──
    if session.ended_at:
        raise HTTPException(status_code=400, detail="This session has already ended")

    # ── CHECK 3: Token must not be expired ──
    if datetime.utcnow() > session.qr_expires_at:
        raise HTTPException(status_code=400, detail="QR code has expired — ask your teacher to refresh it")

    # ── CHECK 4: Student must be enrolled in this class ──
    enrollment = db.query(models.Enrollment).filter(
        models.Enrollment.student_id == current_user.id,
        models.Enrollment.class_id == session.class_id
    ).first()

    if not enrollment:
        raise HTTPException(status_code=403, detail="You are not enrolled in this class")

    # ── CHECK 5: Student must not have already scanned ──
    already_scanned = db.query(models.Attendance).filter(
        models.Attendance.session_id == session.id,
        models.Attendance.student_id == current_user.id
    ).first()

    if already_scanned:
        raise HTTPException(status_code=400, detail="You have already scanned for this session")

    # ── DETERMINE STATUS: present or late ──
    # Calculate how many minutes since session started
    minutes_since_start = (datetime.utcnow() - session.started_at).total_seconds() / 60

    if minutes_since_start <= session.late_threshold_minutes:
        status = models.AttendanceStatus.present
    else:
        status = models.AttendanceStatus.late

    # ── RECORD ATTENDANCE ──
    attendance = models.Attendance(
        session_id=session.id,
        student_id=current_user.id,
        status=status,
        is_manual_override=False
    )
    db.add(attendance)
    db.commit()
    db.refresh(attendance)
    return attendance


@router.post("/manual", response_model=schemas.AttendanceResponse, status_code=201)
def manual_mark(
    data: schemas.ManualAttendanceRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_teacher)
):
    """
    Manually mark a student's attendance. Teacher/Admin only.
    Flagged as is_manual_override=True for audit trail.
    Used when a student has no internet or forgot to scan.
    """
    # Check session exists
    session = db.query(models.Session).filter(
        models.Session.id == data.session_id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Check student exists
    student = db.query(models.User).filter(
        models.User.id == data.student_id,
        models.User.role == models.UserRole.student
    ).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # Check enrollment
    enrollment = db.query(models.Enrollment).filter(
        models.Enrollment.student_id == data.student_id,
        models.Enrollment.class_id == session.class_id
    ).first()
    if not enrollment:
        raise HTTPException(status_code=403, detail="Student is not enrolled in this class")

    # Check not already marked
    existing = db.query(models.Attendance).filter(
        models.Attendance.session_id == data.session_id,
        models.Attendance.student_id == data.student_id
    ).first()
    if existing:
        # Update existing record instead of creating a duplicate
        existing.status = data.status
        existing.is_manual_override = True
        db.commit()
        db.refresh(existing)
        return existing

    # Create new attendance record
    attendance = models.Attendance(
        session_id=data.session_id,
        student_id=data.student_id,
        status=data.status,
        is_manual_override=True  # flagged for audit trail
    )
    db.add(attendance)
    db.commit()
    db.refresh(attendance)
    return attendance


@router.get("/session/{session_id}", response_model=List[schemas.AttendanceSessionResponse])
def get_session_attendance(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_teacher)
):
    """Get all attendance records for a session — teacher/admin only"""
    session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    records = db.query(models.Attendance).filter(
        models.Attendance.session_id == session_id
    ).all()

    # Attach student username to each record for display on the frontend
    result = []
    for record in records:
        student = db.query(models.User).filter(models.User.id == record.student_id).first()
        result.append(schemas.AttendanceSessionResponse(
            id=record.id,
            session_id=record.session_id,
            student_id=record.student_id,
            student_username=student.username if student else "Unknown",
            scanned_at=record.scanned_at,
            status=record.status,
            is_manual_override=record.is_manual_override,
        ))
    return result


@router.get("/student/{student_id}", response_model=List[schemas.AttendanceHistoryResponse])
def get_student_attendance(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Get a student's full attendance history.
    Students can only view their own — teachers and admins can view anyone's.
    """
    # Students can only see their own attendance
    if current_user.role == models.UserRole.student and current_user.id != student_id:
        raise HTTPException(status_code=403, detail="You can only view your own attendance")

    records = db.query(models.Attendance).filter(
        models.Attendance.student_id == student_id
    ).order_by(models.Attendance.scanned_at.desc()).all()

    # Attach class name to each record by following: attendance → session → class
    result = []
    for record in records:
        session = db.query(models.Session).filter(models.Session.id == record.session_id).first()
        cls = db.query(models.Class).filter(models.Class.id == session.class_id).first() if session else None
        result.append(schemas.AttendanceHistoryResponse(
            id=record.id,
            session_id=record.session_id,
            student_id=record.student_id,
            class_name=cls.name if cls else "Unknown",
            scanned_at=record.scanned_at,
            status=record.status,
            is_manual_override=record.is_manual_override,
        ))
    return result


@router.get("/summary/{class_id}")
def get_class_attendance_summary(
    class_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_teacher)
):
    """
    Get attendance summary for all students in a class.
    Returns each student's attendance percentage and status breakdown.
    Used for the dashboard and at-risk student detection.
    """
    # Get all sessions for this class
    sessions = db.query(models.Session).filter(
        models.Session.class_id == class_id
    ).all()
    total_sessions = len(sessions)

    if total_sessions == 0:
        return {"class_id": class_id, "total_sessions": 0, "students": []}

    session_ids = [s.id for s in sessions]

    # Get all enrolled students
    enrollments = db.query(models.Enrollment).filter(
        models.Enrollment.class_id == class_id
    ).all()

    summary = []
    for enrollment in enrollments:
        student = enrollment.student

        # Count each status for this student
        records = db.query(models.Attendance).filter(
            models.Attendance.student_id == student.id,
            models.Attendance.session_id.in_(session_ids)
        ).all()

        present_count = sum(1 for r in records if r.status == models.AttendanceStatus.present)
        late_count    = sum(1 for r in records if r.status == models.AttendanceStatus.late)
        absent_count  = total_sessions - len(records)  # sessions with no scan = absent

        attendance_pct = round((present_count + late_count) / total_sessions * 100, 1)

        summary.append({
            "student_id":      student.id,
            "username":        student.username,
            "email":           student.email,
            "present":         present_count,
            "late":            late_count,
            "absent":          absent_count,
            "total_sessions":  total_sessions,
            "attendance_pct":  attendance_pct,
            "at_risk":         attendance_pct < 75  # flag if below 75%
        })

    return {"class_id": class_id, "total_sessions": total_sessions, "students": summary}
