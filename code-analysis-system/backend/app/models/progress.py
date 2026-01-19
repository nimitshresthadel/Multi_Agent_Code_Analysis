from sqlalchemy import Column, String, Integer, Float, DateTime, Text, Enum, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum
from app.database import Base


class ProgressStatus(enum.Enum):
    """Progress status types."""
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ProgressStage(enum.Enum):
    """Processing stages."""
    UPLOAD = "upload"
    EXTRACTION = "extraction"
    ANALYSIS = "analysis"
    FILE_PROCESSING = "file_processing"
    CODE_CHUNKING = "code_chunking"
    SEMANTIC_INDEXING = "semantic_indexing"
    DOC_GENERATION = "doc_generation"
    COMPLETED = "completed"


class ActivityType(enum.Enum):
    """Activity feed message types."""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    MILESTONE = "milestone"


class ProjectProgress(Base):
    """Track overall project processing progress."""
    __tablename__ = "project_progress"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)

    # Status
    status = Column(Enum(ProgressStatus), default=ProgressStatus.QUEUED)
    current_stage = Column(Enum(ProgressStage), default=ProgressStage.UPLOAD)

    # Progress metrics
    overall_percentage = Column(Float, default=0.0)
    current_stage_percentage = Column(Float, default=0.0)

    # File processing
    total_files = Column(Integer, default=0)
    processed_files = Column(Integer, default=0)
    current_file = Column(String)

    # Chunks
    total_chunks = Column(Integer, default=0)
    processed_chunks = Column(Integer, default=0)

    # Timing
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    estimated_completion = Column(DateTime)

    # Error handling
    error_message = Column(Text)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    project = relationship("Project", back_populates="progress")
    activities = relationship("ProgressActivity", back_populates="progress", cascade="all, delete-orphan")


class ProgressActivity(Base):
    """Activity feed entries for progress tracking."""
    __tablename__ = "progress_activities"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    progress_id = Column(String, ForeignKey("project_progress.id"), nullable=False)

    # Activity details
    activity_type = Column(Enum(ActivityType), nullable=False)
    stage = Column(Enum(ProgressStage))
    message = Column(Text, nullable=False)
    details = Column(Text)

    # File context
    file_name = Column(String)
    file_path = Column(String)

    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    progress = relationship("ProjectProgress", back_populates="activities")
