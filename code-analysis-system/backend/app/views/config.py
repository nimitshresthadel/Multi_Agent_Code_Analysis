from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models.project import Project
from app.models.analysis_config import AnalysisConfig, AnalysisDepth, VerbosityLevel
from app.views.deps import get_current_active_user
from pydantic import BaseModel
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/config", tags=["configuration"])


class ConfigCreateRequest(BaseModel):
    project_id: str
    depth: str = "standard"
    verbosity: str = "medium"
    enable_web_search: bool = True
    enable_diagrams: bool = True
    enable_security_analysis: bool = True
    enable_performance_analysis: bool = False
    enable_code_quality: bool = True
    personas: List[str] = ["SDE", "PM"]
    max_parallel_agents: int = 3
    max_web_searches: int = 5
    diagram_format: str = "mermaid"
    include_class_diagrams: bool = True
    include_sequence_diagrams: bool = True
    name: Optional[str] = None
    is_template: bool = False


class ConfigUpdateRequest(BaseModel):
    depth: Optional[str] = None
    verbosity: Optional[str] = None
    enable_web_search: Optional[bool] = None
    enable_diagrams: Optional[bool] = None
    enable_security_analysis: Optional[bool] = None
    enable_performance_analysis: Optional[bool] = None
    enable_code_quality: Optional[bool] = None
    personas: Optional[List[str]] = None
    max_parallel_agents: Optional[int] = None
    max_web_searches: Optional[int] = None


@router.post("")
async def create_config(
        request: ConfigCreateRequest,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """Create or update analysis configuration for a project."""

    # Verify project ownership
    project = db.query(Project).filter(
        Project.id == request.project_id,
        Project.owner_id == current_user.id
    ).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check if config already exists
    existing_config = db.query(AnalysisConfig).filter(
        AnalysisConfig.project_id == request.project_id
    ).first()

    if existing_config:
        # Update existing
        for key, value in request.dict(exclude={'project_id'}, exclude_unset=True).items():
            setattr(existing_config, key, value)
        config = existing_config
    else:
        # Create new
        config = AnalysisConfig(
            project_id=request.project_id,
            depth=AnalysisDepth(request.depth),
            verbosity=VerbosityLevel(request.verbosity),
            enable_web_search=request.enable_web_search,
            enable_diagrams=request.enable_diagrams,
            enable_security_analysis=request.enable_security_analysis,
            enable_performance_analysis=request.enable_performance_analysis,
            enable_code_quality=request.enable_code_quality,
            personas=request.personas,
            max_parallel_agents=request.max_parallel_agents,
            max_web_searches=request.max_web_searches,
            diagram_format=request.diagram_format,
            include_class_diagrams=request.include_class_diagrams,
            include_sequence_diagrams=request.include_sequence_diagrams,
            name=request.name,
            is_template=request.is_template
        )
        db.add(config)

    db.commit()
    db.refresh(config)

    logger.info(f"Configuration saved for project {request.project_id}")

    return {
        "success": True,
        "message": "Configuration saved successfully",
        "data": {
            "id": config.id,
            "project_id": config.project_id,
            "depth": config.depth.value,
            "verbosity": config.verbosity.value,
            "enable_web_search": config.enable_web_search,
            "enable_diagrams": config.enable_diagrams,
            "personas": config.personas,
            "created_at": config.created_at.isoformat()
        }
    }


@router.get("/{project_id}")
async def get_config(
        project_id: str,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """Get configuration for a project."""

    # Verify project ownership
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user.id
    ).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    config = db.query(AnalysisConfig).filter(
        AnalysisConfig.project_id == project_id
    ).first()

    if not config:
        # Return default config
        return {
            "success": True,
            "data": {
                "project_id": project_id,
                "depth": "standard",
                "verbosity": "medium",
                "enable_web_search": True,
                "enable_diagrams": True,
                "enable_security_analysis": True,
                "enable_performance_analysis": False,
                "enable_code_quality": True,
                "personas": ["SDE", "PM"],
                "max_parallel_agents": 3,
                "max_web_searches": 5,
                "is_default": True
            }
        }

    return {
        "success": True,
        "data": {
            "id": config.id,
            "project_id": config.project_id,
            "depth": config.depth.value,
            "verbosity": config.verbosity.value,
            "enable_web_search": config.enable_web_search,
            "enable_diagrams": config.enable_diagrams,
            "enable_security_analysis": config.enable_security_analysis,
            "enable_performance_analysis": config.enable_performance_analysis,
            "enable_code_quality": config.enable_code_quality,
            "personas": config.personas,
            "max_parallel_agents": config.max_parallel_agents,
            "max_web_searches": config.max_web_searches,
            "diagram_format": config.diagram_format,
            "include_class_diagrams": config.include_class_diagrams,
            "include_sequence_diagrams": config.include_sequence_diagrams,
            "name": config.name,
            "is_template": config.is_template,
            "is_default": False
        }
    }


@router.get("/templates/list")
async def list_templates(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """List saved configuration templates."""

    templates = db.query(AnalysisConfig).filter(
        AnalysisConfig.is_template == True
    ).all()

    # Add default templates
    default_templates = [
        {
            "id": "quick-scan",
            "name": "Quick Scan",
            "depth": "quick",
            "verbosity": "low",
            "enable_web_search": False,
            "personas": ["SDE"],
            "is_default": True
        },
        {
            "id": "comprehensive",
            "name": "Comprehensive Analysis",
            "depth": "deep",
            "verbosity": "high",
            "enable_web_search": True,
            "enable_diagrams": True,
            "personas": ["SDE", "PM"],
            "is_default": True
        },
        {
            "id": "security-focused",
            "name": "Security Audit",
            "depth": "deep",
            "verbosity": "high",
            "enable_security_analysis": True,
            "enable_web_search": True,
            "personas": ["SDE"],
            "is_default": True
        }
    ]

    return {
        "success": True,
        "data": {
            "templates": [
                             {
                                 "id": t.id,
                                 "name": t.name,
                                 "depth": t.depth.value,
                                 "verbosity": t.verbosity.value,
                                 "personas": t.personas,
                                 "is_default": False
                             }
                             for t in templates
                         ] + default_templates
        }
    }
