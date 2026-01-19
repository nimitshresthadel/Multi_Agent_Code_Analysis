import streamlit as st
from utils.auth import require_auth, get_current_user
from utils.api_client import APIClient
import pandas as pd
import plotly.express as px
from datetime import datetime


st.set_page_config(
    page_title="Dashboard - Code Analysis",
    page_icon="📊",
    layout="wide"
)

# Require authentication
require_auth()

# Get current user
user = get_current_user()
client = APIClient()


def show_user_info():
    """Show user information card."""
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                padding: 2rem; border-radius: 10px; color: white; margin-bottom: 2rem;">
        <h2>👋 Welcome, {user['full_name']}!</h2>
        <p style="font-size: 1.1rem;">📧 {user['email']} • 👤 @{user['username']}</p>
        <p style="font-size: 0.9rem; opacity: 0.9;">Member since: {user['created_at'][:10]}</p>
    </div>
    """, unsafe_allow_html=True)


def show_project_stats():
    """Show project statistics."""
    st.markdown("### 📈 Project Statistics")

    # Get projects
    projects_result = client.get_projects(limit=100)

    if not projects_result["success"]:
        st.error("Failed to load projects")
        return

    projects = projects_result["data"]["projects"]

    if not projects:
        st.info("No projects yet. Upload your first project to get started!")
        return

    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="Total Projects",
            value=len(projects),
            delta="+1" if len(projects) > 0 else None
        )

    with col2:
        uploaded = len([p for p in projects if p["status"] == "uploaded"])
        st.metric(
            label="📤 Uploaded",
            value=uploaded
        )

    with col3:
        processing = len([p for p in projects if p["status"] == "processing"])
        st.metric(
            label="⚙️ Processing",
            value=processing
        )

    with col4:
        completed = len([p for p in projects if p["status"] == "completed"])
        st.metric(
            label="✅ Completed",
            value=completed
        )


def show_recent_projects():
    """Show recent projects table."""
    st.markdown("### 📁 Recent Projects")

    projects_result = client.get_projects(limit=10)

    if not projects_result["success"]:
        st.error("Failed to load projects")
        return

    projects = projects_result["data"]["projects"]

    if not projects:
        st.info("No projects yet")
        return

    # Create DataFrame
    df = pd.DataFrame(projects)

    # Format dates
    df['created_at'] = pd.to_datetime(df['created_at']).dt.strftime('%Y-%m-%d %H:%M')

    # Display table with styling
    st.dataframe(
        df[['name', 'status', 'source_type', 'created_at']],
        use_container_width=True,
        column_config={
            "name": "Project Name",
            "status": st.column_config.TextColumn(
                "Status",
                help="Current project status"
            ),
            "source_type": "Source Type",
            "created_at": "Created At"
        },
        hide_index=True
    )


def show_status_chart():
    """Show project status distribution chart."""
    projects_result = client.get_projects(limit=100)

    if not projects_result["success"] or not projects_result["data"]["projects"]:
        return

    projects = projects_result["data"]["projects"]

    # Count by status
    status_counts = {}
    for project in projects:
        status = project["status"]
        status_counts[status] = status_counts.get(status, 0) + 1

    # Create chart
    fig = px.pie(
        values=list(status_counts.values()),
        names=list(status_counts.keys()),
        title="Project Status Distribution",
        color_discrete_sequence=px.colors.qualitative.Set3
    )

    st.plotly_chart(fig, use_container_width=True)


def show_quick_actions():
    """Show quick action buttons."""
    st.markdown("### ⚡ Quick Actions")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("📤 Upload New Project", use_container_width=True):
            st.switch_page("pages/upload.py")

    with col2:
        if st.button("📁 View All Projects", use_container_width=True):
            st.switch_page("pages/projects.py")

    with col3:
        if st.button("⚙️ Settings", use_container_width=True):
            st.switch_page("pages/settings.py")


def main():
    """Main dashboard function."""
    st.title("📊 Dashboard")

    # User info
    show_user_info()

    # Stats
    show_project_stats()

    st.markdown("---")

    # Recent projects and chart
    col1, col2 = st.columns([2, 1])

    with col1:
        show_recent_projects()

    with col2:
        show_status_chart()

    st.markdown("---")

    # Quick actions
    show_quick_actions()


if __name__ == "__main__":
    main()
