import os
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import re


class RepositoryAnalyzer:
    """Analyzes repository structure and detects project type."""

    # Detection patterns for different project types
    PROJECT_PATTERNS = {
        "fastapi": {
            "files": ["main.py", "app.py"],
            "imports": ["from fastapi import", "import fastapi"],
            "configs": ["backend_requirements.txt", "pyproject.toml"],
            "indicators": ["@app.get", "@app.post", "FastAPI("]
        },
        "flask": {
            "files": ["app.py", "wsgi.py"],
            "imports": ["from flask import", "import flask"],
            "configs": ["backend_requirements.txt"],
            "indicators": ["@app.route", "Flask(__name__)"]
        },
        "django": {
            "files": ["manage.py", "wsgi.py"],
            "imports": ["django"],
            "configs": ["backend_requirements.txt", "settings.py"],
            "indicators": ["INSTALLED_APPS", "DATABASES"]
        },
        "react": {
            "files": ["package.json", "src/App.js", "src/index.js"],
            "imports": ["import React", "from 'react'"],
            "configs": ["package.json", "tsconfig.json"],
            "indicators": ["React.Component", "useState", "useEffect"]
        },
        "express": {
            "files": ["package.json", "server.js", "app.js"],
            "imports": ["express", "const express"],
            "configs": ["package.json"],
            "indicators": ["app.listen", "express()"]
        },
        "spring_boot": {
            "files": ["pom.xml", "build.gradle"],
            "imports": ["org.springframework"],
            "configs": ["application.properties", "application.yml"],
            "indicators": ["@SpringBootApplication", "@RestController"]
        }
    }

    # Files/directories to skip
    SKIP_PATTERNS = [
        "__pycache__", ".git", ".venv", "venv", "node_modules",
        ".pytest_cache", "build", "dist", ".idea", ".vscode",
        "*.pyc", "*.pyo", "*.so", "*.dylib", "*.dll",
        ".DS_Store", "Thumbs.db", "*.log", "*.tmp"
    ]

    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.files_list = []
        self.file_tree = {}

    def analyze(self) -> Dict:
        """Main analysis method."""
        print(f"🔍 Analyzing repository at: {self.project_path}")

        # 1. Scan directory structure
        self._scan_directory()

        # 2. Detect project type
        project_type, confidence = self._detect_project_type()

        # 3. Find entry points
        entry_points = self._find_entry_points(project_type)

        # 4. Identify important files
        important_files = self._identify_important_files(project_type)

        # 5. Parse configuration files
        dependencies, tech_stack = self._parse_configs(project_type)

        # 6. Detect API endpoints (if applicable)
        endpoints = self._detect_endpoints(project_type)

        # 7. Detect database usage
        database_info = self._detect_database()

        # 8. Check for tests
        test_info = self._detect_tests()

        # 9. Calculate statistics
        stats = self._calculate_statistics()

        return {
            "repository_type": project_type,
            "primary_language": self._detect_primary_language(),
            "framework": self._get_framework_name(project_type),
            "confidence_score": confidence,
            "entry_points": entry_points,
            "important_files": important_files,
            "config_files": self._find_config_files(),
            "dependencies": dependencies,
            "tech_stack": tech_stack,
            "endpoints": endpoints,
            "endpoints_count": len(endpoints),
            "database_type": database_info.get("type"),
            "orm_detected": database_info.get("orm"),
            "has_tests": test_info.get("has_tests", False),
            "test_framework": test_info.get("framework"),
            "total_files": stats["total_files"],
            "code_files": stats["code_files"],
            "total_lines": stats["total_lines"],
            "analysis_notes": self._generate_notes(project_type, confidence)
        }

    def _scan_directory(self):
        """Scan directory and build file list."""
        for root, dirs, files in os.walk(self.project_path):
            # Remove skip directories
            dirs[:] = [d for d in dirs if not self._should_skip(d)]

            for file in files:
                if not self._should_skip(file):
                    file_path = Path(root) / file
                    rel_path = file_path.relative_to(self.project_path)
                    self.files_list.append(str(rel_path))

    def _should_skip(self, name: str) -> bool:
        """Check if file/directory should be skipped."""
        for pattern in self.SKIP_PATTERNS:
            if pattern.startswith("*."):
                if name.endswith(pattern[1:]):
                    return True
            elif name == pattern or name.startswith(pattern):
                return True
        return False

    def _detect_project_type(self) -> Tuple[str, float]:
        """Detect project type with confidence score."""
        scores = {}

        for proj_type, patterns in self.PROJECT_PATTERNS.items():
            score = 0
            max_score = 0

            # Check for specific files
            for file in patterns["files"]:
                max_score += 3
                if self._file_exists(file):
                    score += 3

            # Check for config files
            for config in patterns["configs"]:
                max_score += 2
                if self._file_exists(config):
                    score += 2

            # Check file contents for imports and indicators
            max_score += 5
            content_score = self._check_file_contents(patterns)
            score += content_score

            if max_score > 0:
                scores[proj_type] = score / max_score

        if not scores:
            return "unknown", 0.0

        best_match = max(scores.items(), key=lambda x: x[1])
        return best_match[0], best_match[1]

    def _file_exists(self, pattern: str) -> bool:
        """Check if file matching pattern exists."""
        for file in self.files_list:
            if file.endswith(pattern) or pattern in file:
                return True
        return False

    def _check_file_contents(self, patterns: Dict) -> float:
        """Check file contents for imports and indicators."""
        score = 0
        files_checked = 0

        # Check up to 10 relevant files
        for file_path in self.files_list[:10]:
            full_path = self.project_path / file_path
            if full_path.suffix in ['.py', '.js', '.java', '.ts', '.jsx', '.tsx']:
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        content = f.read(5000)  # Read first 5KB
                        files_checked += 1

                        for import_pattern in patterns["imports"]:
                            if import_pattern in content:
                                score += 1

                        for indicator in patterns["indicators"]:
                            if indicator in content:
                                score += 1
                except:
                    pass

        return min(score / max(files_checked, 1), 5.0)

    def _find_entry_points(self, project_type: str) -> List[str]:
        """Find entry points based on project type."""
        entry_points = []

        if project_type in self.PROJECT_PATTERNS:
            for file in self.PROJECT_PATTERNS[project_type]["files"]:
                for f in self.files_list:
                    if f.endswith(file):
                        entry_points.append(f)

        # Common entry points
        common_entries = ["main.py", "app.py", "index.js", "server.js", "Main.java"]
        for entry in common_entries:
            for f in self.files_list:
                if f.endswith(entry) and f not in entry_points:
                    entry_points.append(f)

        return entry_points[:5]  # Return top 5

    def _identify_important_files(self, project_type: str) -> List[Dict]:
        """Identify important files with priority."""
        important = []

        priority_patterns = {
            10: ["main.py", "app.py", "index.js", "server.js"],
            8: ["routes", "api", "controllers", "views"],
            7: ["models", "schemas", "entities"],
            6: ["services", "utils", "helpers"],
            5: ["config", "settings"],
            3: ["tests", "test_"]
        }

        for priority, patterns in priority_patterns.items():
            for file in self.files_list:
                for pattern in patterns:
                    if pattern in file.lower():
                        important.append({
                            "file": file,
                            "priority": priority,
                            "reason": f"Contains '{pattern}'"
                        })
                        break

        # Sort by priority and return top 20
        important.sort(key=lambda x: x["priority"], reverse=True)
        return important[:20]

    def _parse_configs(self, project_type: str) -> Tuple[Dict, List]:
        """Parse configuration files for dependencies."""
        dependencies = {}
        tech_stack = []

        # Python projects
        if "backend_requirements.txt" in str(self.files_list):
            deps = self._parse_requirements()
            dependencies.update(deps)
            tech_stack.extend(self._infer_tech_from_deps(deps))

        # Node.js projects
        if "package.json" in str(self.files_list):
            deps = self._parse_package_json()
            dependencies.update(deps)
            tech_stack.extend(self._infer_tech_from_deps(deps))

        # Java projects
        if "pom.xml" in str(self.files_list):
            tech_stack.append("Maven")
        if "build.gradle" in str(self.files_list):
            tech_stack.append("Gradle")

        return dependencies, list(set(tech_stack))

    def _parse_requirements(self) -> Dict:
        """Parse backend_requirements.txt file."""
        deps = {}
        for file in self.files_list:
            if file.endswith("backend_requirements.txt"):
                try:
                    with open(self.project_path / file, 'r') as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith('#'):
                                if '==' in line:
                                    name, version = line.split('==')
                                    deps[name.strip()] = version.strip()
                                else:
                                    deps[line.split('[')[0].strip()] = "latest"
                except:
                    pass
        return deps

    def _parse_package_json(self) -> Dict:
        """Parse package.json file."""
        deps = {}
        for file in self.files_list:
            if file.endswith("package.json"):
                try:
                    with open(self.project_path / file, 'r') as f:
                        data = json.load(f)
                        if "dependencies" in data:
                            deps.update(data["dependencies"])
                        if "devDependencies" in data:
                            deps.update(data["devDependencies"])
                except:
                    pass
        return deps

    def _infer_tech_from_deps(self, deps: Dict) -> List[str]:
        """Infer technology stack from dependencies."""
        tech = []

        tech_mapping = {
            "fastapi": "FastAPI",
            "flask": "Flask",
            "django": "Django",
            "express": "Express.js",
            "react": "React",
            "vue": "Vue.js",
            "angular": "Angular",
            "sqlalchemy": "SQLAlchemy",
            "mongoose": "MongoDB",
            "redis": "Redis",
            "celery": "Celery",
            "pytest": "PyTest",
            "jest": "Jest"
        }

        for dep_name, tech_name in tech_mapping.items():
            if any(dep_name in d.lower() for d in deps.keys()):
                tech.append(tech_name)

        return tech

    def _detect_endpoints(self, project_type: str) -> List[Dict]:
        """Detect API endpoints in the code."""
        endpoints = []

        if project_type in ["fastapi", "flask"]:
            endpoints = self._detect_python_endpoints()
        elif project_type in ["express"]:
            endpoints = self._detect_js_endpoints()

        return endpoints

    def _detect_python_endpoints(self) -> List[Dict]:
        """Detect Python API endpoints."""
        endpoints = []
        route_pattern = re.compile(r'@app\.(get|post|put|delete|patch)\(["\']([^"\']+)')

        for file in self.files_list:
            if file.endswith('.py'):
                try:
                    with open(self.project_path / file, 'r') as f:
                        content = f.read()
                        matches = route_pattern.findall(content)
                        for method, path in matches:
                            endpoints.append({
                                "method": method.upper(),
                                "path": path,
                                "file": file
                            })
                except:
                    pass

        return endpoints

    def _detect_js_endpoints(self) -> List[Dict]:
        """Detect JavaScript API endpoints."""
        endpoints = []
        route_pattern = re.compile(r'app\.(get|post|put|delete|patch)\(["\']([^"\']+)')

        for file in self.files_list:
            if file.endswith('.js') or file.endswith('.ts'):
                try:
                    with open(self.project_path / file, 'r') as f:
                        content = f.read()
                        matches = route_pattern.findall(content)
                        for method, path in matches:
                            endpoints.append({
                                "method": method.upper(),
                                "path": path,
                                "file": file
                            })
                except:
                    pass

        return endpoints

    def _detect_database(self) -> Dict:
        """Detect database usage."""
        db_info = {"type": None, "orm": None}

        # Check for common database indicators
        for file in self.files_list:
            try:
                with open(self.project_path / file, 'r') as f:
                    content = f.read(10000).lower()

                    if "sqlalchemy" in content:
                        db_info["orm"] = "SQLAlchemy"
                        if "postgresql" in content or "psycopg" in content:
                            db_info["type"] = "PostgreSQL"
                        elif "mysql" in content:
                            db_info["type"] = "MySQL"
                        elif "sqlite" in content:
                            db_info["type"] = "SQLite"

                    if "mongoose" in content:
                        db_info["orm"] = "Mongoose"
                        db_info["type"] = "MongoDB"

                    if "redis" in content:
                        db_info["type"] = "Redis"
            except:
                pass

        return db_info

    def _detect_tests(self) -> Dict:
        """Detect test files and framework."""
        test_info = {"has_tests": False, "framework": None}

        test_files = [f for f in self.files_list if 'test' in f.lower()]

        if test_files:
            test_info["has_tests"] = True

            # Check first test file for framework
            try:
                with open(self.project_path / test_files[0], 'r') as f:
                    content = f.read(5000)
                    if "pytest" in content or "import pytest" in content:
                        test_info["framework"] = "pytest"
                    elif "unittest" in content:
                        test_info["framework"] = "unittest"
                    elif "jest" in content or "describe(" in content:
                        test_info["framework"] = "jest"
            except:
                pass

        return test_info

    def _calculate_statistics(self) -> Dict:
        """Calculate repository statistics."""
        stats = {
            "total_files": len(self.files_list),
            "code_files": 0,
            "total_lines": 0
        }

        code_extensions = ['.py', '.js', '.ts', '.java', '.cpp', '.c', '.go', '.rs']

        for file in self.files_list:
            file_path = self.project_path / file

            # Count code files
            if any(file.endswith(ext) for ext in code_extensions):
                stats["code_files"] += 1

                # Count lines
                try:
                    with open(file_path, 'r') as f:
                        stats["total_lines"] += len(f.readlines())
                except:
                    pass

        return stats

    def _detect_primary_language(self) -> str:
        """Detect primary programming language."""
        language_counts = {}

        extension_map = {
            '.py': 'Python',
            '.js': 'JavaScript',
            '.ts': 'TypeScript',
            '.java': 'Java',
            '.cpp': 'C++',
            '.c': 'C',
            '.go': 'Go',
            '.rs': 'Rust'
        }

        for file in self.files_list:
            for ext, lang in extension_map.items():
                if file.endswith(ext):
                    language_counts[lang] = language_counts.get(lang, 0) + 1

        if language_counts:
            return max(language_counts.items(), key=lambda x: x[1])[0]
        return "Unknown"

    def _get_framework_name(self, project_type: str) -> str:
        """Get human-readable framework name."""
        framework_map = {
            "fastapi": "FastAPI",
            "flask": "Flask",
            "django": "Django",
            "react": "React",
            "express": "Express.js",
            "spring_boot": "Spring Boot"
        }
        return framework_map.get(project_type, "Unknown")

    def _find_config_files(self) -> List[str]:
        """Find all configuration files."""
        config_patterns = [
            "backend_requirements.txt", "package.json", "pom.xml", "build.gradle",
            "pyproject.toml", "setup.py", "tsconfig.json", ".env",
            "config.py", "settings.py", "application.properties"
        ]

        configs = []
        for file in self.files_list:
            if any(pattern in file for pattern in config_patterns):
                configs.append(file)

        return configs

    def _generate_notes(self, project_type: str, confidence: float) -> str:
        """Generate analysis notes."""
        notes = []

        if confidence < 0.5:
            notes.append("Low confidence in project type detection.")
        elif confidence < 0.75:
            notes.append("Moderate confidence in project type detection.")
        else:
            notes.append("High confidence in project type detection.")

        if project_type == "unknown":
            notes.append("Could not determine project type. Manual review recommended.")

        return " ".join(notes)
