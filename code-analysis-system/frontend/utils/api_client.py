"""API client for interacting with the backend."""
import json
import time
from sys import exception

import requests
from typing import Dict, List, Optional, Any
import streamlit as st
from datetime import datetime


class APIClient:
    """Client for backend API communication."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.api_prefix = "/api/v1"
        self.timeout = 30
        self.token = st.session_state.get('token')

    def _get_headers(self) -> Dict[str, str]:
        """Get headers with authentication token."""
        headers = {"Content-Type": "application/json"}

        if "access_token" in st.session_state:
            headers["Authorization"] = f"Bearer {st.session_state.access_token}"

        return headers

    def health_check(self) -> Dict:
        """Check API health."""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            st.error(f"API health check failed: {e}")
            return {"status": "unhealthy"}

    # Authentication
    def signup(self, email: str, username: str, password: str, full_name: str) -> Dict:
        """Sign up a new user."""
        try:
            response = requests.post(
                f"{self.base_url}/api/v1/auth/signup",
                json={
                    "email": email,
                    "username": username,
                    "password": password,
                    "full_name": full_name,
                    "role": "user"
                },
                timeout=self.timeout
            )
            response.raise_for_status()
            return {"success": True, "data": response.json()}
        except requests.exceptions.HTTPError as e:
            error_detail = e.response.json().get("detail", str(e))
            return {"success": False, "error": error_detail}
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": str(e)}

    def login(self, email: str, password: str) -> Dict:
        """Log in a user."""
        try:
            response = requests.post(
                f"{self.base_url}/api/v1/auth/login",
                json={"email": email, "password": password},
                timeout=self.timeout
            )
            response.raise_for_status()
            return {"success": True, "data": response.json()}
        except requests.exceptions.HTTPError as e:
            error_detail = e.response.json().get("detail", "Invalid credentials")
            return {"success": False, "error": error_detail}
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": str(e)}

    # User
    def get_current_user(self) -> Optional[Dict]:
        """Get current user profile."""
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/users/me",
                headers=self._get_headers(),
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException:
            return None

    def update_profile(self, full_name: Optional[str] = None) -> Dict:
        """Update user profile."""
        try:
            data = {}
            if full_name:
                data["full_name"] = full_name

            response = requests.put(
                f"{self.base_url}/api/v1/users/me",
                headers=self._get_headers(),
                json=data,
                timeout=self.timeout
            )
            response.raise_for_status()
            return {"success": True, "data": response.json()}
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": str(e)}

    # Projects
    def get_projects(self, skip: int = 0, limit: int = 20, status: Optional[str] = None) -> Dict:
        """Get user's projects."""
        try:
            params = {"skip": skip, "limit": limit}
            if status:
                print("status", status)
                params["status"] = status

            response = requests.get(
                f"{self.base_url}/api/v1/projects/",
                headers=self._get_headers(),
                params=params,
                timeout=self.timeout
            )
            response.raise_for_status()
            return {"success": True, "data": response.json()}
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": str(e)}

    def get_project(self, project_id: str) -> Dict:
        """Get project details."""
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/projects/{project_id}",
                headers=self._get_headers(),
                timeout=self.timeout
            )
            print("Response_project", response.json())
            response.raise_for_status()
            return {"success": True, "data": response.json()}
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": str(e)}

    def upload_project(self, name: str, file, description: str = "", personas: List[str] = None) -> Dict:
        """Upload a project ZIP file."""
        try:
            files = {"file": file}
            print("file", files)
            personas_json = json.dumps(personas)
            data = {
                "name": name,
                "description": description,
                "personas": personas_json
            }

            # Don't include Content-Type in headers for multipart/form-data
            headers = {}
            if "access_token" in st.session_state:
                headers["Authorization"] = f"Bearer {st.session_state.access_token}"

            print("headers", headers)
            print("data", data)

            response = requests.post(
                f"{self.base_url}/api/v1/projects/upload",
                headers=headers,
                files=files,
                data=data,
                timeout=60  # Longer timeout for uploads
            )
            print("response", response)
            response.raise_for_status()
            return {"success": True, "data": response.json()}
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": str(e)}

    def delete_project(self, project_id: str) -> Dict:
        """Delete a project."""
        try:
            response = requests.delete(
                f"{self.base_url}/api/v1/projects/{project_id}",
                headers=self._get_headers(),
                timeout=self.timeout
            )
            response.raise_for_status()
            return {"success": True}
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": str(e)}


    def create_project_from_zip(self, name: str, description: str,
                                personas: List[str], file) -> Optional[Dict]:
        """Create a project by uploading a ZIP file."""
        try:
            url = f"{self.base_url}{self.api_prefix}/projects/upload"

            # Prepare multipart form data
            files = {
                'file': (file.name, file.getvalue(), 'application/zip')
            }

            data = {
                'name': name,
                'description': description,
                'personas': json.dumps(personas)
            }

            response = requests.post(
                url,
                headers=self._get_headers(),
                data=data,
                files=files,
                timeout=300  # 5 minutes timeout for large files
            )

            if response.status_code == 201:
                return response.json()
            else:
                st.error(f"Server error: {response.status_code} - {response.text}")
                return None

        except requests.exceptions.Timeout:
            st.error("Upload timed out. Please try with a smaller file.")
            return None
        except Exception as e:
            st.error(f"Error uploading file: {str(e)}")
            return None

    def create_project_from_github(self, name: str, description: str,
                                   personas: List[str], github_url: str) -> Optional[Dict]:
        """Create a project from a GitHub repository."""
        try:
            url = f"{self.base_url}{self.api_prefix}/projects/github"

            payload = {
                'name': name,
                'description': description,
                'personas': personas,
                'source_url': github_url
            }

            print("payload", payload)

            response = requests.post(
                url,
                headers={**self._get_headers(), 'Content-Type': 'application/json'},
                json=payload,
                timeout=300  # 5 minutes timeout for cloning
            )
            # print(f"response1", response)
            # print(f"response2", response.status_code)
            # print(f"response3", response.text)
            # print(f"response4", response.json())

            if response.status_code == 201:
                return response.json()
            else:
                error_detail = response.json().get('detail', response.text)
                st.error(f"GitHub clone failed: {error_detail}")
                return None

        except requests.exceptions.Timeout:
            st.error("GitHub clone timed out. The repository might be too large.")
            return None
        except Exception as e:
            st.error(f"Error cloning from GitHub: {str(e)}")
            return None

    def start_analysis(self, project_id: str) -> Optional[Dict]:
        """Start preprocessing and analysis for a project."""
        try:
            url = f"{self.base_url}{self.api_prefix}/analysis/start"
            #with st.spinner(f"Starting Project analysis..."):
            response = requests.post(
                url,
                headers={**self._get_headers(), 'Content-Type': 'application/json'},
                json={"project_id": project_id},
                timeout=30
            )
            response.raise_for_status()

            st.session_state['current_project_id'] = project_id
            if 'celebration_shown' in st.session_state:
                del st.session_state['celebration_shown']

            # Enable auto-refresh
            st.session_state['should_auto_refresh'] = True
            st.success(f"✅ Analysis started")
            time.sleep(0.5)  # Brief pause for user feedback
            #st.switch_page("pages/analysis_progress.py")


        except Exception as e:
            st.error(f"Error starting analysis: {str(e)}")
            return None

    def get_analysis_status(self, project_id: str) -> Optional[Dict]:
        """Get analysis status for a project."""
        try:
            url = f"{self.base_url}{self.api_prefix}/analysis/status/{project_id}"
            response = requests.get(url, headers=self._get_headers())

            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            st.error(f"Error getting status: {str(e)}")
            return None

    def get_repository_insights(self, project_id: str) -> Optional[Dict]:
        """Get repository intelligence insights."""
        try:
            url = f"{self.base_url}{self.api_prefix}/analysis/insights/{project_id}"
            response = requests.get(url, headers=self._get_headers())

            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            st.error(f"Error getting insights: {str(e)}")
            return None

    def semantic_search(self, project_id: str, query: str, top_k: int = 10) -> List[Dict]:
        """Perform semantic search on code."""
        try:
            url = f"{self.base_url}{self.api_prefix}/search/semantic"
            response = requests.post(
                url,
                headers={**self._get_headers(), 'Content-Type': 'application/json'},
                json={
                    "query": query,
                    "project_id": project_id,
                    "top_k": top_k
                },
                timeout=30
            )

            print(f"response1", response)
            print(f"response2", response.status_code)
            print(f"response3", response.text)
            print(f"response4", response.json())

            if response.status_code == 200:
                data = response.json()
                return data.get('results', [])
            return []
        except Exception as e:
            st.error(f"Search error: {str(e)}")
            return []

    def find_similar_chunks(self, chunk_id: str, project_id: str, top_k: int = 5) -> List[Dict]:
        """Find similar code chunks."""
        try:
            url = f"{self.base_url}{self.api_prefix}/search/similar/{chunk_id}"
            response = requests.get(
                url,
                headers=self._get_headers(),
                params={"project_id": project_id, "top_k": top_k}
            )

            if response.status_code == 200:
                data = response.json()
                return data.get('similar_chunks', [])
            return []
        except Exception as e:
            st.error(f"Error finding similar chunks: {str(e)}")
            return []

    def get_progress(self, project_id: str) -> Dict[str, Any]:
        """Always returns a dict usable by the UI."""
        fallback = {"status": "error", "overall_percentage": 0, "stage_label": "Error loading progress"}
        try:
            url = f"{self.base_url}{self.api_prefix}/progress/{project_id}"
            response = requests.get(
                url,
                headers=self._get_headers(),
                timeout=self.timeout
            )
            if response.status_code == 200:
                data = response.json()
                return data
            return []
        except Exception as e:
            st.error(f"Error loading progress: {str(e)}")
            return fallback

    def get_activities(self, project_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        try:
            url = f"{self.base_url}{self.api_prefix}/progress/{project_id}/activities"
            response = requests.get(
                url,
                params={"limit": limit},
                headers=self._get_headers(),
                timeout=self.timeout,
            )
            print(f"response1", response)
            print(f"response2", response.status_code)
            print(f"response3", response.text)
            print(f"response4", response.json())
            if response.status_code == 200:
                r = response.json()
                return (r.get("data") or {}).get("activities") or []
            return []
        except Exception as e:
            st.error(f"Error loading activities: {str(e)}")
            return []

    def restart_analysis(self, project_id: str) -> bool:
        try:
            url = f"{self.base_url}{self.api_prefix}/analysis/start"
            response = requests.post(
                url,
                json={"project_id": project_id},
                headers=self._get_headers(),
                timeout=self.timeout,
            )
            if response.status_code == 200:
                return True
            return False
        except Exception as e:
            st.error(f"Failed to restart: {str(e)}")
            return False

    def get_agents(self, project_id: str, limit: int = 20) -> Dict:
        """Fetch agent status."""
        try:
            url = f"{self.base_url}{self.api_prefix}/agent_analysis/{project_id}/agents"
            response = requests.get(
                url,
                headers=self._get_headers()
            )

            print(f"responseP", response)
            print(f"responseQ", response.status_code)
            print(f"responseR", response.text)
            print(f"responseS", response.json())
            response.raise_for_status()
            return response.json()['data']['agents']
        except Exception as e:
            st.error(f"Failed to restart: {str(e)}")
            return []