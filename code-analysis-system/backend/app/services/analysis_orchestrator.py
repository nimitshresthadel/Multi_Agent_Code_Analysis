import logging
import asyncio
from sqlalchemy.orm import Session
from datetime import datetime
from app.models.project import Project
from app.models.analysis_config import AnalysisConfig, AgentExecution
from app.models.progress import ProjectProgress, ProgressStage, ProgressStatus, ProgressActivity, ActivityType
from app.models.code_chunk import CodeChunk
from app.models.file_metadata import FileMetadata
from app.agents.workflow import AgentOrchestrator

logger = logging.getLogger(__name__)


class AnalysisOrchestrationService:
    """Service to orchestrate multi-agent analysis."""

    def __init__(self):
        self.orchestrator = AgentOrchestrator()

    async def start_analysis(self, project_id: str, db: Session):
        """Start multi-agent analysis for a project."""

        logger.info(f"🚀 Starting orchestrated analysis for project {project_id}")

        try:
            # Get project
            project = db.query(Project).filter(Project.id == project_id).first()
            if not project:
                raise ValueError("Project not found")

            # Get or create configuration
            config = db.query(AnalysisConfig).filter(
                AnalysisConfig.project_id == project_id
            ).first()

            if not config:
                logger.info("No config found, using defaults")
                config_dict = {
                    "depth": "standard",
                    "verbosity": "medium",
                    "enable_web_search": True,
                    "enable_diagrams": True,
                    "enable_security_analysis": True,
                    "personas": ["SDE", "PM"],
                    "max_parallel_agents": 3,
                    "max_web_searches": 5
                }
            else:
                config_dict = {
                    "depth": config.depth.value,
                    "verbosity": config.verbosity.value,
                    "enable_web_search": config.enable_web_search,
                    "enable_diagrams": config.enable_diagrams,
                    "enable_security_analysis": config.enable_security_analysis,
                    "personas": config.personas,
                    "max_parallel_agents": config.max_parallel_agents,
                    "max_web_searches": config.max_web_searches
                }

            # Create or reset progress
            progress = db.query(ProjectProgress).filter(
                ProjectProgress.project_id == project_id
            ).first()

            if progress:
                progress.status = ProgressStatus.IN_PROGRESS
                progress.current_stage = ProgressStage.ANALYSIS
                progress.overall_percentage = 10
                progress.started_at = datetime.utcnow()
            else:
                progress = ProjectProgress(
                    project_id=project_id,
                    status=ProgressStatus.IN_PROGRESS,
                    current_stage=ProgressStage.ANALYSIS,
                    overall_percentage=10,
                    started_at=datetime.utcnow()
                )
                db.add(progress)

            db.commit()
            db.refresh(progress)

            # Log activity
            self._log_activity(
                db, progress.id, ActivityType.INFO,
                "Starting multi-agent analysis",
                {"config": config_dict}
            )

            # Get existing data
            files = db.query(FileMetadata).filter(FileMetadata.project_id == project_id).all()
            code_chunks = db.query(CodeChunk).filter(CodeChunk.project_id == project_id).all()

            file_paths = [f.file_path for f in files]
            chunks_data = [
                {
                    "id": c.id,
                    "chunk_type": c.chunk_type,
                    "name": c.name,
                    "signature": c.signature,
                    "file_path": c.file_path,
                    "code": c.code[:500]  # First 500 chars
                }
                for c in code_chunks[:100]  # First 100 chunks
            ]

            # Prepare initial state
            initial_state = {
                "project_id": project_id,
                "config": config_dict,
                "files": file_paths,
                "code_chunks": chunks_data
            }

            # Update progress
            progress.current_stage = ProgressStage.ANALYSIS
            progress.overall_percentage = 20
            db.commit()

            # Execute orchestration
            result = await self._execute_with_tracking(
                project_id, initial_state, db, progress.id
            )

            if result["success"]:
                # Save results
                await self._save_results(project_id, result["state"], db)

                # Mark complete
                progress.status = ProgressStatus.COMPLETED
                progress.current_stage = ProgressStage.COMPLETED
                progress.overall_percentage = 100
                progress.completed_at = datetime.utcnow()

                self._log_activity(
                    db, progress.id, ActivityType.SUCCESS,
                    "Analysis completed successfully",
                    {
                        "duration": result["duration"],
                        "agents_completed": len(result["agents_completed"]),
                        "total_tokens": result["state"].get("total_tokens", 0)
                    }
                )
            else:
                progress.status = ProgressStatus.FAILED
                progress.error_message = result.get("error", "Unknown error")

                self._log_activity(
                    db, progress.id, ActivityType.ERROR,
                    f"Analysis failed: {result.get('error')}",
                    None
                )

            db.commit()

            logger.info(f"✅ Analysis orchestration complete for project {project_id}")

            return result

        except Exception as e:
            logger.error(f"❌ Analysis orchestration failed: {str(e)}")

            # Mark as failed
            if progress:
                progress.status = ProgressStatus.FAILED
                progress.error_message = str(e)
                db.commit()

            raise

    async def _execute_with_tracking(
            self,
            project_id: str,
            initial_state: dict,
            db: Session,
            progress_id: str
    ) -> dict:
        """Execute workflow with real-time tracking."""

        logger.info("🎯 Executing agents with tracking...")

        # Track each agent execution
        agent_names = [
            "file_analyzer",
            "code_extractor",
            "web_searcher",
            "security_auditor",
            "doc_generator",
            "pm_summarizer"
        ]

        progress_percentages = [30, 40, 50, 60, 80, 90]

        # Create agent execution records
        for agent_name in agent_names:
            agent_exec = AgentExecution(
                project_id=project_id,
                agent_name=agent_name,
                agent_type=self._get_agent_type(agent_name),
                status="pending"
            )
            db.add(agent_exec)

        db.commit()

        # Execute workflow
        result = await self.orchestrator.execute(initial_state)

        # Update agent execution records
        for i, agent_name in enumerate(agent_names):
            agent_exec = db.query(AgentExecution).filter(
                AgentExecution.project_id == project_id,
                AgentExecution.agent_name == agent_name
            ).first()

            if agent_name in result.get("agents_completed", []):
                agent_exec.status = "completed"
                agent_exec.completed_at = datetime.utcnow()

                # Log activity
                self._log_activity(
                    db, progress_id, ActivityType.PROGRESS,
                    f"✅ {self._format_agent_name(agent_name)} completed",
                    None
                )

                # Update overall progress
                progress = db.query(ProjectProgress).filter(
                    ProjectProgress.id == progress_id
                ).first()
                progress.overall_percentage = progress_percentages[i]

            else:
                agent_exec.status = "skipped"

            db.commit()

        return result

    def _get_agent_type(self, agent_name: str) -> str:
        """Map agent name to type."""
        mapping = {
            "file_analyzer": "analyzer",
            "code_extractor": "analyzer",
            "web_searcher": "searcher",
            "security_auditor": "analyzer",
            "doc_generator": "generator",
            "pm_summarizer": "generator"
        }
        return mapping.get(agent_name, "unknown")

    def _format_agent_name(self, agent_name: str) -> str:
        """Format agent name for display."""
        return agent_name.replace("_", " ").title()

    async def _save_results(self, project_id: str, state: dict, db: Session):
        """Save agent results to database."""

        logger.info("💾 Saving agent results...")

        # Here you would save:
        # - SDE documentation
        # - PM summary
        # - Security findings
        # - Diagrams
        # etc.

        # For now, just log
        logger.info(f"SDE Doc length: {len(state.get('sde_documentation', ''))}")
        logger.info(f"PM Summary length: {len(state.get('pm_summary', '') or '')}")
        logger.info(f"API Signatures: {len(state.get('api_signatures', []))}")

    def _log_activity(
            self,
            db: Session,
            progress_id: str,
            activity_type: ActivityType,
            message: str,
            details: dict
    ):
        """Log an activity."""
        activity = ProgressActivity(
            progress_id=progress_id,
            activity_type=activity_type,
            message=message,
            details=details
        )
        db.add(activity)
        db.commit()
