from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy import func
from sqlalchemy.orm import Session
from typing import List, Optional, Dict
from pydantic import BaseModel
import logging
from app.database import get_db, SessionLocal
from app.views.deps import get_current_active_user
from app.models.user import User
from app.models.project import Project
from app.models.repo_metadata import RepositoryMetadata
from app.models.file_metadata import FileMetadata
from app.models.code_chunk import CodeChunk
from app.services.preprocessing_sys import PreprocessingOrchestrator

router = APIRouter(prefix="/api/v1/analysis", tags=["analysis"])

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)

# Request/Response Models
class AnalysisRequest(BaseModel):
    project_id: str


class AnalysisStatusResponse(BaseModel):
    project_id: str
    status: str
    progress: Optional[Dict] = None
    error: Optional[str] = None


class RepositoryInsightsResponse(BaseModel):
    project_id: str
    repository_type: str
    primary_language: str
    framework: str
    confidence_score: float
    entry_points: List[str]
    important_files: List[Dict]
    config_files: List[str]
    total_files: int
    code_files: int
    total_lines: int
    dependencies: Dict
    tech_stack: List[str]
    endpoints_count: int
    endpoints: List[Dict]
    database_type: Optional[str]
    orm_detected: Optional[str]
    has_tests: bool
    test_framework: Optional[str]
    analysis_notes: str


class FileMetadataResponse(BaseModel):
    id: str
    file_path: str
    file_name: str
    file_type: str
    language: Optional[str]
    priority_level: int
    lines_of_code: int
    has_classes: bool
    has_functions: bool
    complexity_score: float
    imports: List[str]


class CodeChunkResponse(BaseModel):
    id: str
    file_path: str
    chunk_type: str
    name: str
    signature: str
    start_line: int
    end_line: int
    code: str
    docstring: Optional[str]
    complexity: int
    keywords: List[str]


class ProjectStatisticsResponse(BaseModel):
    total_files: int
    code_files: int
    total_chunks: int
    chunk_breakdown: Dict[str, int]
    languages: Dict[str, int]
    avg_complexity: float
    top_complex_files: List[Dict]


# Background task for preprocessing
def run_preprocessing_task(project_id: str, project_path: str, db: Session):
    """Background task to run preprocessing pipeline."""
    db = SessionLocal()
    try:
        orchestrator = PreprocessingOrchestrator(project_id, project_path, db)
        results = orchestrator.run_full_pipeline()

        # Update project status
        project = db.query(Project).filter(Project.id == project_id).first()
        if project:
            project.status = "completed"
            db.commit()

        return results
    except Exception as e:
        # Update project status to failed
        project = db.query(Project).filter(Project.id == project_id).first()
        if project:
            project.status = "failed"
            db.commit()
        raise


@router.post("/start", response_model=AnalysisStatusResponse)
async def start_analysis(
        request: AnalysisRequest,
        background_tasks: BackgroundTasks,
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db)
):
    """Start preprocessing and analysis for a project."""

    # Get project
    project = db.query(Project).filter(
        Project.id == request.project_id,
        Project.owner_id == current_user.id
    ).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.status == "processing":
        raise HTTPException(
            status_code=400,
            detail="Project is already being processed"
        )

    # Update status
    project.status = "processing"
    db.commit()

    # Start background processing
    project_path = f"backend/app/storage/projects/{project.id}"
    background_tasks.add_task(run_preprocessing_task, project.id, project_path, db)

    return AnalysisStatusResponse(
        project_id=project.id,
        status="processing",
        progress={"step": "starting", "message": "Analysis started"}
    )


@router.get("/status/{project_id}", response_model=AnalysisStatusResponse)
async def get_analysis_status(
        project_id: str,
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db)
):
    """Get current analysis status for a project."""

    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user.id
    ).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    return AnalysisStatusResponse(
        project_id=project.id,
        status=project.status
    )


@router.get("/insights/{project_id}", response_model=RepositoryInsightsResponse)
async def get_repository_insights(
        project_id: str,
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db)
):
    """Get repository intelligence insights for a project."""
    # Verify project ownership
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get repository metadata
    repo_metadata = db.query(RepositoryMetadata).filter(
        RepositoryMetadata.project_id == project_id
    ).first()

    if not repo_metadata:
        raise HTTPException(
            status_code=404,
            detail="Repository analysis not completed yet"
        )

    return RepositoryInsightsResponse(
        project_id=project_id,
        repository_type=repo_metadata.repository_type,
        primary_language=repo_metadata.primary_language,
        framework=repo_metadata.framework,
        confidence_score=repo_metadata.confidence_score,
        entry_points=repo_metadata.entry_points or [],
        important_files=repo_metadata.important_files or [],
        config_files=repo_metadata.config_files or [],
        total_files=repo_metadata.total_files,
        code_files=repo_metadata.code_files,
        total_lines=repo_metadata.total_lines,
        dependencies=repo_metadata.dependencies or {},
        tech_stack=repo_metadata.tech_stack or [],
        endpoints_count=repo_metadata.endpoints_count,
        endpoints=repo_metadata.endpoints or [],
        database_type=repo_metadata.database_type,
        orm_detected=repo_metadata.orm_detected,
        has_tests=repo_metadata.has_tests,
        test_framework=repo_metadata.test_framework,
        analysis_notes=repo_metadata.analysis_notes
    )

