"""Authentication utilities for Streamlit."""
import streamlit as st
from typing import Optional, Dict
from .api_client import APIClient


def init_session_state():
    """Initialize session state variables."""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "user" not in st.session_state:
        st.session_state.user = None
    if "access_token" not in st.session_state:
        st.session_state.access_token = None


def login_user(email: str, password: str) -> bool:
    """Log in a user."""
    client = APIClient()
    result = client.login(email, password)

    if result["success"]:
        st.session_state.access_token = result["data"]["access_token"]

        # Get user profile
        user = client.get_current_user()
        if user:
            st.session_state.user = user
            st.session_state.authenticated = True
            return True

    return False


def logout_user():
    """Log out the current user."""
    st.session_state.authenticated = False
    st.session_state.user = None
    st.session_state.access_token = None


def require_auth():
    """Require authentication for a page."""
    init_session_state()

    if not st.session_state.authenticated:
        st.warning("⚠️ Please log in to access this page")
        st.stop()


def get_current_user() -> Optional[dict]:
    """Get the current logged-in user."""
    return st.session_state.get("user")


def get_auth_headers() -> Dict[str, str]:
    """
    Get authorization headers for API requests.
    Returns empty dict if not authenticated.

    Usage:
        headers = get_auth_headers()
        response = requests.get(url, headers=headers)
    """
    if 'token' not in st.session_state:
        return {}
    return {"Authorization": f"Bearer {st.session_state['token']}"}
