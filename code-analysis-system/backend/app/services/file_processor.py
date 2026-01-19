from pathlib import Path
from typing import Dict, List, Tuple
import mimetypes
import hashlib


class FileProcessor:
    """Process files and determine which should be analyzed."""

    # Skip patterns (already defined in RepositoryAnalyzer)
    SKIP_PATTERNS = [
        "__pycache__", ".git", ".venv", "venv", "node_modules",
        ".pytest_cache", "build", "dist", ".idea", ".vscode",
        "*.pyc", "*.pyo", "*.so", "*.dylib", "*.dll",
        ".DS_Store", "Thumbs.db", "*.log", "*.tmp",
        "*.min.js", "*.min.css", "package-lock.json", "yarn.lock"
    ]

    # File type classification
    SOURCE_EXTENSIONS = {
        '.py': 'python',
        '.js': 'javascript',
        '.ts': 'typescript',
        '.jsx': 'javascript',
        '.tsx': 'typescript',
        '.java': 'java',
        '.cpp': 'cpp',
        '.c': 'c',
        '.go': 'go',
        '.rs': 'rust',
        '.rb': 'ruby',
        '.php': 'php'
    }

    CONFIG_FILES = [
        'backend_requirements.txt', 'package.json', 'pom.xml', 'build.gradle',
        'pyproject.toml', 'setup.py', 'tsconfig.json', 'webpack.config.js',
        '.env', '.env.example', 'Dockerfile', 'docker-compose.yml'
    ]

    def __init__(self, project_path: str):
        self.project_path = Path(project_path)

    def process_all_files(self, file_list: List[str]) -> Dict:
        """Process all files and categorize them."""
        results = {
            "process": [],
            "skip": [],
            "config": [],
            "test": [],
            "documentation": []
        }

        for file_path in file_list:
            category, metadata = self._classify_file(file_path)
            results[category].append(metadata)

        return results

    def _classify_file(self, file_path: str) -> Tuple[str, Dict]:
        """Classify a single file."""
        full_path = self.project_path / file_path

        # Basic metadata
        metadata = {
            "file_path": file_path,
            "file_name": Path(file_path).name,
            "file_extension": Path(file_path).suffix,
            "file_size": full_path.stat().st_size if full_path.exists() else 0
        }

        # Check if should skip
        if self._should_skip(file_path):
            metadata["skip_reason"] = self._get_skip_reason(file_path)
            return "skip", metadata

        # Check if config file
        if any(config in file_path for config in self.CONFIG_FILES):
            metadata["file_type"] = "config"
            return "config", metadata

        # Check if test file
        if "test" in file_path.lower() or "spec" in file_path.lower():
            metadata["file_type"] = "test"
            return "test", metadata

        # Check if documentation
        if file_path.endswith(('.md', '.rst', '.txt')) or 'README' in file_path:
            metadata["file_type"] = "documentation"
            return "documentation", metadata

        # Check if source code
        ext = Path(file_path).suffix
        if ext in self.SOURCE_EXTENSIONS:
            metadata["file_type"] = "source"
            metadata["language"] = self.SOURCE_EXTENSIONS[ext]
            metadata["priority_level"] = self._calculate_priority(file_path)
            return "process", metadata

        # Unknown file type
        metadata["skip_reason"] = "unknown_type"
        return "skip", metadata

    def _should_skip(self, file_path: str) -> bool:
        """Check if file should be skipped."""
        file_path_lower = file_path.lower()

        for pattern in self.SKIP_PATTERNS:
            if pattern.startswith("*."):
                if file_path.endswith(pattern[1:]):
                    return True
            elif pattern in file_path_lower:
                return True

        # Skip binary files
        if self._is_binary(file_path):
            return True

        # Skip very large files (> 1MB)
        full_path = self.project_path / file_path
        if full_path.exists() and full_path.stat().st_size > 1_000_000:
            return True

        return False

    def _get_skip_reason(self, file_path: str) -> str:
        """Get reason for skipping file."""
        if self._is_binary(file_path):
            return "binary"

        full_path = self.project_path / file_path
        if full_path.exists() and full_path.stat().st_size > 1_000_000:
            return "too_large"

        for pattern in self.SKIP_PATTERNS:
            if pattern in file_path.lower():
                return f"matches_pattern_{pattern}"

        return "unknown"

    def _is_binary(self, file_path: str) -> bool:
        """Check if file is binary."""
        mime_type, _ = mimetypes.guess_type(file_path)

        if mime_type:
            return not mime_type.startswith('text')

        # Check by extension
        binary_extensions = [
            '.exe', '.dll', '.so', '.dylib', '.bin', '.pdf',
            '.jpg', '.jpeg', '.png', '.gif', '.ico', '.svg',
            '.zip', '.tar', '.gz', '.rar', '.7z'
        ]

        return any(file_path.endswith(ext) for ext in binary_extensions)

    def _calculate_priority(self, file_path: str) -> int:
        """Calculate priority level (0-10) for file."""
        priority = 5  # Default

        file_lower = file_path.lower()

        # Entry points
        if any(entry in file_path for entry in ['main.py', 'app.py', 'index.js', 'server.js']):
            priority = 10

        # Routes/API
        elif any(keyword in file_lower for keyword in ['route', 'api', 'endpoint', 'controller']):
            priority = 9

        # Models/Schemas
        elif any(keyword in file_lower for keyword in ['model', 'schema', 'entity']):
            priority = 8

        # Services/Business Logic
        elif any(keyword in file_lower for keyword in ['service', 'business', 'logic']):
            priority = 7

        # Utils/Helpers
        elif any(keyword in file_lower for keyword in ['util', 'helper', 'common']):
            priority = 6

        # Tests
        elif 'test' in file_lower:
            priority = 3

        return priority

    def extract_file_metadata(self, file_path: str) -> Dict:
        """Extract detailed metadata from a file."""
        full_path = self.project_path / file_path

        metadata = {
            "file_path": file_path,
            "file_name": Path(file_path).name,
            "file_extension": Path(file_path).suffix,
            "file_size": 0,
            "lines_of_code": 0,
            "has_classes": False,
            "has_functions": False,
            "imports": [],
            "complexity_score": 0.0
        }

        if not full_path.exists():
            return metadata

        metadata["file_size"] = full_path.stat().st_size

        # Read file content
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')

                # Count LOC (non-empty, non-comment)
                metadata["lines_of_code"] = len([
                    line for line in lines
                    if line.strip() and not line.strip().startswith(('#', '//', '/*'))
                ])

                # Detect classes and functions (simple heuristic)
                metadata["has_classes"] = 'class ' in content
                metadata["has_functions"] = any(
                    keyword in content
                    for keyword in ['def ', 'function ', 'func ', 'fn ']
                )

                # Extract imports (Python example)
                if file_path.endswith('.py'):
                    metadata["imports"] = self._extract_python_imports(content)

                # Simple complexity score
                metadata["complexity_score"] = self._calculate_complexity(content)

        except:
            pass

        return metadata

    def _extract_python_imports(self, content: str) -> List[str]:
        """Extract Python imports."""
        imports = []
        for line in content.split('\n'):
            line = line.strip()
            if line.startswith('import ') or line.startswith('from '):
                imports.append(line.split()[1].split('.')[0])
        return list(set(imports))

    def _calculate_complexity(self, content: str) -> float:
        """Calculate simple complexity score."""
        # Count decision points
        decision_keywords = ['if ', 'elif ', 'else:', 'for ', 'while ', 'try:', 'except:']
        complexity = sum(content.count(keyword) for keyword in decision_keywords)

        # Normalize by lines of code
        lines = len([l for l in content.split('\n') if l.strip()])
        return complexity / max(lines, 1) * 10  # Scale 0-10
