import streamlit as st
import time
from datetime import datetime

from utils.auth import require_auth
from utils.api_client import APIClient

# Page config
st.set_page_config(
    page_title="Analysis Progress - DocuGenius",
    page_icon="⏳",
    layout="wide"
)

# Authentication
require_auth()

# Get project ID from query params or session
if 'project_id' in st.query_params:
    project_id = st.query_params['project_id']
    st.session_state['current_project_id'] = project_id
elif 'current_project_id' in st.session_state:
    project_id = st.session_state['current_project_id']
else:
    st.warning("⚠️ No project selected")
    st.info("👈 Please use the sidebar to navigate to **Projects** page")
    st.stop()

client = APIClient()


# ==================== Header ====================

st.title("⏳ Analysis Progress")

# View toggle
view_mode = st.radio(
    "View Mode",
    options=["📊 Overview", "🤖 Agent Details", "📜 Activity Log"],
    horizontal=True
)

st.divider()

# ==================== Fetch Data ====================

progress_data = client.get_progress(project_id)
agents_data = client.get_agents(project_id)

if not progress_data:
    st.error("Unable to load progress data")
    st.stop()

# ==================== Overview Mode ====================

if view_mode == "📊 Overview":

    # Overall status
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        status = progress_data.get('status', 'unknown')
        status_emoji = {
            'not_started': '⏸️',
            'in_progress': '🔄',
            'completed': '✅',
            'failed': '❌'
        }
        st.metric("Status", f"{status_emoji.get(status, '•')} {status.title()}")

    with col2:
        percentage = progress_data.get('overall_percentage', 0)
        st.metric("Progress", f"{percentage}%")

    with col3:
        stage = progress_data.get('stage_label', 'Unknown')
        st.metric("Current Stage", stage)

    with col4:
        if progress_data.get('total_files'):
            processed = progress_data.get('processed_files', 0)
            total = progress_data.get('total_files', 0)
            st.metric("Files", f"{processed}/{total}")

    # Progress bar
    st.progress(percentage / 100)

    st.divider()

    # Stage breakdown
    st.subheader("🎯 Analysis Stages")

    stages = [
        {"name": "📁 File Analysis", "status": "completed", "progress": 100},
        {"name": "🔍 Code Extraction", "status": "completed", "progress": 100},
        {"name": "🌐 Web Research", "status": "running", "progress": 60},
        {"name": "🔒 Security Audit", "status": "pending", "progress": 0},
        {"name": "📝 Documentation", "status": "pending", "progress": 0},
        {"name": "📊 PM Summary", "status": "pending", "progress": 0},
    ]

    # Map agents to stages
    agent_stage_map = {
        "file_analyzer": 0,
        "code_extractor": 1,
        "web_searcher": 2,
        "security_auditor": 3,
        "doc_generator": 4,
        "pm_summarizer": 5
    }

    # Update stages from actual agent data
    if agents_data:
        for agent in agents_data:
            stage_idx = agent_stage_map.get(agent['name'])
            if stage_idx is not None:
                if agent['status'] == 'completed':
                    stages[stage_idx]['status'] = 'completed'
                    stages[stage_idx]['progress'] = 100
                elif agent['status'] == 'running':
                    stages[stage_idx]['status'] = 'running'
                    stages[stage_idx]['progress'] = 50
                elif agent['status'] == 'failed':
                    stages[stage_idx]['status'] = 'failed'
                    stages[stage_idx]['progress'] = 0

    for stage in stages:
        with st.container():
            col1, col2 = st.columns([3, 1])

            with col1:
                st.markdown(f"**{stage['name']}**")
                st.progress(stage['progress'] / 100)

            with col2:
                status_icons = {
                    'completed': '✅',
                    'running': '🔄',
                    'pending': '⏳',
                    'failed': '❌'
                }
                st.markdown(
                    f"<div style='text-align: right; padding-top: 10px;'>"
                    f"{status_icons.get(stage['status'], '•')} {stage['status'].title()}"
                    f"</div>",
                    unsafe_allow_html=True
                )

            st.divider()

    # Quick agent summary
    if agents_data:
        st.subheader("🤖 Agent Summary")

        col1, col2, col3 = st.columns(3)

        with col1:
            completed = len([a for a in agents_data if a['status'] == 'completed'])
            st.metric("Completed", f"{completed}/{len(agents_data)}")

        with col2:
            running = len([a for a in agents_data if a['status'] == 'running'])
            st.metric("Running", running)

        with col3:
            failed = len([a for a in agents_data if a['status'] == 'failed'])
            st.metric("Failed", failed)

