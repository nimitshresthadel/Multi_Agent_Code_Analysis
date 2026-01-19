import streamlit as st
from datetime import datetime
from typing import Dict, List


class ProgressDisplay:
    """Streamlit components for displaying analysis progress."""

    @staticmethod
    def inject_custom_css():
        """Add custom CSS styling."""
        st.markdown("""
            <style>
            /* Progress bars */
            .stProgress > div > div > div > div {
                background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            }

            /* Metrics */
            [data-testid="stMetricValue"] {
                font-size: 1.5rem;
                font-weight: 600;
            }

            /* Activity cards - using container styling */
            .element-container {
                margin-bottom: 0.5rem;
            }
            </style>
        """, unsafe_allow_html=True)

    @staticmethod
    def render_progress_bar(progress: Dict):
        """Render the main progress bar."""
        overall_percentage = progress.get('overall_percentage', 0)
        stage_percentage = progress.get('stage_percentage', 0)
        stage_label = progress.get('stage_label', 'Processing')
        status = progress.get('status', 'queued')
        current_file = progress.get('current_file')
        processed_files = progress.get('processed_files', 0)
        total_files = progress.get('total_files', 0)

        # Status emoji
        status_emoji = {
            'queued': '⏳',
            'in_progress': '⚙️',
            'completed': '🎉',
            'failed': '❌'
        }

        # Overall progress header
        st.markdown("### Overall Progress")
        col1, col2 = st.columns([4, 1])
        with col1:
            st.progress(overall_percentage / 100)
        with col2:
            st.metric("Overall progress", f"{int(overall_percentage)}%", label_visibility="collapsed")

        st.divider()

        # Current stage
        st.markdown(f"#### {status_emoji.get(status, '⚙️')} {stage_label}")
        st.progress(stage_percentage / 100)

        # File progress details
        if total_files > 0:
            col1, col2 = st.columns(2)
            with col1:
                if current_file:
                    st.caption(f"📄 **{current_file}**")
                else:
                    st.caption("Preparing files...")
            with col2:
                st.caption(f"**{processed_files}** / **{total_files}** files")

        # Status messages
        if status == 'completed':
            st.success("🎉 **Analysis Complete!** Your documentation is ready.")
        elif status == 'failed':
            st.error("❌ **Processing failed.** Check the activity feed for details.")

    @staticmethod
    def render_statistics(progress: Dict):
        """Render processing statistics card."""
        st.markdown("### 📊 Statistics")

        col1, col2 = st.columns(2)

        with col1:
            # Status
            status = progress.get('status', 'queued').replace('_', ' ').title()
            st.metric("Status", status)

            # Files
            if progress.get('total_files', 0) > 0:
                files_text = f"{progress.get('processed_files', 0)}/{progress.get('total_files', 0)}"
                st.metric("Files", files_text)

        with col2:
            # Chunks
            if progress.get('total_chunks', 0) > 0:
                chunks_text = f"{progress.get('processed_chunks', 0)}/{progress.get('total_chunks', 0)}"
                st.metric("Code Chunks", chunks_text)

            # Start time
            if progress.get('started_at'):
                try:
                    started = datetime.fromisoformat(progress['started_at'].replace('Z', '+00:00'))
                    st.metric("Started", started.strftime("%I:%M %p"))
                except:
                    pass

    @staticmethod
    def render_activity_feed(activities: List[Dict], max_items: int = 100):
        """Render the activity feed."""
        st.markdown("### 📋 Activity Feed")

        if not activities:
            st.info("🕐 Waiting for analysis to start...")
            return

        st.caption(f"Showing **{min(len(activities), max_items)}** recent activities")
        st.divider()

        # Activity icons
        activity_icons = {
            'info': 'ℹ️',
            'success': '✅',
            'warning': '⚠️',
            'error': '❌',
            'milestone': '🏆',
        }

        # Render activities
        for activity in activities[:max_items]:
            activity_type = activity.get('type', 'info')
            icon = activity_icons.get(activity_type, 'ℹ️')

            # Message with icon
            st.markdown(f"{icon} **{activity.get('message', '')}**")

            # Details
            if activity.get('details'):
                st.caption(activity['details'])

            # File name (in monospace)
            if activity.get('file_name'):
                st.code(activity['file_name'], language=None)

            # Timestamp
            if activity.get('timestamp'):
                try:
                    timestamp = datetime.fromisoformat(activity['timestamp'].replace('Z', '+00:00'))
                    time_str = timestamp.strftime('%I:%M:%S %p')
                    st.caption(f"🕐 {time_str}")
                except:
                    pass

            st.divider()
