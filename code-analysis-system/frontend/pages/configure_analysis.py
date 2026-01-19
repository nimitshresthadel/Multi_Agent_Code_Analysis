import streamlit as st
import requests
from utils.auth import require_auth, get_auth_headers

# Page config
st.set_page_config(
    page_title="Configure Analysis - DocuGenius",
    page_icon="⚙️",
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


# ==================== Load Current Config ====================

@st.cache_data(ttl=60)
def get_config(proj_id, _headers):
    """Fetch current configuration."""
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/v1/config/{proj_id}",
            headers=_headers
        )
        response.raise_for_status()
        return response.json()['data']
    except Exception as e:
        st.error(f"Error loading config: {str(e)}")
        return None


def save_config(config_data):
    """Save configuration."""
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/config",
            json=config_data,
            headers=headers
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error saving config: {str(e)}")
        return None


# ==================== Header ====================

st.title("⚙️ Analysis Configuration")
st.caption("Configure how agents analyze your codebase")
st.divider()

# Load current config
current_config = get_config(project_id, headers)

# ==================== Configuration Form ====================

with st.form("config_form"):
    # Section 1: Analysis Depth
    st.subheader("📊 Analysis Depth")

    col1, col2 = st.columns(2)

    with col1:
        depth = st.selectbox(
            "Analysis Depth",
            options=["quick", "standard", "deep"],
            index=["quick", "standard", "deep"].index(current_config.get("depth", "standard")),
            help="Quick: Fast overview | Standard: Balanced | Deep: Comprehensive analysis"
        )

    with col2:
        verbosity = st.selectbox(
            "Documentation Verbosity",
            options=["low", "medium", "high"],
            index=["low", "medium", "high"].index(current_config.get("verbosity", "medium")),
            help="How detailed should the documentation be?"
        )

    st.divider()

    # Section 2: Feature Flags
    st.subheader("🎯 Analysis Features")

    col1, col2, col3 = st.columns(3)

    with col1:
        enable_web_search = st.checkbox(
            "🔍 Web-Augmented Analysis",
            value=current_config.get("enable_web_search", True),
            help="Search for framework docs and best practices online"
        )

        enable_security = st.checkbox(
            "🔒 Security Analysis",
            value=current_config.get("enable_security_analysis", True),
            help="Check for security vulnerabilities"
        )

    with col2:
        enable_diagrams = st.checkbox(
            "📊 Generate Diagrams",
            value=current_config.get("enable_diagrams", True),
            help="Create architecture and sequence diagrams"
        )

        enable_performance = st.checkbox(
            "⚡ Performance Analysis",
            value=current_config.get("enable_performance_analysis", False),
            help="Analyze performance bottlenecks"
        )

    with col3:
        enable_quality = st.checkbox(
            "✨ Code Quality Metrics",
            value=current_config.get("enable_code_quality", True),
            help="Calculate complexity and maintainability scores"
        )

    st.divider()

    # Section 3: Personas
    st.subheader("👥 Target Personas")
    st.caption("Select which types of documentation to generate")

    col1, col2, col3 = st.columns(3)

    with col1:
        persona_sde = st.checkbox(
            "💻 Software Engineer",
            value="SDE" in current_config.get("personas", ["SDE", "PM"]),
            help="Technical documentation for developers"
        )

    with col2:
        persona_pm = st.checkbox(
            "📋 Product Manager",
            value="PM" in current_config.get("personas", ["SDE", "PM"]),
            help="Business-focused summaries"
        )

    with col3:
        persona_qa = st.checkbox(
            "🧪 QA Engineer",
            value="QA" in current_config.get("personas", []),
            help="Testing guidelines and test coverage"
        )

    # Build personas list
    personas = []
    if persona_sde:
        personas.append("SDE")
    if persona_pm:
        personas.append("PM")
    if persona_qa:
        personas.append("QA")

    st.divider()

    # Section 4: Web Search Settings
    if enable_web_search:
        st.subheader("🌐 Web Search Settings")

        col1, col2 = st.columns(2)

        with col1:
            max_searches = st.slider(
                "Maximum Web Searches",
                min_value=1,
                max_value=10,
                value=current_config.get("max_web_searches", 5),
                help="How many web searches agents can perform"
            )

        with col2:
            search_depth = st.slider(
                "Results per Search",
                min_value=1,
                max_value=5,
                value=current_config.get("search_depth", 3),
                help="Number of results to retrieve per search"
            )

        st.divider()

    # Section 5: Diagram Settings
    if enable_diagrams:
        st.subheader("📐 Diagram Options")

        col1, col2 = st.columns(2)

        with col1:
            diagram_format = st.selectbox(
                "Diagram Format",
                options=["mermaid", "plantuml"],
                index=0,
                help="Format for generated diagrams"
            )

            include_class = st.checkbox(
                "Class Diagrams",
                value=current_config.get("include_class_diagrams", True)
            )

        with col2:
            include_sequence = st.checkbox(
                "Sequence Diagrams",
                value=current_config.get("include_sequence_diagrams", True)
            )

            include_er = st.checkbox(
                "ER Diagrams",
                value=current_config.get("include_er_diagrams", False)
            )

        st.divider()

    # Section 6: Advanced Settings
    with st.expander("⚙️ Advanced Settings"):
        max_parallel = st.slider(
            "Maximum Parallel Agents",
            min_value=1,
            max_value=5,
            value=current_config.get("max_parallel_agents", 3),
            help="How many agents can run simultaneously"
        )

        agent_timeout = st.number_input(
            "Agent Timeout (seconds)",
            min_value=60,
            max_value=600,
            value=300,
            help="Maximum time for each agent to complete"
        )

    # Section 7: Save as Template
    st.divider()

    save_as_template = st.checkbox("💾 Save as Template", value=False)

    if save_as_template:
        template_name = st.text_input(
            "Template Name",
            placeholder="e.g., 'Deep Security Audit'"
        )
    else:
        template_name = None

    # Submit button
    col1, col2, col3 = st.columns([2, 1, 1])

    with col2:
        submitted = st.form_submit_button(
            "💾 Save Configuration",
            type="primary",
            use_container_width=True
        )

    with col3:
        reset = st.form_submit_button(
            "🔄 Reset to Defaults",
            use_container_width=True
        )

