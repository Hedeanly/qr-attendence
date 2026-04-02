"""
routers/resources.py — Learning resources per class

Handles:
  POST   /resources              → add a resource to a class (teacher/admin)
  GET    /resources/class/{id}   → get all resources for a class (any logged in user)
  DELETE /resources/{id}         → delete a resource (teacher/admin)
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

import models
import schemas
from database import get_db
from routers.auth import get_current_user, require_teacher

router = APIRouter(prefix="/resources", tags=["Resources"])


@router.post("/", response_model=schemas.ResourceResponse, status_code=201)
def add_resource(
    data: schemas.ResourceCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_teacher)
):
    """
    Add a learning resource to a class. Teacher/Admin only.
    added_by is automatically set to the logged in user.
    """
    # Check class exists
    class_ = db.query(models.Class).filter(models.Class.id == data.class_id).first()
    if not class_:
        raise HTTPException(status_code=404, detail="Class not found")

    # Teachers can only add resources to their own classes
    if current_user.role == models.UserRole.teacher and class_.teacher_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only add resources to your own classes")

    resource = models.Resource(
        class_id=data.class_id,
        title=data.title,
        url=data.url,
        added_by=current_user.id
    )
    db.add(resource)
    db.commit()
    db.refresh(resource)
    return resource


@router.get("/class/{class_id}", response_model=List[schemas.ResourceResponse])
def get_class_resources(
    class_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)  # any logged in user
):
    """Get all resources for a class — visible to all logged in users"""
    class_ = db.query(models.Class).filter(models.Class.id == class_id).first()
    if not class_:
        raise HTTPException(status_code=404, detail="Class not found")

    return db.query(models.Resource).filter(
        models.Resource.class_id == class_id
    ).order_by(models.Resource.created_at.desc()).all()


@router.delete("/{resource_id}", status_code=204)
def delete_resource(
    resource_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_teacher)
):
    """
    Delete a resource. Teacher/Admin only.
    Teachers can only delete their own resources.
    """
    resource = db.query(models.Resource).filter(models.Resource.id == resource_id).first()
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")

    # Teachers can only delete resources they added
    if current_user.role == models.UserRole.teacher and resource.added_by != current_user.id:
        raise HTTPException(status_code=403, detail="You can only delete your own resources")

    db.delete(resource)
    db.commit()
