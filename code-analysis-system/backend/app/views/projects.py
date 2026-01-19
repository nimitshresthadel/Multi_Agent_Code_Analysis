from typing import List
from fastapi import APIRouter, Depends, Query, UploadFile, File, Form, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from app.database import get_db
from app.models.user import User
from app.models.project import Project, ProjectStatus, SourceType, PersonaType
from app.schemas.project import (
    ProjectCreateZip,
    ProjectCreateGithub,
    ProjectResponse,
    ProjectListResponse
)
from app.views.deps import get_current_active_user, require_admin
from app.services.file_handler import FileHandler
from app.services.github_handler import GitHubHandler
from app.utils.exceptions import ResourceNotFoundError, AuthorizationError
import json, logging
from loguru import logger

router = APIRouter(prefix="/projects", tags=["Projects"])

# logging.basicConfig(
#     level=logging.INFO,
#     format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
#     datefmt="%Y-%m-%d %H:%M:%S",
# )

#logger = logging.getLogger(__name__)

@router.post("/upload", response_model=ProjectResponse, status_code=201)
async def create_project_from_zip(
        name: str = Form(...),
        description: str = Form(None),
        personas: str = Form(...),  # JSON string of persona list
        file: UploadFile = File(...),
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db)
):
    """
    Create a new project by uploading a ZIP file.

    - **name**: Project name (required)
    - **description**: Project description (optional)
    - **personas**: JSON array of personas to generate docs for (e.g., ["sde", "pm"])
    - **file**: ZIP file containing the codebase

    The file will be validated for:
    - File size (max 100MB)
    - Valid ZIP format
    - Contains actual code files
    - Not corrupted
    """
    # Parse personas
    try:
        personas_list = json.loads(personas)
        # Validate persona types
        valid_personas = [PersonaType(p) for p in personas_list]
    except (json.JSONDecodeError, ValueError) as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid personas format. Expected JSON array of 'sde' and/or 'pm'. Error: {str(e)}"
        )

    # Create project record first

    new_project = Project(
            name=name,
            description=description,
            owner_id=current_user.id,
            source_type=SourceType.ZIP_UPLOAD,
            personas=[p.value for p in valid_personas],
            status=ProjectStatus.UPLOADING
    )
    db.add(new_project)
    db.commit()
    db.refresh(new_project)

    try:
        # Save and validate file
        file_path, file_size, metadata = await FileHandler.save_upload_file(
            file, new_project.id
        )

        # Step 2: Extract the ZIP file ← THIS WAS MISSING!
        extract_path = FileHandler.extract_zip(file_path, new_project.id)

        print(f"✅ Extracted to: {extract_path}")

        # Check what was extracted
        import os
        extracted_items = os.listdir(extract_path)
        print(f"📁 Extracted items: {extracted_items}")

        # Update project with file information
        new_project.file_path = file_path
        new_project.file_size = file_size
        new_project.repository_metadata_json = metadata
        new_project.status = ProjectStatus.UPLOADED

        db.commit()
        db.refresh(new_project)

        return new_project

    except Exception as e:
        # Clean up project if file upload fails
        db.delete(new_project)
        db.commit()
        raise


@router.post("/github", response_model=ProjectResponse, status_code=201)
def create_project_from_github(
        project_data: ProjectCreateGithub,
        background_tasks: BackgroundTasks,
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db)
):
    """
    Create a new project from a GitHub repository.

    - **name**: Project name
    - **description**: Project description (optional)
    - **source_url**: GitHub repository URL (e.g., https://github.com/owner/repo)
    - **personas**: List of personas ["sde", "pm"]

    The repository will be downloaded and validated.
    """
    # Create project record
    new_project = Project(
        name=project_data.name,
        description=project_data.description,
        owner_id=current_user.id,
        source_type=SourceType.GITHUB_URL,
        source_url=str(project_data.source_url),
        personas=[p.value for p in project_data.personas],
        status=ProjectStatus.UPLOADING
    )

    db.add(new_project)
    db.commit()
    db.refresh(new_project)

    print(f"data", project_data)
    logger.info("data1")

    try:
        # Download and validate repository
        file_path, file_size, metadata = GitHubHandler.download_repository(
            str(project_data.source_url),
            new_project.id
        )

        extract_path = FileHandler.extract_zip(file_path, new_project.id)

        print(f"✅ Extracted to: {extract_path}")

        # Update project
        new_project.file_path = file_path
        new_project.file_size = file_size
        new_project.repository_metadata_json = metadata
        new_project.status = ProjectStatus.UPLOADED

        db.commit()
        db.refresh(new_project)

        return new_project

    except Exception as e:
        # Clean up project if download fails
        db.delete(new_project)
        db.commit()
        raise


