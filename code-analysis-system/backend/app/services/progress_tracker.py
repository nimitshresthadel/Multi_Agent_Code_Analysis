from typing import Optional
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.models.progress import (
    ProjectProgress, ProgressActivity, ProgressStatus,
    ProgressStage, ActivityType
)


class ProgressTracker:
    """Tracks and broadcasts progress updates for project processing."""

    def __init__(self, project_id: str, db: Session):
        self.project_id = project_id
        self.db = db
        self.progress = self._get_or_create_progress()

    def _get_or_create_progress(self) -> ProjectProgress:
        """Get existing or create new progress record."""
        progress = self.db.query(ProjectProgress).filter(
            ProjectProgress.project_id == self.project_id
        ).first()

        if not progress:
            progress = ProjectProgress(
                project_id=self.project_id,
                status=ProgressStatus.QUEUED,
                current_stage=ProgressStage.UPLOAD
            )
            self.db.add(progress)
            self.db.commit()
            self.db.refresh(progress)

        return progress

    # ==================== Stage Management ====================

    def start_stage(self, stage: ProgressStage, total_items: int = 0):
        """Start a new processing stage."""
        self.progress.current_stage = stage
        self.progress.status = ProgressStatus.IN_PROGRESS
        self.progress.current_stage_percentage = 0.0

        if stage == ProgressStage.FILE_PROCESSING:
            self.progress.total_files = total_items
            self.progress.processed_files = 0
        elif stage == ProgressStage.CODE_CHUNKING:
            self.progress.total_chunks = total_items
            self.progress.processed_chunks = 0

        if not self.progress.started_at:
            self.progress.started_at = datetime.utcnow()

        self.db.commit()

        # Add activity
        self.add_activity(
            ActivityType.MILESTONE,
            f"Started: {self._stage_label(stage)}",
            stage=stage
        )

    def complete_stage(self, stage: ProgressStage):
        """Mark a stage as complete."""
        self.progress.current_stage_percentage = 100.0
        self._update_overall_percentage()

        self.db.commit()

        # Add activity
        self.add_activity(
            ActivityType.SUCCESS,
            f"Completed: {self._stage_label(stage)}",
            stage=stage
        )

    def complete_processing(self):
        """Mark entire processing as complete."""
        self.progress.status = ProgressStatus.COMPLETED
        self.progress.current_stage = ProgressStage.COMPLETED
        self.progress.overall_percentage = 100.0
        self.progress.completed_at = datetime.utcnow()

        self.db.commit()

        self.add_activity(
            ActivityType.MILESTONE,
            "🎉 Analysis Complete! Your documentation is ready.",
            stage=ProgressStage.COMPLETED
        )

    def mark_failed(self, error_message: str):
        """Mark processing as failed."""
        self.progress.status = ProgressStatus.FAILED
        self.progress.error_message = error_message
        self.progress.completed_at = datetime.utcnow()

        self.db.commit()

        self.add_activity(
            ActivityType.ERROR,
            f"Processing failed: {error_message}"
        )

    # ==================== File Progress ====================

    def update_file_progress(self, file_name: str, file_path: str,
                             current: int, total: int):
        """Update progress for file processing."""
        self.progress.current_file = file_name
        self.progress.processed_files = current
        self.progress.total_files = total

        # Calculate stage percentage
        if total > 0:
            self.progress.current_stage_percentage = (current / total) * 100

        self._update_overall_percentage()

        self.db.commit()

        # Add activity (every 10 files to avoid spam)
        if current % 10 == 0 or current == total:
            self.add_activity(
                ActivityType.INFO,
                f"Processing file {current}/{total}: {file_name}",
                file_name=file_name,
                file_path=file_path
            )

    def update_chunk_progress(self, file_name: str, chunks_created: int):
        """Update progress for chunking."""
        self.progress.processed_chunks += chunks_created

        if self.progress.total_chunks > 0:
            self.progress.current_stage_percentage = (
                    (self.progress.processed_chunks / self.progress.total_chunks) * 100
            )

        self._update_overall_percentage()

        self.db.commit()

        self.add_activity(
            ActivityType.INFO,
            f"Created {chunks_created} code chunks from {file_name}",
            file_name=file_name
        )

    # ==================== Activity Feed ====================

    def add_activity(self, activity_type: ActivityType, message: str,
                     stage: Optional[ProgressStage] = None,
                     details: Optional[str] = None,
                     file_name: Optional[str] = None,
                     file_path: Optional[str] = None):
        """Add an activity to the feed."""
        activity = ProgressActivity(
            progress_id=self.progress.id,
            activity_type=activity_type,
            stage=stage or self.progress.current_stage,
            message=message,
            details=details,
            file_name=file_name,
            file_path=file_path
        )

        self.db.add(activity)
        self.db.commit()

    def add_warning(self, message: str, file_name: Optional[str] = None):
        """Add a warning message."""
        self.add_activity(ActivityType.WARNING, message, file_name=file_name)

    def add_info(self, message: str, details: Optional[str] = None):
        """Add an info message."""
        self.add_activity(ActivityType.INFO, message, details=details)

    # ==================== Helper Methods ====================

    def _update_overall_percentage(self):
        """Calculate overall progress percentage."""
        stage_weights = {
            ProgressStage.UPLOAD: 5,
            ProgressStage.EXTRACTION: 5,
            ProgressStage.ANALYSIS: 15,
            ProgressStage.FILE_PROCESSING: 25,
            ProgressStage.CODE_CHUNKING: 25,
            ProgressStage.SEMANTIC_INDEXING: 20,
            ProgressStage.DOC_GENERATION: 5,
        }

        completed_stages = {
            ProgressStage.UPLOAD: 0,
            ProgressStage.EXTRACTION: 0,
            ProgressStage.ANALYSIS: 0,
            ProgressStage.FILE_PROCESSING: 0,
            ProgressStage.CODE_CHUNKING: 0,
            ProgressStage.SEMANTIC_INDEXING: 0,
            ProgressStage.DOC_GENERATION: 0,
        }

        # Mark completed stages
        stage_order = list(ProgressStage)
        current_index = stage_order.index(self.progress.current_stage)

        for i, stage in enumerate(stage_order[:current_index]):
            if stage in stage_weights:
                completed_stages[stage] = 100

        # Add current stage progress
        if self.progress.current_stage in stage_weights:
            completed_stages[self.progress.current_stage] = (
                self.progress.current_stage_percentage
            )

        # Calculate weighted average
        total_weight = sum(stage_weights.values())
        weighted_sum = sum(
            (completed_stages.get(stage, 0) * weight) / 100
            for stage, weight in stage_weights.items()
        )

        self.progress.overall_percentage = (weighted_sum / total_weight) * 100

    def _stage_label(self, stage: ProgressStage) -> str:
        """Get user-friendly stage label."""
        labels = {
            ProgressStage.UPLOAD: "Uploading Files",
            ProgressStage.EXTRACTION: "Extracting Archive",
            ProgressStage.ANALYSIS: "Analyzing Repository Structure",
            ProgressStage.FILE_PROCESSING: "Processing Code Files",
            ProgressStage.CODE_CHUNKING: "Breaking Down Code",
            ProgressStage.SEMANTIC_INDEXING: "Building Code Understanding",
            ProgressStage.DOC_GENERATION: "Generating Documentation",
            ProgressStage.COMPLETED: "Complete"
        }
        return labels.get(stage, stage.value)
