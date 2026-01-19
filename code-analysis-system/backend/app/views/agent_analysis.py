from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models.project import Project
from app.models.analysis_config import AgentExecution
from app.views.deps import get_current_active_user
from app.services.analysis_orchestrator import AnalysisOrchestrationService
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/agent_analysis", tags=["analysis"])


class StartAnalysisRequest(BaseModel):
    project_id: str


@router.post("/start")
async def start_agent_analysis(
        request: StartAnalysisRequest,
        background_tasks: BackgroundTasks,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """Start multi-agent analysis."""

    logger.info(f"Starting analysis for project {request.project_id}")

    # Verify ownership
    project = db.query(Project).filter(
        Project.id == request.project_id,
        Project.owner_id == current_user.id
    ).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Start analysis in background
    orchestrator = AnalysisOrchestrationService()
    background_tasks.add_task(
        orchestrator.start_analysis,
        request.project_id,
        db
    )

    return {
        "success": True,
        "message": "Analysis started",
        "data": {
            "project_id": request.project_id
        }
    }


@router.get("/{project_id}/agents")
async def get_agent_status(
        project_id: str,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """Get status of all agents for a project."""

    # Verify ownership
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user.id
    ).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get agent executions
    agents = db.query(AgentExecution).filter(
        AgentExecution.project_id == project_id
    ).order_by(AgentExecution.created_at).all()

    return {
        "success": True,
        "data": {
            "agents": [
                {
                    "id": a.id,
                    "name": a.agent_name,
                    "type": a.agent_type,
                    "status": a.status,
                    "started_at": a.started_at.isoformat() if a.started_at else None,
                    "completed_at": a.completed_at.isoformat() if a.completed_at else None,
                    "tokens_used": a.tokens_used,
                    "web_searches": a.web_searches_performed,
                    "error": a.error_message
                }
                for a in agents
            ]
        }
    }
