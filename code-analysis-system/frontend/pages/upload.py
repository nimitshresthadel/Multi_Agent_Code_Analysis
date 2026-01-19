"""Project upload page."""
import streamlit as st
from utils.auth import require_auth
from utils.api_client import APIClient

st.set_page_config(
    page_title="Upload Project - Code Analysis",
    page_icon="⬆️",
    layout="wide"
)

# Require authentication
require_auth()

client = APIClient()


def show_create_project_form():
    """Show form to create a new project with ZIP or GitHub options."""
    st.markdown("### 📦 Create New Project Via Github Repo")

    # Project details
    with st.form("create_project_form", clear_on_submit=True):
        # Basic information
        project_name = st.text_input(
            "Project Name *",
            placeholder="e.g., My Awesome Project",
            help="Enter a descriptive name for your project"
        )

        project_description = st.text_area(
            "Description",
            placeholder="Brief description of your project...",
            help="Optional description"
        )

        # Persona selection
        st.markdown("**Select Analysis Personas:**")
        col1, col2 = st.columns(2)

        with col1:
            sde_persona = st.checkbox("👨‍💻 Software Developer", value=True)
        with col2:
            pm_persona = st.checkbox("📊 Product Manager", value=False)

        # GitHub URL
        st.markdown("#### GitHub Repository")
        github_url = st.text_input(
            "Repository URL *",
            placeholder="https://github.com/username/repository",
            help="Enter the full GitHub repository URL"
        )

        github_branch = st.text_input(
            "Branch",
            value="master",
            placeholder="master",
            help="Branch to clone (default: master)"
        )

        if github_url:
            st.info(f"📍 Will clone from: `{github_url}` (branch: `{github_branch}`)")

        # Submit button
        st.markdown("---")
        submitted = st.form_submit_button("🚀 Create Project", use_container_width=True)

        if submitted:
            # Validation
            if not project_name:
                st.error("❌ Project name is required!")
                return

            if not sde_persona and not pm_persona:
                st.error("❌ Please select at least one persona!")
                return

            # Prepare personas list
            personas = []
            if sde_persona:
                personas.append("sde")
            if pm_persona:
                personas.append("pm")

            #else:  # GitHub URL
            if not github_url:
                st.error("❌ Please enter a GitHub repository URL!")
                return

            # Create from GitHub
            create_project_from_github(
                name=project_name,
                description=project_description,
                personas=personas,
                github_url=github_url
            )


def create_project_from_zip(name: str, description: str, personas: list, file):
    """Create project by uploading ZIP file."""
    with st.spinner("📤 Uploading and creating project..."):
        try:
            # Call API to create project from ZIP
            response = client.create_project_from_zip(
                name=name,
                description=description,
                personas=personas,
                file=file
            )

            if response:
                st.success(f"✅ Project '{name}' created successfully!")
                st.balloons()

                # Show project details
                st.json(response)

                # Refresh the page after 2 seconds
                import time
                time.sleep(2)
                st.rerun()
            else:
                st.error("❌ Failed to create project. Please try again.")

        except Exception as e:
            st.error(f"❌ Error: {str(e)}")


def create_project_from_github(name: str, description: str, personas: list,
                               github_url: str):
    """Create project from GitHub repository."""
    with st.spinner("🔗 Connecting to GitHub and cloning repository..."):
        try:
            # Call API to create project from GitHub
            response = client.create_project_from_github(
                name=name,
                description=description,
                personas=personas,
                github_url=github_url
            )

            if response:
                st.success(f"✅ Project '{name}' created from GitHub!")
                st.balloons()

                # Show project details
                st.json(response)

                # Refresh the page after 2 seconds
                import time
                time.sleep(2)
                st.rerun()
            else:
                st.error("❌ Failed to create project from GitHub. Please check the URL and try again.")

        except Exception as e:
            st.error(f"❌ Error: {str(e)}")


def main():
    """Main upload function."""
    st.title("⬆️ Upload New Project")

    st.markdown("""
    Upload your code project as a ZIP file to get AI-powered analysis and insights.
    """)


    # Upload form
    with st.form("upload_form"):
        # Project name
        project_name = st.text_input(
            "Project Name *",
            placeholder="My Awesome Project",
            help="Enter a descriptive name for your project"
        )

        # Description
        description = st.text_area(
            "Description",
            placeholder="What does this project do?",
            help="Optional description of your project"
        )

        # Personas
        st.markdown("**Select Target Personas** *")
        col1, col2 = st.columns(2)

        with col1:
            sde = st.checkbox("👨‍💻 Software Developer", value=True)
        with col2:
            pm = st.checkbox("📊 Product Manager")

        # File upload
        uploaded_file = st.file_uploader(
            "Upload ZIP file *",
            type=['zip'],
            help="Upload your project as a ZIP file (max 100MB)"
        )

        # Submit button
        submitted = st.form_submit_button("🚀 Upload Project", use_container_width=True)

        if submitted:
            # Validation
            if not project_name:
                st.error("❌ Project name is required")
            elif not uploaded_file:
                st.error("❌ Please upload a ZIP file")
            elif not any([sde, pm]):
                st.error("❌ Please select at least one persona")
            else:
                # Build personas list
                personas = []
                if sde:
                    personas.append("sde")
                if pm:
                    personas.append("pm")

                # Upload
                with st.spinner("Uploading project... This may take a minute."):
                    result = client.upload_project(
                        name=project_name,
                        file=uploaded_file,
                        description=description,
                        personas=personas
                    )

                    if result["success"]:
                        st.success("✅ Project uploaded successfully!")
                        st.balloons()

                        # Show project details
                        project = result["data"]
                        st.markdown(f"""
                        **Project ID:** `{project['id']}`

                        **Status:** {project['status']}

                        Your project is being processed. Check the dashboard for updates!
                        """)

                        # Navigation buttons
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("📊 Go to Dashboard"):
                                st.switch_page("pages/dashboard.py")
                        with col2:
                            if st.button("📁 View All Projects"):
                                st.switch_page("pages/projects.py")
                    else:
                        st.error(f"❌ Upload failed: {result['error']}")

    # Instructions
    st.markdown("---")
    st.markdown("### 📋 Upload Instructions")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        **Supported Files:**
        - ZIP archives (.zip)
        - Maximum size: 100MB
        - Should contain source code files
        """)

    with col2:
        st.markdown("""
        **Personas:**
        - **SDE**: Technical code analysis
        - **PM**: Business and feature insights
        - **Executive**: High-level overview
        """)

    show_create_project_form()


if __name__ == "__main__":
    main()
