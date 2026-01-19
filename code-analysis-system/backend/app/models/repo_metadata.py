from sqlalchemy import Column, String, JSON, Integer, DateTime, ForeignKey, Text, Boolean, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class RepositoryMetadata(Base):
    """Store intelligent metadata about the repository."""

    __tablename__ = "repository_metadata"

    id = Column(String, primary_key=True, index=True)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)

    # Detection results
    repository_type = Column(String)  # "fastapi", "react", "spring_boot", etc.
    primary_language = Column(String)  # "python", "javascript", "java"
    framework = Column(String)  # "FastAPI", "Express", "Spring Boot"

    # Structure analysis
    entry_points = Column(JSON)  # ["main.py", "app.py"]
    important_files = Column(JSON)  # List of prioritized files
    config_files = Column(JSON)  # ["backend_requirements.txt", "package.json"]

    # Statistics
    total_files = Column(Integer, default=0)
    code_files = Column(Integer, default=0)
    total_lines = Column(Integer, default=0)

    # Dependencies and stack
    dependencies = Column(JSON)  # {"fastapi": "0.104.1", ...}
    tech_stack = Column(JSON)  # ["FastAPI", "PostgreSQL", "Redis"]

    # API/Route detection
    endpoints_count = Column(Integer, default=0)
    endpoints = Column(JSON)  # [{"path": "/api/users", "method": "GET"}]

    # Database detection
    database_type = Column(String)  # "postgresql", "mongodb"
    orm_detected = Column(String)  # "sqlalchemy", "mongoose"

    # Additional insights
    has_tests = Column(Boolean, default=False)
    test_framework = Column(String)  # "pytest", "jest"

    confidence_score = Column(Float)  # 0-1 confidence in detection
    analysis_notes = Column(Text)  # Any notes from analysis

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    project = relationship("Project", back_populates="repository_metadata")
