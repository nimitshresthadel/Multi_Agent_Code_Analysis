import streamlit as st
import requests
import time
from datetime import datetime
from utils.auth import require_auth, get_auth_headers

# Page config
st.set_page_config(
    page_title="Agent Monitor - DocuGenius",
    page_icon="🤖",
    layout="wide"
)

# Authentication
require_auth()

# Get project ID
if 'current_project_id' not in st.session_state:
    st.warning("⚠️ No project selected")
    st.info("👈 Please use the sidebar to navigate to **Projects** page")
    st.stop()

project_id = st.session_state['current_project_id']

# API setup
API_BASE_URL = "http://localhost:8000"
headers = get_auth_headers()

# ==================== Agent Status Colors ====================

STATUS_COLORS = {
    "pending": "🟡",
    "running": "🔵",
    "completed": "🟢",
    "failed": "🔴",
    "skipped": "⚪"
}

STATUS_STYLES = {
    "pending": "background-color: #FFF3CD; color: #856404; padding: 5px 10px; border-radius: 5px;",
    "running": "background-color: #D1ECF1; color: #0C5460; padding: 5px 10px; border-radius: 5px;",
    "completed": "background-color: #D4EDDA; color: #155724; padding: 5px 10px; border-radius: 5px;",
    "failed": "background-color: #F8D7DA; color: #721C24; padding: 5px 10px; border-radius: 5px;",
    "skipped": "background-color: #E2E3E5; color: #383D41; padding: 5px 10px; border-radius: 5px;"
}


# ==================== Fetch Functions ====================

def get_agent_status():
    """Fetch agent execution status."""
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/v1/agent_analysis/{project_id}/agents",
            headers=headers
        )
        response.raise_for_status()
        return response.json()['data']['agents']
    except Exception as e:
        st.error(f"Error fetching agents: {str(e)}")
        return []


def get_progress_status():
    """Fetch overall progress."""
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/v1/progress/{project_id}",
            headers=headers
        )
        response.raise_for_status()
        return response.json()['data']
    except Exception as e:
        return None


def get_activities():
    """Fetch recent activities."""
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/v1/progress/{project_id}/activities?limit=20",
            headers=headers
        )
        response.raise_for_status()
        return response.json()['data']['activities']
    except Exception as e:
        return []


# ==================== Header ====================

st.title("🤖 Multi-Agent Orchestration Monitor")
st.caption("Real-time view of agent execution and coordination")

# Auto-refresh toggle
col1, col2, col3 = st.columns([3, 1, 1])

with col2:
    auto_refresh = st.checkbox("🔄 Auto-refresh", value=True)

with col3:
    if st.button("🔄 Refresh Now", use_container_width=True):
        st.rerun()

st.divider()

# ==================== Overall Progress ====================

progress_data = get_progress_status()

if progress_data:
    st.subheader("📊 Overall Progress")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Status",
            progress_data.get('status', 'Unknown').title(),
            delta=progress_data.get('stage_label', '')
        )

    with col2:
        st.metric(
            "Completion",
            f"{progress_data.get('overall_percentage', 0)}%"
        )

    with col3:
        if progress_data.get('total_files'):
            processed = progress_data.get('processed_files', 0)
            total = progress_data.get('total_files', 0)
            st.metric("Files Processed", f"{processed}/{total}")

    with col4:
        if progress_data.get('started_at'):
            started = datetime.fromisoformat(progress_data['started_at'].replace('Z', '+00:00'))
            duration = datetime.now().astimezone() - started.astimezone()
            minutes = int(duration.total_seconds() / 60)
            st.metric("Duration", f"{minutes} min")

    # Progress bar
    st.progress(progress_data.get('overall_percentage', 0) / 100)

    st.divider()

# ==================== Agent Execution Grid ====================

st.subheader("🎯 Agent Execution Status")

agents = get_agent_status()

if not agents:
    st.info("No agent executions found. Start an analysis to see agents in action.")
