"""Home page with login and signup."""
import streamlit as st
from utils.auth import init_session_state, login_user
from utils.api_client import APIClient

# Page config
st.set_page_config(
    page_title="Code Analysis System",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
init_session_state()

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        color: #FF6B6B;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.5rem;
        text-align: center;
        color: #666;
        margin-bottom: 2rem;
    }
    .feature-box {
        background-color: #00008B;
        padding: 1.5rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
    .stButton>button {
        width: 100%;
        background-color: #FF6B6B;
        color: white;
        border-radius: 5px;
        padding: 0.5rem;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)


def show_welcome():
    """Show welcome screen."""
    st.markdown('<p class="main-header">🚀 Code Analysis System</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Analyze your code with AI-powered insights</p>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("""
        <div class="feature-box">
            <h3>📊 Deep Analysis</h3>
            <p>Get comprehensive code quality metrics and insights</p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div class="feature-box">
            <h3>🎯 Personalized</h3>
            <p>Tailored recommendations for different personas</p>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown("""
        <div class="feature-box">
            <h3>⚡ Fast & Easy</h3>
            <p>Upload your code and get insights in minutes</p>
        </div>
        """, unsafe_allow_html=True)


def show_login():
    """Show login form."""
    st.markdown("### 🔐 Login to Your Account")

    with st.form("login_form"):
        email = st.text_input("Email", placeholder="your.email@example.com")
        password = st.text_input("Password", type="password", placeholder="Enter your password")
        submit = st.form_submit_button("Login")

        if submit:
            if not email or not password:
                st.error("Please fill in all fields")
            else:
                with st.spinner("Logging in..."):
                    if login_user(email, password):
                        st.success("✅ Login successful!")
                        st.rerun()
                    else:
                        st.error("❌ Invalid email or password")


def show_signup():
    """Show signup form."""
    st.markdown("### 📝 Create New Account")

    with st.form("signup_form"):
        col1, col2 = st.columns(2)

        with col1:
            full_name = st.text_input("Full Name", placeholder="John Doe")
            email = st.text_input("Email", placeholder="john.doe@example.com")

        with col2:
            username = st.text_input("Username", placeholder="johndoe")
            password = st.text_input("Password", type="password", placeholder="Min 8 characters")

        confirm_password = st.text_input("Confirm Password", type="password", placeholder="Re-enter password")

        agree = st.checkbox("I agree to the Terms of Service and Privacy Policy")
        submit = st.form_submit_button("Create Account")

        if submit:
            if not all([full_name, email, username, password, confirm_password]):
                st.error("Please fill in all fields")
            elif password != confirm_password:
                st.error("Passwords do not match")
            elif len(password) < 8:
                st.error("Password must be at least 8 characters")
            elif not agree:
                st.error("Please agree to the Terms of Service")
            else:
                with st.spinner("Creating account..."):
                    client = APIClient()
                    result = client.signup(email, username, password, full_name)

                    if result["success"]:
                        st.success("✅ Account created successfully! Please log in.")
                        st.balloons()
                    else:
                        st.error(f"❌ {result['error']}")


def main():
    """Main function."""
    # Check if already authenticated
    if st.session_state.authenticated:
        st.markdown(f"### Welcome back, {st.session_state.user['full_name']}! 👋")
        st.info("👈 Use the sidebar to navigate to your dashboard")

        # Show quick stats
        client = APIClient()
        projects = client.get_projects()

        if projects["success"]:
            col1, col2, col3, col4 = st.columns(4)

            data = projects["data"]
            with col1:
                st.metric("Total Projects", data.get("total", 0))
            with col2:
                uploaded = len([p for p in data.get("projects", []) if p["status"] == "uploaded"])
                st.metric("Uploaded", uploaded)
            with col3:
                processing = len([p for p in data.get("projects", []) if p["status"] == "processing"])
                st.metric("Processing", processing)
            with col4:
                completed = len([p for p in data.get("projects", []) if p["status"] == "completed"])
                st.metric("Completed", completed)

        # Logout button
        if st.button("🚪 Logout"):
            from utils.auth import logout_user
            logout_user()
            st.rerun()

    else:
        # Show welcome
        show_welcome()

        st.markdown("---")

        # Login/Signup tabs
        tab1, tab2 = st.tabs(["🔐 Login", "📝 Sign Up"])

        with tab1:
            show_login()

        with tab2:
            show_signup()


if __name__ == "__main__":
    main()
