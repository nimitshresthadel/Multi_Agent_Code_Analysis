import streamlit as st
import requests
import plotly.graph_objects as go
import plotly.express as px
from typing import Dict, List

from utils.api_client import APIClient

api_client = APIClient()


def main():
    st.title("🔍 Repository Intelligence")

    # Project selection
    projects_response = api_client.get_projects()

    # Extract the actual projects list from nested structure
    if not projects_response or not projects_response.get('success'):
        st.error("❌ Failed to fetch projects")
        return

    projects_data = projects_response.get('data', {})
    projects = projects_data.get('projects', [])

    if not projects:
        st.info("📭 No projects found. Please create a project first.")
        return

    # Filter ready projects
    ready_projects = [p for p in projects if p.get('status') == 'completed']

    # if not projects:
    #     st.info("📭 No projects found. Please create a project first.")
    #     return
    #
    # # Filter ready projects
    # print("projects", projects)
    # ready_projects = [p for p in projects if p.get('status') == 'ready']

    if not ready_projects:
        st.warning("⚠️ No analyzed projects yet. Please start analysis for a project.")
        return

    selected_project = st.selectbox(
        "Select Project",
        options=ready_projects,
        format_func=lambda x: x['name']
    )

    if not selected_project:
        return

    project_id = selected_project['id']

    # Fetch insights
    with st.spinner("Loading repository insights..."):
        insights = api_client.get_repository_insights(project_id)

    if not insights:
        st.error("❌ Failed to load insights")
        return

    # Display insights
    display_repository_insights(insights)


def display_repository_insights(insights: Dict):
    """Display comprehensive repository insights."""

    # Header with confidence badge
    col1, col2 = st.columns([3, 1])

    with col1:
        st.markdown(f"## {insights['framework']} Project")
        st.markdown(f"**Language:** {insights['primary_language']}")

    with col2:
        confidence = insights['confidence_score']
        if confidence >= 0.75:
            st.success(f"✅ Confidence: {confidence:.0%}")
        elif confidence >= 0.5:
            st.warning(f"⚠️ Confidence: {confidence:.0%}")
        else:
            st.error(f"❌ Confidence: {confidence:.0%}")

    st.markdown("---")

    # Overview metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Files", f"{insights['total_files']:,}")
    with col2:
        st.metric("Code Files", f"{insights['code_files']:,}")
    with col3:
        st.metric("Lines of Code", f"{insights['total_lines']:,}")
    with col4:
        st.metric("API Endpoints", insights['endpoints_count'])

    st.markdown("---")

    # Three column layout
    col1, col2, col3 = st.columns(3)

    with col1:
        display_entry_points(insights['entry_points'])
        display_tech_stack(insights['tech_stack'])

    with col2:
        display_important_files(insights['important_files'])

    with col3:
        display_database_info(insights)
        display_test_info(insights)

    # Dependencies section
    if insights['dependencies']:
        st.markdown("---")
        display_dependencies(insights['dependencies'])

    # API Endpoints
    if insights['endpoints']:
        st.markdown("---")
        display_api_endpoints(insights['endpoints'])


def display_entry_points(entry_points: List[str]):
    """Display entry points."""
    with st.expander("🚀 Entry Points", expanded=True):
        if entry_points:
            for ep in entry_points:
                st.code(ep, language="text")
        else:
            st.info("No entry points detected")


def display_tech_stack(tech_stack: List[str]):
    """Display technology stack."""
    with st.expander("🛠️ Technology Stack", expanded=True):
        if tech_stack:
            for tech in tech_stack:
                st.markdown(f"- {tech}")
        else:
            st.info("No technologies detected")


def display_important_files(important_files: List[Dict]):
    """Display important files ranked by priority."""
    with st.expander("📌 Important Files", expanded=True):
        if important_files:
            for file_info in important_files[:10]:  # Top 10
                priority = file_info['priority']
                file = file_info['file']
                reason = file_info['reason']

                # Color code by priority
                if priority >= 8:
                    st.markdown(f"🔴 **{file}** (Priority: {priority})")
                elif priority >= 6:
                    st.markdown(f"🟡 **{file}** (Priority: {priority})")
                else:
                    st.markdown(f"🟢 {file} (Priority: {priority})")

                st.caption(f"_{reason}_")
        else:
            st.info("No important files identified")


def display_database_info(insights: Dict):
    """Display database information."""
    with st.expander("🗄️ Database", expanded=True):
        if insights['database_type']:
            st.markdown(f"**Type:** {insights['database_type']}")
            if insights['orm_detected']:
                st.markdown(f"**ORM:** {insights['orm_detected']}")
        else:
            st.info("No database detected")


def display_test_info(insights: Dict):
    """Display testing information."""
    with st.expander("🧪 Testing", expanded=True):
        if insights['has_tests']:
            st.success("✅ Tests found")
            if insights['test_framework']:
                st.markdown(f"**Framework:** {insights['test_framework']}")
        else:
            st.warning("⚠️ No tests detected")


def display_dependencies(dependencies: Dict):
    """Display dependencies."""
    st.subheader("📦 Dependencies")

    if not dependencies:
        st.info("No dependencies found")
        return

    # Show count
    st.markdown(f"**Total:** {len(dependencies)} packages")

    # Display in columns
    cols = st.columns(3)
    deps_list = list(dependencies.items())

    for i, (name, version) in enumerate(deps_list[:30]):  # Show top 30
        col_idx = i % 3
        with cols[col_idx]:
            st.markdown(f"**{name}**")
            st.caption(f"v{version}")


def display_api_endpoints(endpoints: List[Dict]):
    """Display API endpoints."""
    st.subheader("🌐 API Endpoints")

    if not endpoints:
        st.info("No API endpoints detected")
        return

    # Group by method
    methods = {}
    for ep in endpoints:
        method = ep['method']
        if method not in methods:
            methods[method] = []
        methods[method].append(ep)

    # Create tabs for each method
    tabs = st.tabs(list(methods.keys()))

    for tab, (method, eps) in zip(tabs, methods.items()):
        with tab:
            for ep in eps:
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.code(ep['path'], language="text")
                with col2:
                    st.caption(ep['file'])


if __name__ == "__main__":
    main()
