import streamlit as st
from typing import Dict, List
from utils.api_client import APIClient

api_client = APIClient()


def main():
    st.title("🔍 Code Search & Discovery")

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

    if not ready_projects:
        st.warning("⚠️ No analyzed projects. Please complete analysis first.")
        return

    selected_project = st.selectbox(
        "Select Project",
        options=ready_projects,
        format_func=lambda x: x['name']
    )

    if not selected_project:
        return

    project_id = selected_project['id']

    # Search interface
    st.markdown("---")
    st.markdown("### 🔎 Semantic Search")
    st.caption("Search by what the code does, not just by keywords")

    search_query = st.text_input(
        "What are you looking for?",
        placeholder="e.g., authentication, database queries, API endpoints",
        help="Describe what you're looking for in natural language"
    )

    col1, col2 = st.columns([3, 1])
    with col1:
        top_k = st.slider("Number of results", 5, 20, 10)
    with col2:
        search_button = st.button("🔍 Search", type="primary", use_container_width=True)

    # Perform search
    if search_button and search_query:
        with st.spinner("Searching..."):
            results = api_client.semantic_search(project_id, search_query, top_k)

        if results:
            st.success(f"✅ Found {len(results)} relevant code sections")
            display_search_results(results, project_id)
        else:
            st.info("No results found. Try a different query.")

    # Quick filters
    st.markdown("---")
    st.markdown("### 🏷️ Browse by Category")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("🔐 Authentication", use_container_width=True):
            quick_search(project_id, "authentication", top_k)

    with col2:
        if st.button("🗄️ Database", use_container_width=True):
            quick_search(project_id, "database queries models", top_k)

    with col3:
        if st.button("🌐 API Routes", use_container_width=True):
            quick_search(project_id, "API endpoints routes", top_k)

    with col4:
        if st.button("⚙️ Configuration", use_container_width=True):
            quick_search(project_id, "configuration settings", top_k)


def quick_search(project_id: str, query: str, top_k: int):
    """Perform quick search and display results."""
    with st.spinner(f"Searching for {query}..."):
        results = api_client.semantic_search(project_id, query, top_k)

    if results:
        st.success(f"✅ Found {len(results)} results for '{query}'")
        display_search_results(results, project_id)
    else:
        st.info(f"No results found for '{query}'")


def display_search_results(results: List[Dict], project_id: str):
    """Display search results with code snippets."""

    for i, result in enumerate(results, 1):
        with st.expander(
                f"**{i}. {result['name']}** ({result['chunk_type']}) - "
                f"{result['file_path']} (Lines {result['start_line']}-{result['end_line']})",
                expanded=(i <= 3)  # Expand first 3 results
        ):
            # Header with metadata
            col1, col2, col3 = st.columns([2, 2, 1])

            with col1:
                st.markdown(f"**File:** `{result['file_path']}`")
            with col2:
                st.markdown(f"**Type:** {result['chunk_type']}")
            with col3:
                similarity = result['similarity_score']
                if similarity >= 0.8:
                    st.success(f"Match: {similarity:.0%}")
                elif similarity >= 0.6:
                    st.warning(f"Match: {similarity:.0%}")
                else:
                    st.info(f"Match: {similarity:.0%}")

            # Signature
            st.markdown(f"**Signature:**")
            st.code(result['signature'], language="python")

            # Docstring if available
            if result.get('docstring'):
                st.markdown(f"**Documentation:**")
                st.info(result['docstring'])

            # Code
            st.markdown(f"**Code:**")
            st.code(result['code'], language="python", line_numbers=True)

            # Action buttons
            col1, col2, col3 = st.columns(3)

            with col1:
                if st.button(f"🔗 Find Similar", key=f"similar_{result['chunk_id']}"):
                    find_similar_chunks(result['chunk_id'], project_id)

            with col2:
                if st.button(f"📋 Copy Code", key=f"copy_{result['chunk_id']}"):
                    st.toast("Code copied to clipboard!")

            with col3:
                if st.button(f"📂 View File", key=f"file_{result['chunk_id']}"):
                    st.info(f"Opening {result['file_path']}...")


def find_similar_chunks(chunk_id: str, project_id: str):
    """Find and display similar code chunks."""
    with st.spinner("Finding similar code..."):
        similar = api_client.find_similar_chunks(chunk_id, project_id, top_k=5)

    if similar:
        st.markdown("### 🔗 Similar Code Sections")
        display_search_results(similar, project_id)
    else:
        st.info("No similar chunks found")


if __name__ == "__main__":
    main()
