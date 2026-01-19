import shutil
import zipfile
from pathlib import Path
from typing import Tuple
import uuid
from app.core.config import settings
from app.services.validator import FileValidator
from app.utils.exceptions import FileValidationError


class FileHandler:
    """Handles file storage and management."""

    @staticmethod
    async def save_upload_file(file, project_id: str) -> Tuple[str, int, dict]:
        """
        Save uploaded file and validate it.
        Returns: (file_path, file_size, metadata)
        """
        # Create unique filename
        file_extension = Path(file.filename).suffix
        unique_filename = f"{project_id}_{uuid.uuid4()}{file_extension}"
        file_path = Path(settings.UPLOAD_DIR) / unique_filename

        # Save file
        try:
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
        except Exception as e:
            raise FileValidationError(f"Failed to save file: {str(e)}")

        # Get file size
        file_size = file_path.stat().st_size

        # Validate file
        try:
            FileValidator.validate_file_size(file_size)
            FileValidator.validate_file_type(str(file_path))
            FileValidator.validate_zip_integrity(str(file_path))
            is_valid, metadata = FileValidator.validate_code_content(str(file_path))

            return str(file_path), file_size, metadata

        except FileValidationError:
            # Clean up invalid file
            file_path.unlink(missing_ok=True)
            raise

    @staticmethod
    def extract_zip(zip_path: str, project_id: str) -> str:
        """
        Extract ZIP file to project directory.
        Returns: extraction_path
        """
        extract_path = Path(settings.PROJECT_DIR) / project_id
        extract_path.mkdir(parents=True, exist_ok=True)

        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_path)

            return str(extract_path)

        except Exception as e:
            # Clean up on error
            shutil.rmtree(extract_path, ignore_errors=True)
            raise FileValidationError(f"Failed to extract ZIP file: {str(e)}")

    @staticmethod
    def delete_project_files(project_id: str, file_path: str = None):
        """Delete all files associated with a project."""
        # Delete extracted files
        extract_path = Path(settings.PROJECT_DIR) / project_id
        if extract_path.exists():
            shutil.rmtree(extract_path, ignore_errors=True)

        # Delete uploaded ZIP
        if file_path:
            zip_path = Path(file_path)
            if zip_path.exists():
                zip_path.unlink(missing_ok=True)