@router.get("/files/{project_id}", response_model=List[FileMetadataResponse])
async def get_project_files(
        project_id: str,
        skip: int = 0,
        limit: int = 100,
        file_type: Optional[str] = None,
        language: Optional[str] = None,
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db)
):
    """Get file metadata for a project with filtering."""

    # Verify project ownership
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user.id
    ).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Build query
    query = db.query(FileMetadata).filter(
        FileMetadata.project_id == project_id,
        FileMetadata.should_skip == False
    )

    if file_type:
        query = query.filter(FileMetadata.file_type == file_type)

    if language:
        query = query.filter(FileMetadata.language == language)

    # Get files ordered by priority
    files = query.order_by(
        FileMetadata.priority_level.desc()
    ).offset(skip).limit(limit).all()

    return [
        FileMetadataResponse(
            id=f.id,
            file_path=f.file_path,
            file_name=f.file_name,
            file_type=f.file_type,
            language=f.language,
            priority_level=f.priority_level,
            lines_of_code=f.lines_of_code,
            has_classes=f.has_classes,
            has_functions=f.has_functions,
            complexity_score=f.complexity_score,
            imports=f.imports or []
        )
        for f in files
    ]


@router.get("/chunks/{project_id}", response_model=List[CodeChunkResponse])
async def get_code_chunks(
        project_id: str,
        skip: int = 0,
        limit: int = 50,
        chunk_type: Optional[str] = None,
        file_path: Optional[str] = None,
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db)
):
    """Get code chunks for a project with filtering."""

    # Verify project ownership
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user.id
    ).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Build query
    query = db.query(CodeChunk).filter(CodeChunk.project_id == project_id)

    if chunk_type:
        query = query.filter(CodeChunk.chunk_type == chunk_type)

    if file_path:
        query = query.filter(CodeChunk.file_path.contains(file_path))

    chunks = query.offset(skip).limit(limit).all()

    return [
        CodeChunkResponse(
            id=c.id,
            file_path=c.file_path,
            chunk_type=c.chunk_type,
            name=c.name,
            signature=c.signature,
            start_line=c.start_line,
            end_line=c.end_line,
            code=c.code,
            docstring=c.docstring,
            complexity=c.complexity,
            keywords=c.keywords or []
        )
        for c in chunks
    ]


@router.get("/statistics/{project_id}", response_model=ProjectStatisticsResponse)
async def get_project_statistics(
        project_id: str,
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db)
):
    """Get comprehensive statistics for a project."""

    # Verify project ownership
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user.id
    ).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get file statistics
    total_files = db.query(FileMetadata).filter(
        FileMetadata.project_id == project_id
    ).count()

    code_files = db.query(FileMetadata).filter(
        FileMetadata.project_id == project_id,
        FileMetadata.file_type == "source"
    ).count()

    # Get chunk statistics
    total_chunks = db.query(CodeChunk).filter(
        CodeChunk.project_id == project_id
    ).count()

    # Chunk breakdown by type
    chunk_types = db.query(
        CodeChunk.chunk_type,
        func.count(CodeChunk.id)
    ).filter(
        CodeChunk.project_id == project_id
    ).group_by(CodeChunk.chunk_type).all()

    chunk_breakdown = {chunk_type: count for chunk_type, count in chunk_types}

    # Language distribution
    languages = db.query(
        FileMetadata.language,
        func.count(FileMetadata.id)
    ).filter(
        FileMetadata.project_id == project_id,
        FileMetadata.language.isnot(None)
    ).group_by(FileMetadata.language).all()

    language_dist = {lang: count for lang, count in languages}

    # Average complexity
    avg_complexity_result = db.query(
        func.avg(CodeChunk.complexity)
    ).filter(
        CodeChunk.project_id == project_id
    ).scalar()

    avg_complexity = float(avg_complexity_result or 0)

    # Top complex files
    complex_files = db.query(
        FileMetadata.file_path,
        FileMetadata.complexity_score
    ).filter(
        FileMetadata.project_id == project_id
    ).order_by(
        FileMetadata.complexity_score.desc()
    ).limit(5).all()

    top_complex = [
        {"file": file, "complexity": complexity}
        for file, complexity in complex_files
    ]

    return ProjectStatisticsResponse(
        total_files=total_files,
        code_files=code_files,
        total_chunks=total_chunks,
        chunk_breakdown=chunk_breakdown,
        languages=language_dist,
        avg_complexity=avg_complexity,
        top_complex_files=top_complex
    )
