import logging
from typing import Dict, List
from openai import OpenAI
import os
from app.services.web_search import WebSearchService

logger = logging.getLogger(__name__)


class FileAnalyzerAgent:
    """Agent 1: Analyzes file structure and architecture."""

    def __init__(self):
        self.name = "File Analyzer"
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    async def execute(self, state: Dict) -> Dict:
        """Analyze project file structure."""

        logger.info(f"🤖 {self.name}: Starting file structure analysis")

        # Get files from state
        files = state.get("files", [])

        # Analyze structure
        response = self.client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {
                    "role": "system",
                    "content": "You are a software architect analyzing project structure. Identify architectural patterns, main components, and technology stack."
                },
                {
                    "role": "user",
                    "content": f"Analyze this project structure:\n{files[:100]}"  # First 100 files
                }
            ],
            temperature=0.3
        )

        analysis = response.choices[0].message.content

        logger.info(f"✅ {self.name}: Analysis complete")

        return {
            "file_structure": {
                "analysis": analysis,
                "total_files": len(files),
                "frameworks_detected": self._detect_frameworks(files)
            },
            "tokens_used": response.usage.total_tokens
        }

    def _detect_frameworks(self, files: List[str]) -> List[str]:
        """Detect frameworks from file patterns."""
        frameworks = []

        file_str = " ".join(files)

        if "package.json" in file_str:
            frameworks.append("Node.js")
        if "backend_requirements.txt" in file_str or "pyproject.toml" in file_str:
            frameworks.append("Python")
        if "main.py" in file_str and "app" in file_str:
            frameworks.append("FastAPI")
        if "App.tsx" in file_str or "App.jsx" in file_str:
            frameworks.append("React")

        return frameworks


class WebSearcherAgent:
    """Agent 2: Searches web for best practices."""

    def __init__(self):
        self.name = "Web Searcher"
        self.search_service = WebSearchService()

    async def execute(self, state: Dict) -> Dict:
        """Search for framework-specific best practices."""

        logger.info(f"🤖 {self.name}: Starting web search")

        frameworks = state.get("file_structure", {}).get("frameworks_detected", [])
        config = state.get("config", {})

        if not config.get("enable_web_search", False):
            logger.info(f"⏭️ {self.name}: Web search disabled, skipping")
            return {"web_search_results": {}, "searches_performed": 0}

        search_results = {}
        searches_performed = 0
        max_searches = config.get("max_web_searches", 5)

        for framework in frameworks[:max_searches]:
            logger.info(f"🔍 Searching best practices for {framework}")

            result = await self.search_service.search_framework_docs(
                framework,
                "best practices and common patterns"
            )

            search_results[framework] = result
            searches_performed += 1

        logger.info(f"✅ {self.name}: Completed {searches_performed} searches")

        return {
            "web_search_results": search_results,
            "searches_performed": searches_performed
        }


class CodeExtractorAgent:
    """Agent 3: Extracts API signatures and key code elements."""

    def __init__(self):
        self.name = "Code Extractor"
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    async def execute(self, state: Dict) -> Dict:
        """Extract API signatures and important code elements."""

        logger.info(f"🤖 {self.name}: Extracting API signatures")

        code_chunks = state.get("code_chunks", [])

        # Extract classes, functions, APIs
        api_signatures = []

        for chunk in code_chunks[:50]:  # Analyze first 50 chunks
            if chunk.get("chunk_type") in ["class", "function", "method"]:
                api_signatures.append({
                    "name": chunk.get("name"),
                    "type": chunk.get("chunk_type"),
                    "signature": chunk.get("signature"),
                    "file": chunk.get("file_path")
                })

        logger.info(f"✅ {self.name}: Extracted {len(api_signatures)} API signatures")

        return {
            "api_signatures": api_signatures
        }


