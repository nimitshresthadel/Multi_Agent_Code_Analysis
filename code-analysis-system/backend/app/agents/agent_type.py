from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel


class AgentType(str, Enum):
    """Types of specialized agents."""
    COORDINATOR = "coordinator"
    FILE_ANALYZER = "file_analyzer"
    CODE_EXTRACTOR = "code_extractor"
    WEB_SEARCHER = "web_searcher"
    SECURITY_AUDITOR = "security_auditor"
    PERFORMANCE_ANALYZER = "performance_analyzer"
    DOCUMENTATION_GENERATOR = "documentation_generator"
    DIAGRAM_GENERATOR = "diagram_generator"
    PM_SUMMARIZER = "pm_summarizer"


class AgentState(BaseModel):
    """Shared state between agents."""
    project_id: str
    config: Dict

    # Analysis data
    file_structure: Optional[Dict] = None
    code_chunks: Optional[List[Dict]] = None
    api_signatures: Optional[List[Dict]] = None

    # Web search results
    web_search_results: Optional[Dict] = None
    framework_best_practices: Optional[Dict] = None
    security_guidelines: Optional[Dict] = None

    # Generated outputs
    sde_documentation: Optional[str] = None
    pm_summary: Optional[str] = None
    diagrams: Optional[List[Dict]] = None

    # Agent execution tracking
    completed_agents: List[str] = []
    current_agent: Optional[str] = None
    errors: List[str] = []

    class Config:
        arbitrary_types_allowed = True


class AgentResult(BaseModel):
    """Result from an agent execution."""
    agent_name: str
    status: str  # success, failed, skipped
    output: Optional[Dict] = None
    error: Optional[str] = None
    tokens_used: int = 0
    duration_seconds: float = 0
    web_searches: int = 0
