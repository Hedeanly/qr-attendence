"""
routers/classes.py — Class (course) management endpoints

Handles:
  POST   /classes                    → create a new class (teacher/admin)
  GET    /classes                    → get all classes
  GET    /classes/{id}               → get one class
  PUT    /classes/{id}               → edit a class (teacher/admin)
  DELETE /classes/{id}               → delete a class (admin only)
  POST   /classes/{id}/enroll        → enroll a student (admin)
  GET    /classes/{id}/students      → get all enrolled students (teacher/admin)
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

import models
import schemas
from database import get_db
from routers.auth import get_current_user, require_admin, require_teacher

router = APIRouter(prefix="/classes", tags=["Classes"])


@router.post("/", response_model=schemas.ClassResponse, status_code=201)
def create_class(
    data: schemas.ClassCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_teacher)  # teacher or admin only
):
    """
    Create a new class.
    The teacher_id is automatically set to whoever is logged in.
    """
    # Admin can assign a specific teacher, otherwise defaults to whoever is creating the class
    assigned_teacher_id = data.teacher_id if data.teacher_id else current_user.id

    new_class = models.Class(
        name=data.name,
        description=data.description,
        teacher_id=assigned_teacher_id
    )
    db.add(new_class)
    db.commit()
    db.refresh(new_class)
    return new_class


@router.get("/", response_model=List[schemas.ClassResponse])
def get_all_classes(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get all classes — visible to everyone logged in"""
    return db.query(models.Class).all()


@router.get("/{class_id}", response_model=schemas.ClassResponse)
def get_class(
    class_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get one class by ID"""
    class_ = db.query(models.Class).filter(models.Class.id == class_id).first()
    if not class_:
        raise HTTPException(status_code=404, detail="Class not found")
    return class_


@router.put("/{class_id}", response_model=schemas.ClassResponse)
def update_class(
    class_id: int,
    data: schemas.ClassUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_teacher)
):
    """
    Edit a class. Teacher/Admin only.
    Teachers can only edit their own classes.
    Admins can edit any class.
    """
    class_ = db.query(models.Class).filter(models.Class.id == class_id).first()
    if not class_:
        raise HTTPException(status_code=404, detail="Class not found")

    # Teachers can only edit their own classes
    if current_user.role == models.UserRole.teacher and class_.teacher_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only edit your own classes")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(class_, field, value)

    db.commit()
    db.refresh(class_)
    return class_


@router.delete("/{class_id}", status_code=204)
def delete_class(
    class_id: int,
    db: Session = Depends(get_db),
    admin: models.User = Depends(require_admin)  # admin only
):
    """Delete a class. Admin only."""
    class_ = db.query(models.Class).filter(models.Class.id == class_id).first()
    if not class_:
        raise HTTPException(status_code=404, detail="Class not found")

    db.delete(class_)
    db.commit()


@router.post("/{class_id}/enroll", response_model=schemas.EnrollmentResponse, status_code=201)
def enroll_student(
    class_id: int,
    data: schemas.EnrollmentCreate,
    db: Session = Depends(get_db),
    admin: models.User = Depends(require_admin)  # admin only
):
    """
    Enroll a student in a class. Admin only.
    Checks that the student exists and is not already enrolled.
    """
    # Check class exists
    class_ = db.query(models.Class).filter(models.Class.id == class_id).first()
    if not class_:
        raise HTTPException(status_code=404, detail="Class not found")

    # Check student exists and is actually a student
    student = db.query(models.User).filter(
        models.User.id == data.student_id,
        models.User.role == models.UserRole.student
    ).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # Check not already enrolled
    existing = db.query(models.Enrollment).filter(
        models.Enrollment.student_id == data.student_id,
        models.Enrollment.class_id == class_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Student already enrolled in this class")

    enrollment = models.Enrollment(student_id=data.student_id, class_id=class_id)
    db.add(enrollment)
    db.commit()
    db.refresh(enrollment)
    return enrollment


@router.get("/{class_id}/students", response_model=List[schemas.UserResponse])
def get_enrolled_students(
    class_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_teacher)
):
    """Get all students enrolled in a class. Teacher/Admin only."""
    class_ = db.query(models.Class).filter(models.Class.id == class_id).first()
    if not class_:
        raise HTTPException(status_code=404, detail="Class not found")

    enrollments = db.query(models.Enrollment).filter(
        models.Enrollment.class_id == class_id
    ).all()

    return [e.student for e in enrollments]
