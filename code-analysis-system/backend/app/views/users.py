from typing import List
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models.user import User
from app.models.project import Project
from app.schemas.user import UserResponse, UserWithProjects, UserUpdate
from app.views.deps import get_current_active_user, require_admin
from app.utils.exceptions import ResourceNotFoundError, DuplicateResourceError
from app.core.security import get_password_hash

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserWithProjects)
def get_my_profile(
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db)
):
    """
    Get current user's profile with project count.

    Returns user information including total number of projects.
    """
    project_count = db.query(func.count(Project.id)).filter(
        Project.owner_id == current_user.id
    ).scalar()

    user_dict = {
        "id": current_user.id,
        "email": current_user.email,
        "username": current_user.username,
        "full_name": current_user.full_name,
        "role": current_user.role,
        "is_active": current_user.is_active,
        "created_at": current_user.created_at,
        "project_count": project_count
    }

    return user_dict


@router.put("/me", response_model=UserResponse)
def update_my_profile(
        user_update: UserUpdate,
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db)
):
    """
    Update current user's profile.

    - **email**: New email address (optional)
    - **username**: New username (optional)
    - **full_name**: New full name (optional)
    - **password**: New password (optional)
    """
    # Check for duplicate email
    if user_update.email and user_update.email != current_user.email:
        existing_email = db.query(User).filter(
            User.email == user_update.email,
            User.id != current_user.id
        ).first()
        if existing_email:
            raise DuplicateResourceError("User", "email", user_update.email)
        current_user.email = user_update.email

    # Check for duplicate username
    if user_update.username and user_update.username != current_user.username:
        existing_username = db.query(User).filter(
            User.username == user_update.username,
            User.id != current_user.id
        ).first()
        if existing_username:
            raise DuplicateResourceError("User", "username", user_update.username)
        current_user.username = user_update.username

    # Update other fields
    if user_update.full_name is not None:
        current_user.full_name = user_update.full_name

    if user_update.password:
        current_user.hashed_password = get_password_hash(user_update.password)

    db.commit()
    db.refresh(current_user)

    return current_user


@router.get("/", response_model=List[UserWithProjects])
def list_users(
        skip: int = Query(0, ge=0),
        limit: int = Query(100, ge=1, le=100),
        admin_user: User = Depends(require_admin),
        db: Session = Depends(get_db)
):
    """
    List all users (Admin only).

    - **skip**: Number of records to skip (pagination)
    - **limit**: Maximum number of records to return

    Returns list of all users with their project counts.
    """
    users = db.query(User).offset(skip).limit(limit).all()

    result = []
    for user in users:
        project_count = db.query(func.count(Project.id)).filter(
            Project.owner_id == user.id
        ).scalar()

        user_dict = {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "full_name": user.full_name,
            "role": user.role,
            "is_active": user.is_active,
            "created_at": user.created_at,
            "project_count": project_count
        }
        result.append(user_dict)

    return result


@router.get("/{user_id}", response_model=UserWithProjects)
def get_user(
        user_id: str,
        admin_user: User = Depends(require_admin),
        db: Session = Depends(get_db)
):
    """
    Get specific user by ID (Admin only).

    Returns user information with project count.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise ResourceNotFoundError("User", user_id)

    project_count = db.query(func.count(Project.id)).filter(
        Project.owner_id == user.id
    ).scalar()

    user_dict = {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "full_name": user.full_name,
        "role": user.role,
        "is_active": user.is_active,
        "created_at": user.created_at,
        "project_count": project_count
    }

    return user_dict


@router.delete("/{user_id}", status_code=204)
def delete_user(
        user_id: str,
        admin_user: User = Depends(require_admin),
        db: Session = Depends(get_db)
):
    """
    Delete a user (Admin only).

    This will also delete all projects owned by the user.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise ResourceNotFoundError("User", user_id)

    # Prevent deleting yourself
    if user.id == admin_user.id:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete your own account"
        )

    db.delete(user)
    db.commit()

    return None
