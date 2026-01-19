import os
import logging
from typing import List, Dict, Optional
from openai import OpenAI
import requests

logger = logging.getLogger(__name__)


class WebSearchService:
    """Service for web-augmented analysis."""

    def __init__(self):
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.tavily_api_key = os.getenv("TAVILY_API_KEY")  # Optional: Better search

    async def search_framework_docs(self, framework: str, query: str) -> Dict:
        """Search for framework-specific documentation."""

        logger.info(f"🔍 Searching {framework} documentation for: {query}")

        try:
            # Use OpenAI with web browsing capability (if available)
            # Or use Tavily API for better results
            if self.tavily_api_key:
                results = await self._tavily_search(f"{framework} {query}")
            else:
                results = await self._openai_search(f"{framework} {query}")

            logger.info(f"✅ Found {len(results.get('results', []))} results")
            return results

        except Exception as e:
            logger.error(f"Search error: {str(e)}")
            return {"results": [], "error": str(e)}

    async def _tavily_search(self, query: str) -> Dict:
        """Search using Tavily API (better for development docs)."""

        url = "https://api.tavily.com/search"
        payload = {
            "api_key": self.tavily_api_key,
            "query": query,
            "search_depth": "advanced",
            "include_answer": True,
            "max_results": 3
        }

        response = requests.post(url, json=payload)
        response.raise_for_status()

        return response.json()

    async def _openai_search(self, query: str) -> Dict:
        """Fallback: Use OpenAI to generate search insights."""

        # This doesn't actually search the web, but provides knowledge-based answers
        response = self.openai_client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {
                    "role": "system",
                    "content": "You are a technical documentation expert. Provide accurate, up-to-date information about frameworks and best practices."
                },
                {
                    "role": "user",
                    "content": f"Provide detailed information about: {query}"
                }
            ],
            temperature=0.3
        )

        return {
            "results": [{
                "content": response.choices[0].message.content,
                "source": "OpenAI Knowledge Base"
            }],
            "tokens_used": response.usage.total_tokens
        }

    async def search_security_guidelines(self, technology: str, issue: str) -> Dict:
        """Search for security best practices."""

        logger.info(f"🔒 Searching security guidelines for {technology}: {issue}")

        query = f"OWASP {technology} {issue} security best practices"
        return await self.search_framework_docs("security", query)

    async def search_migration_notes(self, library: str, from_version: str, to_version: str) -> Dict:
        """Search for version migration information."""

        logger.info(f"📦 Searching migration notes: {library} {from_version} → {to_version}")

        query = f"{library} migration {from_version} to {to_version}"
        return await self.search_framework_docs(library, query)