# ==================== Handle Form Submission ====================

if submitted:
    # Build config data
    config_data = {
        "project_id": project_id,
        "depth": depth,
        "verbosity": verbosity,
        "enable_web_search": enable_web_search,
        "enable_diagrams": enable_diagrams,
        "enable_security_analysis": enable_security,
        "enable_performance_analysis": enable_performance,
        "enable_code_quality": enable_quality,
        "personas": personas,
        "max_parallel_agents": max_parallel,
        "max_web_searches": max_searches if enable_web_search else 0,
        "diagram_format": diagram_format if enable_diagrams else "mermaid",
        "include_class_diagrams": include_class if enable_diagrams else False,
        "include_sequence_diagrams": include_sequence if enable_diagrams else False,
        "include_er_diagrams": include_er if enable_diagrams else False,
        "name": template_name,
        "is_template": save_as_template
    }

    # Save config
    result = save_config(config_data)

    if result and result.get("success"):
        st.success("✅ Configuration saved successfully!")

        if save_as_template:
            st.success(f"💾 Saved as template: '{template_name}'")

        # Clear cache and rerun
        st.cache_data.clear()
        st.rerun()
    else:
        st.error("❌ Failed to save configuration")

if reset:
    # Reset to defaults by clearing and reloading
    st.cache_data.clear()
    st.rerun()

# ==================== Configuration Summary ====================

st.divider()

with st.expander("📋 Current Configuration Summary", expanded=False):
    st.json(current_config)

# ==================== Quick Templates ====================

st.divider()
st.subheader("⚡ Quick Templates")

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("🚀 Quick Scan", use_container_width=True):
        quick_config = {
            "project_id": project_id,
            "depth": "quick",
            "verbosity": "low",
            "enable_web_search": False,
            "enable_diagrams": False,
            "personas": ["SDE"],
            "max_parallel_agents": 2
        }
        save_config(quick_config)
        st.success("Applied Quick Scan template")
        st.cache_data.clear()
        st.rerun()

with col2:
    if st.button("📚 Comprehensive", use_container_width=True):
        comprehensive_config = {
            "project_id": project_id,
            "depth": "deep",
            "verbosity": "high",
            "enable_web_search": True,
            "enable_diagrams": True,
            "enable_security_analysis": True,
            "personas": ["SDE", "PM"],
            "max_parallel_agents": 3,
            "max_web_searches": 5
        }
        save_config(comprehensive_config)
        st.success("Applied Comprehensive template")
        st.cache_data.clear()
        st.rerun()

with col3:
    if st.button("🔒 Security Audit", use_container_width=True):
        security_config = {
            "project_id": project_id,
            "depth": "deep",
            "verbosity": "high",
            "enable_web_search": True,
            "enable_security_analysis": True,
            "personas": ["SDE"],
            "max_parallel_agents": 2,
            "max_web_searches": 3
        }
        save_config(security_config)
        st.success("Applied Security Audit template")
        st.cache_data.clear()
        st.rerun()
