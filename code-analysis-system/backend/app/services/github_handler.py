import re
import requests
from typing import Tuple, Dict
from pathlib import Path
import zipfile
import shutil
from app.core.config import settings
from app.utils.exceptions import FileValidationError
import logging

logging.basicConfig(
    level=logging.DEBUG,
)

logger = logging.getLogger(__name__)

class GitHubHandler:
    """Handles GitHub repository operations."""

    GITHUB_URL_PATTERN = re.compile(
        r'^https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$'
    )

    @classmethod
    def validate_github_url(cls, url: str) -> Tuple[str, str]:
        """
        Validate GitHub URL and extract owner/repo.
        Returns: (owner, repo)
        """
        print(f"coming url", url)
        logger.debug("coming_url", url)
        match = cls.GITHUB_URL_PATTERN.match(url.strip())
        if not match:
            raise FileValidationError(
                "Invalid GitHub URL format. "
                "Expected format: https://github.com/owner/repository"
            )
        return match.groups()

    @staticmethod
    def download_repository(url: str, project_id: str) -> Tuple[str, int, Dict]:
        """
        Download GitHub repository as ZIP.
        Returns: (file_path, file_size, metadata)
        """
        try:
            # Extract owner and repo
            owner, repo = GitHubHandler.validate_github_url(url)

            # Build archive download URL
            archive_url = f"https://github.com/{owner}/{repo}/archive/refs/heads/main.zip"

            # Try main branch first, then master
            for branch in ['main', 'master']:
                archive_url = f"https://github.com/{owner}/{repo}/archive/refs/heads/{branch}.zip"

                headers = {}
                if settings.GITHUB_TOKEN:
                    headers['Authorization'] = f"token {settings.GITHUB_TOKEN}"

                response = requests.get(archive_url, headers=headers, stream=True, timeout=30)

                if response.status_code == 200:
                    break
            else:
                raise FileValidationError(
                    f"Could not download repository. "
                    f"Please check the URL and ensure the repository is public. "
                    f"Status code: {response.status_code}"
                )

            # Save ZIP file
            file_path = Path(settings.UPLOAD_DIR) / f"{project_id}_github.zip"
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            file_size = file_path.stat().st_size

            # Validate downloaded file
            from app.services.validator import FileValidator
            FileValidator.validate_file_size(file_size)
            FileValidator.validate_zip_integrity(str(file_path))
            is_valid, metadata = FileValidator.validate_code_content(str(file_path))

            metadata['github_url'] = url
            metadata['repository'] = f"{owner}/{repo}"

            return str(file_path), file_size, metadata

        except FileValidationError:
            raise
        except requests.RequestException as e:
            raise FileValidationError(
                f"Failed to download repository: {str(e)}. "
                "Please check your internet connection and the repository URL."
            )
        except Exception as e:
            raise FileValidationError(f"Error downloading GitHub repository: {str(e)}")
