from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models.project import Project
from app.models.progress import ProjectProgress, ProgressActivity
from app.views.deps import get_current_active_user

router = APIRouter(prefix="/api/v1/progress", tags=["progress"])


@router.get("/{project_id}")
async def get_project_progress(
        project_id: str,
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db)
):
    """Get current progress for a project."""

    # Verify project ownership
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user.id
    ).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")


    # Get progress
    progress = db.query(ProjectProgress).filter(
        ProjectProgress.project_id == project_id
    ).first()

    if not progress:
        return {
            "success": True,
            "data": {
                "project_id": project_id,
                "status": "not_started",
                "overall_percentage": 0
            }
        }

    # Stage label mapping
    stage_labels = {
        "upload": "Uploading Files",
        "extraction": "Extracting Archive",
        "analysis": "Analyzing Repository Structure",
        "file_processing": "Processing Code Files",
        "code_chunking": "Breaking Down Code",
        "semantic_indexing": "Building Code Understanding",
        "doc_generation": "Generating Documentation",
        "completed": "Complete"
    }

    return {
        "success": True,
        "data": {
            "project_id": progress.project_id,
            "status": progress.status.value,
            "current_stage": progress.current_stage.value,
            "stage_label": stage_labels.get(progress.current_stage.value, progress.current_stage.value),
            "overall_percentage": progress.overall_percentage,
            "stage_percentage": progress.current_stage_percentage,
            "total_files": progress.total_files,
            "processed_files": progress.processed_files,
            "current_file": progress.current_file,
            "total_chunks": progress.total_chunks,
            "processed_chunks": progress.processed_chunks,
            "started_at": progress.started_at.isoformat() if progress.started_at else None,
            "completed_at": progress.completed_at.isoformat() if progress.completed_at else None,
            "error_message": progress.error_message
        }
    }


@router.get("/{project_id}/activities")
async def get_project_activities(
        project_id: str,
        limit: int = 50,
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db)
):
    """Get activity feed for a project."""
    print(f"xyz1")

    # Verify project ownership
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user.id
    ).first()
    print(f"pqr1", project)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get progress record
    progress = db.query(ProjectProgress).filter(
        ProjectProgress.project_id == project_id
    ).first()

    if not progress:
        return {"success": True, "data": {"activities": []}}

    # Get activities
    activities = db.query(ProgressActivity).filter(
        ProgressActivity.progress_id == progress.id
    ).order_by(ProgressActivity.created_at.desc()).limit(limit).all()
    return {
        "success": True,
        "data": {
            "activities": [
                {
                    "id": a.id,
                    "type": a.activity_type.value,
                    "stage": a.stage.value if a.stage else None,
                    "message": a.message,
                    "details": a.details,
                    "file_name": a.file_name,
                    "file_path": a.file_path,
                    "timestamp": a.created_at.isoformat()
                }
                for a in activities
            ]
        }
    }