else:
    # Define agent display info
    AGENT_INFO = {
        "file_analyzer": {
            "icon": "📁",
            "title": "File Analyzer",
            "description": "Analyzing project structure and architecture patterns"
        },
        "code_extractor": {
            "icon": "🔍",
            "title": "Code Extractor",
            "description": "Extracting API signatures and key code elements"
        },
        "web_searcher": {
            "icon": "🌐",
            "title": "Web Searcher",
            "description": "Searching for framework docs and best practices online"
        },
        "security_auditor": {
            "icon": "🔒",
            "title": "Security Auditor",
            "description": "Checking for security vulnerabilities and OWASP compliance"
        },
        "doc_generator": {
            "icon": "📝",
            "title": "Documentation Generator",
            "description": "Creating technical documentation for developers"
        },
        "pm_summarizer": {
            "icon": "📊",
            "title": "PM Summarizer",
            "description": "Generating business-focused summaries for stakeholders"
        }
    }

    # Display agents in grid
    for agent in agents:
        agent_name = agent['name']
        agent_info = AGENT_INFO.get(agent_name, {
            "icon": "🤖",
            "title": agent_name.replace('_', ' ').title(),
            "description": "Processing..."
        })

        # Agent card
        with st.container():
            cols = st.columns([0.5, 3, 2, 2])

            with cols[0]:
                st.markdown(f"## {agent_info['icon']}")

            with cols[1]:
                st.markdown(f"**{agent_info['title']}**")
                st.caption(agent_info['description'])

            with cols[2]:
                status = agent['status']
                st.markdown(
                    f"<span style='{STATUS_STYLES.get(status, '')}'>"
                    f"{STATUS_COLORS.get(status, '⚪')} {status.upper()}"
                    f"</span>",
                    unsafe_allow_html=True
                )

                # Show timing if available
                if agent.get('started_at'):
                    started = datetime.fromisoformat(agent['started_at'].replace('Z', '+00:00'))
                    if agent.get('completed_at'):
                        completed = datetime.fromisoformat(agent['completed_at'].replace('Z', '+00:00'))
                        duration = (completed - started).total_seconds()
                        st.caption(f"⏱️ {duration:.1f}s")
                    elif status == "running":
                        elapsed = (datetime.now().astimezone() - started.astimezone()).total_seconds()
                        st.caption(f"⏱️ {elapsed:.1f}s (running)")

            with cols[3]:
                # Show metrics
                metrics = []
                if agent.get('tokens_used', 0) > 0:
                    metrics.append(f"🔢 {agent['tokens_used']:,} tokens")
                if agent.get('web_searches', 0) > 0:
                    metrics.append(f"🔍 {agent['web_searches']} searches")

                if metrics:
                    st.caption(" | ".join(metrics))

                # Show error if failed
                if agent.get('error'):
                    st.error(f"❌ {agent['error']}")

            st.divider()

# ==================== Activity Feed ====================

st.subheader("📜 Activity Feed")

activities = get_activities()

if not activities:
    st.info("No activities yet. Activities will appear here as agents execute.")
else:
    # Create activity feed
    for activity in activities[:10]:  # Show last 10
        activity_type = activity.get('type', 'info')
        timestamp = activity.get('timestamp', '')
        message = activity.get('message', '')

        # Format timestamp
        try:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            time_str = dt.strftime("%H:%M:%S")
        except:
            time_str = timestamp

        # Activity icon
        icons = {
            "info": "ℹ️",
            "progress": "⏳",
            "success": "✅",
            "error": "❌",
            "warning": "⚠️"
        }
        icon = icons.get(activity_type, "•")

        # Display activity
        with st.container():
            cols = st.columns([1, 4, 1])

            with cols[0]:
                st.caption(time_str)

            with cols[1]:
                st.markdown(f"{icon} {message}")

            # Show details if available
            if activity.get('details'):
                with st.expander("Details"):
                    st.json(activity['details'])

            st.divider()

# ==================== Agent Communication Flow ====================

st.divider()
st.subheader("🔄 Agent Communication Flow")

# Create flow diagram
st.markdown("""
```mermaid
graph TD
    A[📁 File Analyzer] --> B[🔍 Code Extractor]
    B --> C[🌐 Web Searcher]
    C --> D[🔒 Security Auditor]
    D --> E[📝 Doc Generator]
    D --> F[📊 PM Summarizer]
    E --> G[✅ Complete]
    F --> G

    style A fill:#e3f2fd
    style B fill:#e8f5e9
    style C fill:#fff3e0
    style D fill:#fce4ec
    style E fill:#f3e5f5
    style F fill:#e0f2f1
    style G fill:#c8e6c9 
""")

if agents:
    st.divider()
    st.subheader("📈 Performance Metrics")
    col1, col2, col3 = st.columns(3)

    with col1:
        total_tokens = sum(a.get('tokens_used', 0) for a in agents)
        st.metric("Total Tokens Used", f"{total_tokens:,}")
    with col2:
        total_searches = sum(a.get('web_searches', 0) for a in agents)
        st.metric("Web Searches Performed", total_searches)
    with col3:
        completed_agents = len([a for a in agents if a['status'] == 'completed'])
        st.metric("Agents Completed", f"{completed_agents}/{len(agents)}")

# Agent timing chart
st.markdown("#### ⏱️ Agent Execution Times")
timing_data = []

for agent in agents:
    if agent.get('started_at') and agent.get('completed_at'):
        started = datetime.fromisoformat(agent['started_at'].replace('Z', '+00:00'))
        completed = datetime.fromisoformat(agent['completed_at'].replace('Z', '+00:00'))
        duration = (completed - started).total_seconds()
        agent_info = AGENT_INFO.get(agent['name'], {})

        timing_data.append({
            "Agent": agent_info.get('title', agent['name']),
            "Duration (seconds)": duration
        })
if timing_data:
    import pandas as pd
    df = pd.DataFrame(timing_data)
    st.bar_chart(df.set_index("Agent"))

#Auto-refresh
if auto_refresh:
    time.sleep(2)  # Refresh every 2 seconds
    st.rerun()
