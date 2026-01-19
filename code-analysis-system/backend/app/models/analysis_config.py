from sqlalchemy import Column, String, Integer, Boolean, JSON, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime
import uuid
import enum


class AnalysisDepth(str, enum.Enum):
    QUICK = "quick"
    STANDARD = "standard"
    DEEP = "deep"


class VerbosityLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class AnalysisConfig(Base):
    """Configuration for analysis behavior."""

    __tablename__ = "analysis_configs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)

    # Analysis Settings
    depth = Column(SQLEnum(AnalysisDepth), default=AnalysisDepth.STANDARD)
    verbosity = Column(SQLEnum(VerbosityLevel), default=VerbosityLevel.MEDIUM)

    # Feature Flags
    enable_web_search = Column(Boolean, default=True)
    enable_diagrams = Column(Boolean, default=True)
    enable_security_analysis = Column(Boolean, default=True)
    enable_performance_analysis = Column(Boolean, default=False)
    enable_code_quality = Column(Boolean, default=True)

    # Persona Settings
    personas = Column(JSON, default=list)  # ["SDE", "PM", "QA"]

    # Agent Configuration
    max_parallel_agents = Column(Integer, default=3)
    agent_timeout = Column(Integer, default=300)  # seconds

    # Web Search Settings
    max_web_searches = Column(Integer, default=5)
    search_depth = Column(Integer, default=3)  # results per search

    # Diagram Settings
    diagram_format = Column(String, default="mermaid")  # mermaid, plantuml
    include_class_diagrams = Column(Boolean, default=True)
    include_sequence_diagrams = Column(Boolean, default=True)
    include_er_diagrams = Column(Boolean, default=False)

    # Metadata
    name = Column(String)  # Template name if saved
    is_template = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    project = relationship("Project", back_populates="config")


class AgentExecution(Base):
    """Track individual agent executions."""

    __tablename__ = "agent_executions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)

    agent_name = Column(String, nullable=False)
    agent_type = Column(String, nullable=False)  # "analyzer", "searcher", "generator"

    status = Column(String, default="pending")  # pending, running, completed, failed
    started_at = Column(DateTime)
    completed_at = Column(DateTime)

    input_data = Column(JSON)
    output_data = Column(JSON)
    error_message = Column(String)

    # Web search tracking
    web_searches_performed = Column(Integer, default=0)
    search_queries = Column(JSON)  # List of search queries made

    # Token usage
    tokens_used = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
