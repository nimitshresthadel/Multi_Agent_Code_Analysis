from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, JSON, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class CodeChunk(Base):
    """Store individual code chunks with metadata for semantic search."""

    __tablename__ = "code_chunks"

    id = Column(String, primary_key=True, index=True)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    file_id = Column(String, ForeignKey("file_metadata.id"), nullable=False)

    # Location
    file_path = Column(String, nullable=False, index=True)
    start_line = Column(Integer, nullable=False)
    end_line = Column(Integer, nullable=False)

    # Code information
    chunk_type = Column(String)  # "function", "class", "method", "block"
    name = Column(String, index=True)  # Function/class name
    signature = Column(Text)  # Full signature
    code = Column(Text, nullable=False)  # Actual code

    # Context
    parent_class = Column(String)  # If method, which class
    module_path = Column(String)  # Full module path

    # Semantic information
    purpose = Column(Text)  # What this code does
    parameters = Column(JSON)  # List of parameters
    return_type = Column(String)
    docstring = Column(Text)

    # Dependencies
    calls_functions = Column(JSON)  # Functions called within
    uses_variables = Column(JSON)  # Variables used
    imports_used = Column(JSON)  # Imports needed

    # Metrics
    complexity = Column(Integer)  # Cyclomatic complexity
    token_count = Column(Integer)  # For LLM context management

    # Search optimization
    keywords = Column(JSON)  # Extracted keywords
    semantic_summary = Column(Text)  # AI-generated summary

    # Vector embedding (stored separately in vector DB)
    embedding_id = Column(String, index=True)  # Reference to vector store

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    project = relationship("Project", back_populates="code_chunks")
    file = relationship("FileMetadata", back_populates="code_chunks")
