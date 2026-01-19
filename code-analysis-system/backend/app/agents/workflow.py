from langgraph.graph import StateGraph, END
from typing import Dict, TypedDict, Annotated
import logging
from datetime import datetime
from app.agents.specialized_agents import (
    FileAnalyzerAgent,
    WebSearcherAgent,
    CodeExtractorAgent,
    SecurityAuditorAgent,
    DocumentationGeneratorAgent,
    PMSummarizerAgent
)

logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    """State shared across all agents."""
    project_id: str
    config: Dict
    files: list
    code_chunks: list

    # Agent outputs
    file_structure: Dict
    api_signatures: list
    web_search_results: Dict
    security_findings: Dict
    sde_documentation: str
    pm_summary: str

    # Execution tracking
    completed_agents: Annotated[list, "append"]
    current_agent: str
    total_tokens: int
    total_searches: int
    errors: list


class AgentOrchestrator:
    """LangGraph-based multi-agent orchestrator."""

    def __init__(self):
        self.workflow = self._build_workflow()
        self.agents = {
            "file_analyzer": FileAnalyzerAgent(),
            "web_searcher": WebSearcherAgent(),
            "code_extractor": CodeExtractorAgent(),
            "security_auditor": SecurityAuditorAgent(),
            "doc_generator": DocumentationGeneratorAgent(),
            "pm_summarizer": PMSummarizerAgent()
        }

    def _build_workflow(self) -> StateGraph:
        """Build the agent workflow graph."""

        workflow = StateGraph(AgentState)

        # Add nodes (agents)
        workflow.add_node("file_analyzer", self._run_file_analyzer)
        workflow.add_node("code_extractor", self._run_code_extractor)
        workflow.add_node("web_searcher", self._run_web_searcher)
        workflow.add_node("security_auditor", self._run_security_auditor)
        workflow.add_node("doc_generator", self._run_doc_generator)
        workflow.add_node("pm_summarizer", self._run_pm_summarizer)

        # Define the flow
        workflow.set_entry_point("file_analyzer")

        # Sequential flow
        workflow.add_edge("file_analyzer", "code_extractor")
        workflow.add_edge("code_extractor", "web_searcher")
        workflow.add_edge("web_searcher", "security_auditor")
        workflow.add_edge("security_auditor", "doc_generator")
        workflow.add_edge("doc_generator", "pm_summarizer")
        workflow.add_edge("pm_summarizer", END)

        return workflow.compile()

    async def _run_file_analyzer(self, state: AgentState) -> AgentState:
        """Execute file analyzer agent."""

        logger.info("=" * 60)
        logger.info("🤖 Agent 1: File Analyzer")
        logger.info("=" * 60)

        state["current_agent"] = "file_analyzer"

        try:
            agent = self.agents["file_analyzer"]
            result = await agent.execute(state)

            state["file_structure"] = result["file_structure"]
            state["total_tokens"] = state.get("total_tokens", 0) + result.get("tokens_used", 0)
            state["completed_agents"].append("file_analyzer")

            logger.info("✅ File Analyzer: Complete")

        except Exception as e:
            logger.error(f"❌ File Analyzer failed: {str(e)}")
            state["errors"].append(f"File Analyzer: {str(e)}")

        return state

    async def _run_code_extractor(self, state: AgentState) -> AgentState:
        """Execute code extractor agent."""

        logger.info("=" * 60)
        logger.info("🤖 Agent 2: Code Extractor")
        logger.info("=" * 60)

        state["current_agent"] = "code_extractor"

        try:
            agent = self.agents["code_extractor"]
            result = await agent.execute(state)

            state["api_signatures"] = result["api_signatures"]
            state["completed_agents"].append("code_extractor")

            logger.info("✅ Code Extractor: Complete")

        except Exception as e:
            logger.error(f"❌ Code Extractor failed: {str(e)}")
            state["errors"].append(f"Code Extractor: {str(e)}")

        return state

    async def _run_web_searcher(self, state: AgentState) -> AgentState:
        """Execute web searcher agent."""

        logger.info("=" * 60)
        logger.info("🤖 Agent 3: Web Searcher")
        logger.info("=" * 60)

        state["current_agent"] = "web_searcher"

        try:
            agent = self.agents["web_searcher"]
            result = await agent.execute(state)

            state["web_search_results"] = result["web_search_results"]
            state["total_searches"] = result["searches_performed"]
            state["completed_agents"].append("web_searcher")

            logger.info("✅ Web Searcher: Complete")

        except Exception as e:
            logger.error(f"❌ Web Searcher failed: {str(e)}")
            state["errors"].append(f"Web Searcher: {str(e)}")

        return state

    async def _run_security_auditor(self, state: AgentState) -> AgentState:
        """Execute security auditor agent."""

        logger.info("=" * 60)
        logger.info("🤖 Agent 4: Security Auditor")
        logger.info("=" * 60)

        state["current_agent"] = "security_auditor"

        try:
            agent = self.agents["security_auditor"]
            result = await agent.execute(state)

            state["security_findings"] = result.get("security_findings", {})
            state["total_tokens"] = state.get("total_tokens", 0) + result.get("tokens_used", 0)
            state["completed_agents"].append("security_auditor")

            logger.info("✅ Security Auditor: Complete")

        except Exception as e:
            logger.error(f"❌ Security Auditor failed: {str(e)}")
            state["errors"].append(f"Security Auditor: {str(e)}")

        return state

    async def _run_doc_generator(self, state: AgentState) -> AgentState:
        """Execute documentation generator agent."""

        logger.info("=" * 60)
        logger.info("🤖 Agent 5: Documentation Generator")
        logger.info("=" * 60)

        state["current_agent"] = "doc_generator"

        try:
            agent = self.agents["doc_generator"]
            result = await agent.execute(state)

            state["sde_documentation"] = result["sde_documentation"]
            state["total_tokens"] = state.get("total_tokens", 0) + result.get("tokens_used", 0)
            state["completed_agents"].append("doc_generator")

            logger.info("✅ Documentation Generator: Complete")

        except Exception as e:
            logger.error(f"❌ Documentation Generator failed: {str(e)}")
            state["errors"].append(f"Documentation Generator: {str(e)}")

        return state

    async def _run_pm_summarizer(self, state: AgentState) -> AgentState:
        """Execute PM summarizer agent."""

        logger.info("=" * 60)
        logger.info("🤖 Agent 6: PM Summarizer")
        logger.info("=" * 60)

        state["current_agent"] = "pm_summarizer"

        try:
            agent = self.agents["pm_summarizer"]
            result = await agent.execute(state)

            state["pm_summary"] = result.get("pm_summary")
            state["total_tokens"] = state.get("total_tokens", 0) + result.get("tokens_used", 0)
            state["completed_agents"].append("pm_summarizer")

            logger.info("✅ PM Summarizer: Complete")

        except Exception as e:
            logger.error(f"❌ PM Summarizer failed: {str(e)}")
            state["errors"].append(f"PM Summarizer: {str(e)}")

        return state

    async def execute(self, initial_state: Dict) -> Dict:
        """Execute the complete workflow."""

        logger.info("🚀 Starting multi-agent orchestration")
        logger.info(f"📋 Configuration: {initial_state['config']}")

        start_time = datetime.now()

        # Initialize state
        state = AgentState(
            project_id=initial_state["project_id"],
            config=initial_state["config"],
            files=initial_state.get("files", []),
            code_chunks=initial_state.get("code_chunks", []),
            completed_agents=[],
            current_agent="",
            total_tokens=0,
            total_searches=0,
            errors=[],
            file_structure={},
            api_signatures=[],
            web_search_results={},
            security_findings={},
            sde_documentation="",
            pm_summary=""
        )

        try:
            # Execute workflow
            final_state = await self.workflow.ainvoke(state)

            duration = (datetime.now() - start_time).total_seconds()

            logger.info("=" * 60)
            logger.info("✅ Multi-agent orchestration complete!")
            logger.info(f"⏱️  Duration: {duration:.2f}s")
            logger.info(f"🎯 Agents completed: {len(final_state['completed_agents'])}/6")
            logger.info(f"🔢 Total tokens: {final_state.get('total_tokens', 0)}")
            logger.info(f"🔍 Web searches: {final_state.get('total_searches', 0)}")
            logger.info("=" * 60)

            return {
                "success": True,
                "state": final_state,
                "duration": duration,
                "agents_completed": final_state["completed_agents"],
                "errors": final_state["errors"]
            }

        except Exception as e:
            logger.error(f"❌ Workflow execution failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "state": state
            }
