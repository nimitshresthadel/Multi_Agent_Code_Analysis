import streamlit as st
import logging
import time
from streamlit_autorefresh import st_autorefresh
from utils.progress import ProgressDisplay
from utils.auth import require_auth
from utils.api_client import APIClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)

# Page config
st.set_page_config(
    page_title="Analysis Progress - DocuGenius",
    page_icon="📊",
    layout="wide"
)

# Inject custom CSS
ProgressDisplay.inject_custom_css()

# ==================== AUTH & PROJECT CHECK ====================

client = APIClient()

require_auth()


# Get project ID - NO st.switch_page()
if 'current_project_id' not in st.session_state:
    st.warning("⚠️ No project selected")
    st.info("👈 Please use the sidebar to navigate to **Projects** page")
    st.stop()

project_id = st.session_state['current_project_id']


# ==================== Auto-refresh Logic ====================

# Initialize refresh state
if 'should_auto_refresh' not in st.session_state:
    st.session_state['should_auto_refresh'] = True

# Fetch current progress first
progress = client.get_progress(project_id)
status = progress.get('status', 'in_progress')

# Stop auto-refresh when complete or failed
if status in ['completed', 'failed']:
    st.session_state['should_auto_refresh'] = False

# Auto-refresh every 2 seconds if in progress
if st.session_state['should_auto_refresh']:
    count = st_autorefresh(interval=2000, limit=None, key="progress_refresh")

# ==================== Header ====================

project_info = client.get_project(project_id)

col1, col2 = st.columns([5, 1])

with col1:
    st.title(project_info['data']['name'] if project_info else "Analysis Progress")
    if project_info and project_info.get('description'):
        st.caption(project_info['description'])

with col2:
    # Show refresh indicator
    if st.session_state['should_auto_refresh']:
        st.caption("🔄 Live")
        st.caption("updates...")
    else:
        if st.button("🔄 Refresh", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

st.divider()

# ==================== Main Content ====================

# Fetch data
activities = client.get_activities(project_id, limit=100)

# Two-column layout
col_left, col_right = st.columns([2, 3])

with col_left:
    # Progress section
    with st.container():
        ProgressDisplay.render_progress_bar(progress)

    st.divider()

    # Statistics
    with st.container():
        ProgressDisplay.render_statistics(progress)

    # Action buttons based on status
    if status == 'completed':
        st.divider()
        st.success("🎉 Analysis Complete!")

        col_btn1, col_btn2 = st.columns(2)

        with col_btn1:
            if st.button("📄 View Docs", type="primary", use_container_width=True):
                # Store state and let user navigate via sidebar
                st.info("👈 Use sidebar to navigate to **Documentation** page")
                # Or if you have a documentation page, you can try:
                # st.session_state['show_documentation'] = True
                # st.rerun()

        with col_btn2:
            if st.button("📂 Projects", use_container_width=True):
                st.info("👈 Use sidebar to navigate to **Projects** page")

    elif status == 'failed':
        st.divider()
        st.error("❌ Analysis Failed")
        error_msg = progress.get('error_message', 'Unknown error occurred')
        st.error(f"**Error:** {error_msg}")

        if st.button("🔄 Retry Analysis", type="primary", use_container_width=True):
            try:
                with st.spinner("Restarting analysis..."):
                    client.restart_analysis(project_id)
                # Reset refresh state
                st.session_state['should_auto_refresh'] = True
                st.success("✅ Analysis restarted!")
                time.sleep(1)
                st.rerun()

            except Exception as e:
                st.error(f"Failed to restart: {str(e)}")

with col_right:
    # Activity feed
    with st.container():
        ProgressDisplay.render_activity_feed(activities)

# ==================== Completion Celebration ====================

# Show balloons only once when completed
if status == 'completed' and 'celebration_shown' not in st.session_state:
    st.balloons()
    st.toast("✅ Analysis complete!", icon="🎉")
    st.session_state['celebration_shown'] = True

# Reset celebration flag if status changes back to processing
if status != 'completed' and 'celebration_shown' in st.session_state:
    del st.session_state['celebration_shown']

# ==================== Debug Info (Optional) ====================

# Uncomment for debugging
# with st.expander("🔍 Debug Info"):
#     st.write("**Session State:**")
#     st.json({
#         'token_exists': 'token' in st.session_state,
#         'project_id': project_id,
#         'status': status,
#         'auto_refresh': st.session_state.get('should_auto_refresh'),
#     })
#     st.write("**Progress Data:**")
#     st.json(progress)
