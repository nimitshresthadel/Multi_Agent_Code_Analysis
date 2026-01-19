"""Projects management page."""

import streamlit as st
from utils.auth import require_auth, get_current_user
from utils.api_client import APIClient
import json
import pandas as pd
import time

st.set_page_config(
    page_title="Projects - Code Analysis",
    page_icon="📁",
    layout="wide"
)

# Require authentication
require_auth()

user = get_current_user()
client = APIClient()


def get_status_badge(status: str) -> str:
    """Get status badge with icon and color."""
    badges = {
        "uploaded": "🟢 Uploaded",
        "processing": "🟡 Processing",
        "ready": "✅ Ready",
        "completed": "✅ Completed",
        "failed": "🔴 Failed"
    }
    return badges.get(status, f"⚪ {status}")


def format_file_size(bytes_size):
    """Format bytes to human-readable size."""
    if not bytes_size:
        return "0 B"

    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f} TB"


def show_projects_list():
    """Show list of all projects."""
    st.markdown("### 📁 All Projects")

    # Filters
    col1, col2, col3 = st.columns([2, 2, 1])

    with col1:
        status_filter = st.selectbox(
            "Filter by Status",
            ["All", "uploaded", "processing", "ready", "completed", "failed"]
        )

    with col2:
        sort_by = st.selectbox(
            "Sort by",
            ["Newest First", "Oldest First", "Name A-Z", "Name Z-A"]
        )

    with col3:
        limit = st.number_input("Projects per page", min_value=10, max_value=100, value=20, step=10)

    # Get projects
    status = None if status_filter == "All" else status_filter
    projects_result = client.get_projects(limit=limit, status=status)

    if not projects_result["success"]:
        st.error("Failed to load projects")
        return

    projects = projects_result["data"]["projects"]

    if not projects:
        st.info("📭 No projects found. Upload your first project to get started!")
        if st.button("📤 Upload Project"):
            st.switch_page("pages/upload.py")
        return

    # Sort projects
    if sort_by == "Newest First":
        projects.sort(key=lambda x: x["created_at"], reverse=True)
    elif sort_by == "Oldest First":
        projects.sort(key=lambda x: x["created_at"])
    elif sort_by == "Name A-Z":
        projects.sort(key=lambda x: x["name"])
    elif sort_by == "Name Z-A":
        projects.sort(key=lambda x: x["name"], reverse=True)

    # Summary statistics
    col1, col2, col3, col4 = st.columns(4)

    status_counts = {}
    for p in projects:
        status = p.get('status', 'unknown')
        status_counts[status] = status_counts.get(status, 0) + 1

    with col1:
        st.metric("Total Projects", len(projects))
    with col2:
        st.metric("Ready", status_counts.get('ready', 0) + status_counts.get('completed', 0))
    with col3:
        st.metric("Processing", status_counts.get('processing', 0))
    with col4:
        st.metric("Uploaded", status_counts.get('uploaded', 0))

    st.divider()

    # Display projects as cards
    for project in projects:
        with st.container():
            # Project header
            col1, col2 = st.columns([4, 1])

            with col1:
                status_badge = get_status_badge(project["status"])

                st.markdown(f"""
                **{project['name']}** {status_badge}
                
                📝 {project.get('description', 'No description')}
                
                📅 Created: {project['created_at'][:10]} • 📦 Source: {project['source_type']} • 💾 Size: {format_file_size(project.get('file_size', 0))}
                """)

            with col2:
                if st.button("👁️ View", key=f"view_{project['id']}", use_container_width=True):
                    st.session_state.selected_project = project['id']
                    st.rerun()

            # Progress bar for processing projects
            if project['status'] == 'processing':
                progress = project.get('progress_percentage', 0)
                st.progress(progress / 100, text=f"Analysis in progress: {progress}%")

            # Error message for failed projects
            if project['status'] == 'failed' and project.get('error_message'):
                st.error(f"❌ Analysis failed: {project['error_message']}")

            # Action buttons
            btn_col1, btn_col2, btn_col3, btn_col4 = st.columns([1, 1, 1, 2])

            with btn_col1:
                # Start Analysis Button
                if project['status'] == 'uploaded':
                    if st.button("🔍 Analyze", key=f"analyze_{project['id']}", type="primary"):
                        #with st.spinner("🔄 Starting analysis..."):
                        result = client.start_analysis(project['id'])

                        if result and result.get('status') == 'processing':
                            st.success("✅ Analysis started!")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("❌ Failed to start analysis")

                elif project['status'] == 'processing':
                    if st.button("🔄 Refresh", key=f"refresh_{project['id']}"):
                        status_result = client.get_analysis_status(project['id'])
                        if status_result:
                            st.info(f"Status: {status_result.get('status', 'Unknown')}")
                        st.rerun()

                elif project['status'] in ['ready', 'completed']:
                    st.success("✅ Ready")

                elif project['status'] == 'failed':
                    if st.button("🔁 Retry", key=f"retry_{project['id']}"):
                        with st.spinner("Retrying analysis..."):
                            result = client.start_analysis(project['id'])
                            if result:
                                st.success("✅ Analysis restarted!")
                                st.rerun()

            with btn_col2:
                # View Insights Button (for ready/completed projects)
                if project['status'] in ['ready', 'completed']:
                    if st.button("📊 Insights", key=f"insights_{project['id']}", type="secondary"):
                        st.session_state['selected_project_id'] = project['id']
                        st.session_state['selected_project_name'] = project['name']
                        st.switch_page("pages/code_insights.py")

            with btn_col3:
                # Semantic Search Button (for ready/completed projects)
                if project['status'] in ['ready', 'completed']:
                    if st.button("🔍 Search", key=f"search_{project['id']}", type="secondary"):
                        st.session_state['search_project_id'] = project['id']
                        st.session_state['search_project_name'] = project['name']
                        st.switch_page("pages/semantic_search.py")

            with btn_col4:
                # Delete button
                delete_key = f"delete_{project['id']}"
                confirm_key = f"confirm_delete_{project['id']}"

                if st.session_state.get(confirm_key, False):
                    col_a, col_b = st.columns(2)
                    with col_a:
                        if st.button("⚠️ Confirm", key=f"{delete_key}_confirm", type="secondary"):
                            result = client.delete_project(project['id'])
                            if result["success"]:
                                st.success("✅ Project deleted!")
                                st.session_state.pop(confirm_key, None)
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error(f"❌ Failed to delete: {result.get('error', 'Unknown error')}")
                                st.session_state.pop(confirm_key, None)
                    with col_b:
                        if st.button("❌ Cancel", key=f"{delete_key}_cancel"):
                            st.session_state.pop(confirm_key, None)
                            st.rerun()
                else:
                    if st.button("🗑️ Delete", key=delete_key):
                        st.session_state[confirm_key] = True
                        st.rerun()

            st.markdown("---")


