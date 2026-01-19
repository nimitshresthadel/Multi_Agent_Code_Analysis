"""User settings page."""
import streamlit as st
from utils.auth import require_auth, get_current_user, logout_user
from utils.api_client import APIClient

st.set_page_config(
    page_title="Settings - Code Analysis",
    page_icon="⚙️",
    layout="wide"
)

# Require authentication
require_auth()

user = get_current_user()
client = APIClient()


def show_profile_settings():
    """Show profile settings."""
    st.markdown("### 👤 Profile Settings")

    with st.form("profile_form"):
        col1, col2 = st.columns(2)

        with col1:
            full_name = st.text_input("Full Name", value=user['full_name'])
            email = st.text_input("Email", value=user['email'], disabled=True, help="Email cannot be changed")

        with col2:
            username = st.text_input("Username", value=user['username'], disabled=True,
                                     help="Username cannot be changed")
            role = st.text_input("Role", value=user['role'], disabled=True)

        submitted = st.form_submit_button("💾 Save Changes")

        if submitted:
            if full_name != user['full_name']:
                result = client.update_profile(full_name=full_name)
                if result["success"]:
                    st.success("✅ Profile updated successfully!")
                    st.session_state.user['full_name'] = full_name
                    st.rerun()
                else:
                    st.error(f"❌ Failed to update: {result['error']}")
            else:
                st.info("No changes made")


def show_account_info():
    """Show account information."""
    st.markdown("### 📊 Account Information")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Account Status", "Active" if user['is_active'] else "Inactive")

    with col2:
        st.metric("Role", user['role'].upper())

    with col3:
        projects_result = client.get_projects()
        if projects_result["success"]:
            total_projects = projects_result["data"]["total"]
            st.metric("Total Projects", total_projects)

    st.markdown(f"""
    **Account Created:** {user['created_at'][:10]}

    **User ID:** `{user['id']}`
    """)


def show_danger_zone():
    """Show danger zone with logout."""
    st.markdown("### ⚠️ Danger Zone")

    st.warning("**Logout:** This will end your current session")

    if st.button("🚪 Logout", type="primary"):
        logout_user()
        st.success("Logged out successfully!")
        st.rerun()


def main():
    """Main settings function."""
    st.title("⚙️ Settings")

    # Profile settings
    show_profile_settings()

    st.markdown("---")

    # Account info
    show_account_info()

    st.markdown("---")

    # Danger zone
    show_danger_zone()


if __name__ == "__main__":
    main()