@router.get("/", response_model=ProjectListResponse)
def list_my_projects(
        skip: int = Query(0, ge=0),
        limit: int = Query(20, ge=1, le=100),
        status: ProjectStatus = Query(None),
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db)
):
    """
    List current user's projects.

    - **skip**: Number of records to skip (pagination)
    - **limit**: Maximum number of records to return
    - **status**: Filter by project status (optional)

    Returns paginated list of projects owned by the current user.
    """
    query = db.query(Project).filter(Project.owner_id == current_user.id)

    if status:
        query = query.filter(Project.status == status)

    total = query.count()
    projects = query.order_by(Project.created_at.desc()).offset(skip).limit(limit).all()

    return {
        "total": total,
        "projects": projects
    }


@router.get("/all")
def list_all_projects(
        skip: int = Query(0, ge=0),
        limit: int = Query(20, ge=1, le=100),
        status: ProjectStatus = Query(None),
        admin_user: User = Depends(require_admin),
        db: Session = Depends(get_db)
):
    """
    List all projects across all users (Admin only).

    - **skip**: Number of records to skip
    - **limit**: Maximum number of records to return
    - **status**: Filter by project status (optional)
    """
    query = db.query(Project)

    if status:
        query = query.filter(Project.status == status)

    total = query.count()
    projects = query.order_by(Project.created_at.desc()).offset(skip).limit(limit).all()

    return {
        "total": total,
        "projects": projects
    }


@router.get("/{project_id}")
async def get_project(
        project_id: str,
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db)
):
    """
    Get specific project details.

    Users can only access their own projects.
    Admins can access any project.
    """
    project = db.query(Project).filter(Project.id==project_id).first()

    if not project:
        raise ResourceNotFoundError("Project", project_id)

    #Check authorization
    from app.models.user import UserRole
    if project.owner_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise AuthorizationError("You don't have access to this project")

    return project


@router.delete("/{project_id}", status_code=204)
def delete_project(
        project_id: str,
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db)
):
    """
    Delete a project.

    Users can only delete their own projects.
    Admins can delete any project.

    This will also delete all associated files.
    """
    project = db.query(Project).filter(Project.id == project_id).first()

    if not project:
        raise ResourceNotFoundError("Project", project_id)

    # Check authorization
    from app.models.user import UserRole
    if project.owner_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise AuthorizationError("You don't have permission to delete this project")

    # Delete associated files
    try:
        FileHandler.delete_project_files(project.id, project.file_path)
    except Exception as e:
        # Log error but continue with database deletion
        print(f"Warning: Failed to delete project files: {str(e)}")

    # Delete database record
    db.delete(project)
    db.commit()

    return None


@router.get("/{project_id}/status", response_model=dict)
def get_project_status(
        project_id: str,
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db)
):
    """
    Get current status and progress of a project.

    Returns real-time information about project analysis progress.
    """
    project = db.query(Project).filter(Project.id == project_id).first()

    if not project:
        raise ResourceNotFoundError("Project", project_id)

    # Check authorization
    from app.models.user import UserRole
    if project.owner_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise AuthorizationError("You don't have access to this project")

    return {
        "project_id": project.id,
        "status": project.status,
        "progress_percentage": project.progress_percentage,
        "error_message": project.error_message,
        "created_at": project.created_at,
        "updated_at": project.updated_at,
        "completed_at": project.completed_at
    }
