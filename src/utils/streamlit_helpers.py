"""
Helper functions for Streamlit app
"""

import streamlit as st
from pathlib import Path
from typing import Optional, List
from ..core.models import PaperMetadata


@st.cache_resource
def get_database():
    """Get database connection (cached)."""
    from src.storage.database import PaperDatabase
    return PaperDatabase()


@st.cache_resource
def get_conference_manager():
    """Get conference manager (cached)."""
    from src.core.conference import ConferenceManager
    return ConferenceManager()


def render_paper_card(paper, show_details: bool = False):
    """Render a single paper card."""
    col1, col2 = st.columns([4, 1])
    
    with col1:
        st.markdown(f"### {paper.title}")
        st.caption(f"**Authors:** {paper.get_authors_string()}")
        
        if paper.overview:
            length = 300 if show_details else 150
            overview = paper.overview[:length]
            if len(paper.overview) > length:
                overview += "..."
            st.write(overview)
    
    with col2:
        if paper.verified:
            st.success("✅")
        elif paper.needs_review:
            st.warning("⚠️")
        else:
            st.info("⏳")


def render_paper_table(papers: List) -> None:
    """Render papers as table."""
    data = {
        "Title": [p.title[:50] for p in papers],
        "Authors": [len(p.authors) for p in papers],
        "Status": ["✅" if p.verified else "⏳" for p in papers],
        "PDF": ["📄" if p.pdf_found else "❌" for p in papers],
    }
    
    st.dataframe(data, use_container_width=True, hide_index=True)


def format_author_list(authors: List, max_display: int = 3) -> str:
    """Format author list for display."""
    if not authors:
        return "Unknown"
    
    if len(authors) <= max_display:
        return ", ".join([a.name for a in authors])
    else:
        first = ", ".join([a.name for a in authors[:max_display]])
        remaining = len(authors) - max_display
        return f"{first}, +{remaining} more"

def display_paper_detail(paper: PaperMetadata):
    """Display detailed view of a paper."""
    
    # Header
    st.markdown(f"## {paper.title}")
    st.caption(f"👥 {paper.get_authors_string()}")
    
    if paper.conference_name:
        st.badge(paper.conference_name.upper(), icon="📚")
    
    st.divider()
    
    # Overview section
    if paper.overview:
        st.markdown("### 📝 Overview")
        st.write(paper.overview)
        st.divider()
    
    # Metadata section
    st.markdown("### 📊 Metadata")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("PDF Status", "✅ Available" if paper.pdf_found else "❌ Missing")
    
    with col2:
        st.metric("Authors", len(paper.authors))
    
    with col3:
        st.metric("Added", paper.created_at.strftime('%Y-%m-%d'))
    
    st.divider()
    
    # Actions section
    st.markdown("### 🔧 Actions")
    
    action_col1, action_col2, action_col3 = st.columns(3)
    
    with action_col1:
        if paper.pdf_found and paper.pdf_path:
            pdf_path = Path(paper.pdf_path)
            if pdf_path.exists():
                with open(pdf_path, "rb") as pdf_file:
                    st.download_button(
                        label="📥 Download PDF",
                        data=pdf_file,
                        file_name=pdf_path.name,
                        mime="application/pdf",
                        use_container_width=True
                    )
    
    with action_col2:
        if paper.source_files:
            st.caption(f"📁 Source: {Path(paper.source_files[0]).name}")
    
    with action_col3:
        if st.button("✖️ Close", use_container_width=True):
            st.session_state.selected_paper_detail = None
            st.rerun()