def show_project_details(project_id: str):
    """Show detailed view of a project."""
    result = client.get_project(project_id)

    if not result["success"]:
        st.error("Failed to load project details")
        return

    project = result["data"]

    st.markdown(f"## 📁 {project['name']}")

    # Status badge
    status_badge = get_status_badge(project["status"])
    st.markdown(f"### {status_badge}")

    # Info grid
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(f"""
        **Status:** {project['status']}
        
        **Source:** {project['source_type']}
        
        **Size:** {format_file_size(project.get('file_size', 0))}
        """)

    with col2:
        st.markdown(f"""
        **Created:** {project['created_at'][:10]}
        
        **Owner:** {project['owner_id']}
        """)

        if project.get('completed_at'):
            st.markdown(f"**Completed:** {project['completed_at'][:10]}")

    with col3:
        if project.get('source_url'):
            st.markdown(f"**URL:** [{project['source_url']}]({project['source_url']})")

        if project.get('personas'):
            st.markdown("**Personas:**")
            for persona in project['personas']:
                st.write(f"• {persona}")

    # Description
    if project.get('description'):
        st.markdown("### 📝 Description")
        st.info(project['description'])

    # Progress for processing
    if project['status'] == 'processing':
        st.markdown("### ⏳ Analysis Progress")
        progress = project.get('progress_percentage', 0)
        st.progress(progress / 100, text=f"{progress}% complete")

    # Error message
    if project['status'] == 'failed' and project.get('error_message'):
        st.markdown("### ❌ Error")
        st.error(project['error_message'])

    # Repository metadata (if available and project is ready)
    if project['status'] in ['ready', 'completed']:
        st.markdown("### 📊 Analysis Summary")

        # Try to get repository insights
        insights = client.get_repository_insights(project_id)

        if insights:
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric("Repository Type", insights.get('repository_type', 'N/A'))

            with col2:
                st.metric("Primary Language", insights.get('primary_language', 'N/A'))

            with col3:
                st.metric("Total Files", insights.get('total_files', 0))

            with col4:
                st.metric("Lines of Code", f"{insights.get('total_lines', 0):,}")

            st.divider()

            # Tech stack
            tech_stack = insights.get('tech_stack', [])
            if tech_stack:
                st.markdown("**🛠️ Tech Stack:**")
                st.write(", ".join(tech_stack))

    st.divider()

    # Action buttons
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("← Back to Projects", type="primary"):
            del st.session_state.selected_project
            st.rerun()

    with col2:
        # Analysis actions
        if project['status'] == 'uploaded':
            if st.button("🔍 Start Analysis"):
                with st.spinner("Starting analysis..."):
                    result = client.start_analysis(project_id)
                    if result and result.get('status') == 'processing':
                        st.success("✅ Analysis started!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        print("ok")

        elif project['status'] == 'processing':
            if st.button("🔄 Refresh Status"):
                st.rerun()

        elif project['status'] == 'failed':
            if st.button("🔁 Retry Analysis"):
                with st.spinner("Retrying..."):
                    result = client.start_analysis(project_id)
                    if result:
                        st.success("✅ Analysis restarted!")
                        st.rerun()

    with col3:
        # View insights
        if project['status'] in ['ready', 'completed']:
            if st.button("📊 View Insights"):
                st.session_state['selected_project_id'] = project_id
                st.session_state['selected_project_name'] = project['name']
                st.switch_page("pages/code_insights.py")

    with col4:
        # Delete
        if st.button("🗑️ Delete Project"):
            if st.session_state.get(f"confirm_delete_detail_{project_id}", False):
                result = client.delete_project(project_id)
                if result["success"]:
                    st.success("✅ Project deleted!")
                    del st.session_state.selected_project
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(f"❌ Failed to delete: {result.get('error', 'Unknown error')}")
            else:
                st.session_state[f"confirm_delete_detail_{project_id}"] = True
                st.warning("⚠️ Click again to confirm deletion")


def main():
    """Main projects function."""
    st.title("📁 My Projects")

    # Check if viewing specific project
    if "selected_project" in st.session_state:
        show_project_details(st.session_state.selected_project)
    else:
        show_projects_list()


if __name__ == "__main__":
    main()
