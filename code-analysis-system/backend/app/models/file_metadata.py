from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Boolean, JSON, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class FileMetadata(Base):
    """Store metadata about individual files in the repository."""

    __tablename__ = "file_metadata"

    id = Column(String, primary_key=True, index=True)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)

    # File information
    file_path = Column(String, nullable=False, index=True)
    file_name = Column(String, nullable=False)
    file_extension = Column(String)
    file_size = Column(Integer)  # in bytes

    # Classification
    file_type = Column(String)  # "source", "config", "test", "documentation"
    language = Column(String)  # "python", "javascript"
    is_entry_point = Column(Boolean, default=False)
    priority_level = Column(Integer, default=0)  # 0-10, higher = more important

    # Content analysis
    lines_of_code = Column(Integer)
    has_classes = Column(Boolean, default=False)
    has_functions = Column(Boolean, default=False)
    complexity_score = Column(Float)  # Cyclomatic complexity

    # Dependencies
    imports = Column(JSON)  # List of imported modules
    exports = Column(JSON)  # List of exported items

    # Processing status
    is_processed = Column(Boolean, default=False)
    should_skip = Column(Boolean, default=False)
    skip_reason = Column(String)  # "binary", "generated", "minified"

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    project = relationship("Project", back_populates="file_metadata")
    code_chunks = relationship("CodeChunk", back_populates="file")