# ==================== Agent Details Mode ====================

elif view_mode == "🤖 Agent Details":

    if not agents_data:
        st.info("No agent data available yet")
    else:
        # Show detailed agent cards
        for agent in agents_data:
            with st.expander(
                    f"{agent['name'].replace('_', ' ').title()} - {agent['status'].upper()}",
                    expanded=(agent['status'] == 'running')
            ):
                col1, col2 = st.columns(2)

                with col1:
                    st.markdown("**Agent Type:**")
                    st.text(agent['type'])

                    st.markdown("**Status:**")
                    st.text(agent['status'])

                    if agent.get('started_at'):
                        st.markdown("**Started:**")
                        st.text(agent['started_at'])

                with col2:
                    if agent.get('completed_at'):
                        st.markdown("**Completed:**")
                        st.text(agent['completed_at'])

                        # Calculate duration
                        started = datetime.fromisoformat(agent['started_at'].replace('Z', '+00:00'))
                        completed = datetime.fromisoformat(agent['completed_at'].replace('Z', '+00:00'))
                        duration = (completed - started).total_seconds()

                        st.markdown("**Duration:**")
                        st.text(f"{duration:.1f} seconds")

                    if agent.get('tokens_used', 0) > 0:
                        st.markdown("**Tokens Used:**")
                        st.text(f"{agent['tokens_used']:,}")

                    if agent.get('web_searches', 0) > 0:
                        st.markdown("**Web Searches:**")
                        st.text(agent['web_searches'])

                # Show error if any
                if agent.get('error'):
                    st.error(f"❌ Error: {agent['error']}")

                # Show output if available (you'd need to add this to your API)
                if agent.get('output_data'):
                    st.markdown("**Output:**")
                    st.json(agent['output_data'])

# ==================== Activity Log Mode ====================

elif view_mode == "📜 Activity Log":

    # Fetch activities
    try:
        activities = client.get_activities(project_id, limit=50)
    except Exception as e:
        st.error(f"Error loading activities: {str(e)}")
        activities = []

    if not activities:
        st.info("No activities recorded yet")
    else:
        # Filter options
        col1, col2 = st.columns([1, 3])

        with col1:
            filter_type = st.selectbox(
                "Filter by type",
                options=["All", "info", "progress", "success", "error", "warning"]
            )

        # Display activities
        filtered_activities = activities
        if filter_type != "All":
            filtered_activities = [a for a in activities if a.get('type') == filter_type]

        st.caption(f"Showing {len(filtered_activities)} activities")

        for activity in filtered_activities:
            with st.container():
                cols = st.columns([1, 5, 1])

                with cols[0]:
                    try:
                        dt = datetime.fromisoformat(activity['timestamp'].replace('Z', '+00:00'))
                        st.caption(dt.strftime("%H:%M:%S"))
                    except:
                        st.caption(activity.get('timestamp', ''))

                with cols[1]:
                    activity_type = activity.get('type', 'info')
                    icons = {
                        'info': 'ℹ️',
                        'progress': '⏳',
                        'success': '✅',
                        'error': '❌',
                        'warning': '⚠️'
                    }
                    icon = icons.get(activity_type, '•')

                    st.markdown(f"{icon} {activity.get('message', '')}")

                    if activity.get('file_name'):
                        st.caption(f"📄 {activity['file_name']}")

                with cols[2]:
                    if activity.get('details'):
                        with st.popover("Details"):
                            st.json(activity['details'])

                st.divider()

# ==================== Action Buttons ====================

st.divider()

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("🔄 Refresh", use_container_width=True):
        st.rerun()

with col2:
    if st.button("🤖 View Agents", use_container_width=True):
        st.switch_page("pages/agent_monitor.py")

with col3:
    if st.button("⚙️ Configure", use_container_width=True):
        st.switch_page("pages/configure_analysis.py")

# ==================== Auto-refresh ====================

if progress_data.get('status') == 'in_progress':
    time.sleep(3)
    st.rerun()
