from pydantic import BaseModel, Field, HttpUrl, AnyHttpUrl
from typing import Optional, List
from datetime import datetime
from app.models.project import ProjectStatus, SourceType, PersonaType


class ProjectBase(BaseModel):
    """Base project schema."""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    personas: List[PersonaType] = Field(..., min_items=1)


class ProjectCreateZip(ProjectBase):
    """Schema for project creation via ZIP upload."""
    source_type: SourceType = SourceType.ZIP_UPLOAD


class ProjectCreateGithub(ProjectBase):
    """Schema for project creation via GitHub URL."""
    source_type: SourceType = SourceType.GITHUB_URL
    source_url: AnyHttpUrl


class ProjectResponse(ProjectBase):
    """Schema for project response."""
    id: str
    owner_id: str
    source_type: SourceType
    source_url: Optional[str] = None
    file_size: Optional[int] = None
    status: ProjectStatus
    progress_percentage: int
    error_message: Optional[str] = None
    repository_metadata: Optional[dict] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ProjectListResponse(BaseModel):
    """Schema for paginated project list."""
    total: int
    projects: List[ProjectResponse]
