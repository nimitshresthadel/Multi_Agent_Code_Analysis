import zipfile
import filetype
from pathlib import Path
from typing import Tuple, Dict
from app.utils.exceptions import FileValidationError
from app.core.config import settings


class FileValidator:
    """Validates uploaded files for code analysis."""

    # Recognized code file extensions
    CODE_EXTENSIONS = {
        '.py', '.js', '.ts', '.java', '.cpp', '.c', '.h', '.hpp',
        '.cs', '.go', '.rb', '.php', '.swift', '.kt', '.rs',
        '.jsx', '.tsx', '.vue', '.html', '.css', '.scss', '.sql',
        '.sh', '.bash', '.yaml', '.yml', '.json', '.xml', '.md'
    }

    # Extensions to skip
    SKIP_EXTENSIONS = {
        '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.ico',
        '.mp4', '.avi', '.mov', '.mp3', '.wav',
        '.zip', '.tar', '.gz', '.rar', '.7z',
        '.exe', '.dll', '.so', '.dylib',
        '.pdf', '.doc', '.docx', '.xls', '.xlsx'
    }

    @staticmethod
    def validate_file_size(file_size: int) -> None:
        """Validate file size is within limits."""
        if file_size > settings.MAX_UPLOAD_SIZE:
            size_mb = file_size / (1024 * 1024)
            limit_mb = settings.MAX_UPLOAD_SIZE / (1024 * 1024)
            raise FileValidationError(
                f"File size ({size_mb:.2f}MB) exceeds maximum allowed size ({limit_mb:.2f}MB)"
            )

    @staticmethod
    def validate_file_type(file_path: str) -> None:
        """Validate file is actually a ZIP file."""
        try:
            # Check magic bytes
            # mime = magic.Magic(mime=True)
            # file_type = mime.from_file(file_path)

            kind = filetype.guess(file_path)
            if kind is None:
                raise ValueError("Could not determine file type")

            if kind.mime not in ['application/zip', 'application/x-zip-compressed']:
                raise FileValidationError(
                    f"Invalid file type. Expected ZIP file, got {kind}. "
                    "Please upload a .zip file only."
                )
        except Exception as e:
            raise FileValidationError(f"Could not determine file type: {str(e)}")

    @staticmethod
    def validate_zip_integrity(file_path: str) -> None:
        """Validate ZIP file is not corrupted."""
        try:
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                # Test ZIP integrity
                corrupt_file = zip_ref.testzip()
                if corrupt_file:
                    raise FileValidationError(
                        f"ZIP file is corrupted. File '{corrupt_file}' failed integrity check."
                    )
        except zipfile.BadZipFile:
            raise FileValidationError(
                "The uploaded file is corrupted or not a valid ZIP archive. "
                "Please re-create the ZIP file and try again."
            )
        except Exception as e:
            raise FileValidationError(f"Error validating ZIP file: {str(e)}")

    @classmethod
    def validate_code_content(cls, file_path: str) -> Tuple[bool, Dict]:
        """
        Validate that ZIP contains actual code files.
        Returns: (is_valid, metadata_dict)
        """
        try:
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                all_files = zip_ref.namelist()

                # Filter out directories and system files
                files = [
                    f for f in all_files
                    if not f.endswith('/') and not f.startswith('__MACOSX')
                ]

                if not files:
                    raise FileValidationError(
                        "ZIP file is empty or contains only directories."
                    )

                # Count code files
                code_files = []
                binary_files = []
                other_files = []

                for file in files:
                    ext = Path(file).suffix.lower()
                    if ext in cls.CODE_EXTENSIONS:
                        code_files.append(file)
                    elif ext in cls.SKIP_EXTENSIONS:
                        binary_files.append(file)
                    else:
                        other_files.append(file)

                # Must have at least some code files
                if not code_files:
                    raise FileValidationError(
                        "No recognizable code files found in ZIP. "
                        "Repository appears to contain only documentation or binary files. "
                        f"Total files: {len(files)}, Binary/Media: {len(binary_files)}, Other: {len(other_files)}"
                    )

                # Calculate statistics
                code_percentage = (len(code_files) / len(files)) * 100

                if code_percentage < 10:
                    raise FileValidationError(
                        f"Insufficient code content. Only {len(code_files)} out of {len(files)} "
                        f"files ({code_percentage:.1f}%) are recognized code files. "
                        "This appears to be primarily documentation or binary content."
                    )

                # Gather metadata
                metadata = {
                    "total_files": len(files),
                    "code_files": len(code_files),
                    "binary_files": len(binary_files),
                    "other_files": len(other_files),
                    "code_percentage": round(code_percentage, 2),
                    "detected_languages": cls._detect_languages(code_files),
                }

                return True, metadata

        except FileValidationError:
            raise
        except Exception as e:
            raise FileValidationError(f"Error analyzing ZIP content: {str(e)}")

    @staticmethod
    def _detect_languages(code_files: list) -> Dict[str, int]:
        """Detect programming languages from file extensions."""
        language_map = {
            '.py': 'Python',
            '.js': 'JavaScript',
            '.ts': 'TypeScript',
            '.jsx': 'React',
            '.tsx': 'React TypeScript',
            '.java': 'Java',
            '.cpp': 'C++',
            '.c': 'C',
            '.cs': 'C#',
            '.go': 'Go',
            '.rb': 'Ruby',
            '.php': 'PHP',
            '.swift': 'Swift',
            '.kt': 'Kotlin',
            '.rs': 'Rust',
        }

        languages = {}
        for file in code_files:
            ext = Path(file).suffix.lower()
            lang = language_map.get(ext, 'Other')
            languages[lang] = languages.get(lang, 0) + 1

        return languages