class SecurityAuditorAgent:
    """Agent 4: Performs security analysis."""

    def __init__(self):
        self.name = "Security Auditor"
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.search_service = WebSearchService()

    async def execute(self, state: Dict) -> Dict:
        """Analyze code for security issues."""

        logger.info(f"🤖 {self.name}: Starting security audit")

        config = state.get("config", {})

        if not config.get("enable_security_analysis", False):
            logger.info(f"⏭️ {self.name}: Security analysis disabled, skipping")
            return {"security_findings": []}

        code_chunks = state.get("code_chunks", [])

        # Analyze for common security issues
        response = self.client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {
                    "role": "system",
                    "content": "You are a security expert. Analyze code for security vulnerabilities, OWASP Top 10 issues, and suggest fixes."
                },
                {
                    "role": "user",
                    "content": f"Analyze these code snippets for security issues:\n{code_chunks[:20]}"
                }
            ],
            temperature=0.2
        )

        # Search for OWASP guidelines if issues found
        security_guidelines = await self.search_service.search_security_guidelines(
            "web application",
            "authentication authorization"
        )

        logger.info(f"✅ {self.name}: Security audit complete")

        return {
            "security_findings": {
                "analysis": response.choices[0].message.content,
                "owasp_guidelines": security_guidelines
            },
            "tokens_used": response.usage.total_tokens
        }


class DocumentationGeneratorAgent:
    """Agent 5: Generates SDE-focused documentation."""

    def __init__(self):
        self.name = "Documentation Generator"
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    async def execute(self, state: Dict) -> Dict:
        """Generate technical documentation for developers."""

        logger.info(f"🤖 {self.name}: Generating SDE documentation")

        config = state.get("config", {})
        verbosity = config.get("verbosity", "medium")

        file_structure = state.get("file_structure", {})
        api_signatures = state.get("api_signatures", [])
        web_search = state.get("web_search_results", {})
        security_findings = state.get("security_findings", {})

        # Generate comprehensive technical docs
        prompt = f"""
Generate detailed technical documentation for software engineers.

Verbosity Level: {verbosity}

Project Structure:
{file_structure.get('analysis', '')}

API Signatures:
{api_signatures[:20]}

Best Practices Found:
{web_search}

Security Considerations:
{security_findings.get('analysis', '')}

Include:
1. Architecture overview
2. API documentation
3. Setup instructions
4. Code examples
5. Best practices
6. Security considerations
"""

        response = self.client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {
                    "role": "system",
                    "content": "You are a senior software engineer creating technical documentation. Be thorough, technical, and include code examples."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3
        )

        documentation = response.choices[0].message.content

        logger.info(f"✅ {self.name}: Documentation generated ({len(documentation)} chars)")

        return {
            "sde_documentation": documentation,
            "tokens_used": response.usage.total_tokens
        }


class PMSummarizerAgent:
    """Agent 6: Creates PM-focused business summaries."""

    def __init__(self):
        self.name = "PM Summarizer"
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    async def execute(self, state: Dict) -> Dict:
        """Generate business-focused summary for product managers."""

        logger.info(f"🤖 {self.name}: Generating PM summary")

        config = state.get("config", {})

        if "PM" not in config.get("personas", []):
            logger.info(f"⏭️ {self.name}: PM persona not enabled, skipping")
            return {"pm_summary": None}

        file_structure = state.get("file_structure", {})
        api_signatures = state.get("api_signatures", [])

        # Generate business-focused summary
        prompt = f"""
Create a high-level summary for product managers and business stakeholders.

Project Overview:
{file_structure.get('analysis', '')}

Key Features (from API analysis):
{api_signatures[:10]}

Focus on:
1. What the application does (business value)
2. Key features and capabilities
3. Technology choices and why they matter
4. Integration points
5. Scalability and maintenance considerations

Use non-technical language. Think "business value" not "technical implementation".
"""

        response = self.client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {
                    "role": "system",
                    "content": "You are a product manager translating technical details into business value. Avoid jargon, focus on capabilities and outcomes."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.4
        )

        summary = response.choices[0].message.content

        logger.info(f"✅ {self.name}: PM summary generated")

        return {
            "pm_summary": summary,
            "tokens_used": response.usage.total_tokens
        }
