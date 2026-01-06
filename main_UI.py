"""Research Reader - Streamlit Web Application"""

import streamlit as st
from pathlib import Path
import sys
import os

sys.path.insert(0, str(Path(__file__).parent))

from src.storage.database import PaperDatabase
from src.utils.download_service import DownloadService

st.set_page_config(
    page_title="Research Reader",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.info("📱 This is a **read-only** version. Papers and PDFs are pre-loaded and cannot be modified.")

@st.cache_resource
def get_summarizer():
    from src.utils.conference_summarizer import ConferenceSummarizer
    return ConferenceSummarizer()
    
@st.cache_resource
def get_database():
    db_path = Path("data/database/papers.db")
    if not db_path.exists():
        st.error("❌ Database not found. Please ensure papers.db is in the repository.")
        st.stop()
    return PaperDatabase()

@st.cache_resource
def get_download_service():
    try:
        return DownloadService()
    except Exception as e:
        st.warning(f"⚠️ Download service unavailable: {str(e)}")
        return None

if "selected_paper" not in st.session_state:
    st.session_state.selected_paper = None

db = get_database()
download_service = get_download_service()

st.sidebar.title("📚 Research Reader")
st.sidebar.write("Conference Paper Browser")
st.sidebar.divider()

page = st.sidebar.radio(
    "Navigation",
    options=["🏠 Home", "📄 Papers", "🔍 Search", "📈 Analytics"],
    label_visibility="collapsed"
)

st.sidebar.divider()

with st.sidebar:
    st.subheader("📊 Quick Stats")
    
    stats = db.get_statistics()
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Papers", stats['total_papers'])
    with col2:
        st.metric("PDFs Found", stats['papers_with_pdf'])    
    pdf_pct = (stats['papers_with_pdf'] / stats['total_papers'] * 100) if stats['total_papers'] > 0 else 0
    st.metric("PDF Coverage", f"{pdf_pct:.0f}%")

    if st.sidebar.button("🔄 Regenerate All Summaries"):
        summarizer = get_summarizer()
        conferences = db.get_all_conferences()
        
        progress_bar = st.sidebar.progress(0)
        for i, conf in enumerate(conferences):
            st.sidebar.text(f"Processing {conf}...")
            summarizer.get_or_generate_summary(conf, force_regenerate=True)
            progress_bar.progress((i + 1) / len(conferences))
        
        st.sidebar.success("All summaries regenerated!")
        st.rerun()

if page == "🏠 Home":
    st.title("📚 Research Reader")
    st.write("Browse and search research papers extracted from conferences")
    st.divider()
    
    most_recent_conference = db.get_most_recent_conference()
    
    if most_recent_conference:
        col1, col2, col3 = st.columns([4, 1, 1])
        
        with col1:
            st.subheader(f"🎯 {most_recent_conference.upper()} Highlights")
        
        with col2:
            if st.button("✏️ Edit", key="edit_summary_btn", help="Edit summary"):
                if os.getenv("STREAMLIT_SERVER_HEADLESS") == "true":
                    st.warning("📱 Editing is disabled on Streamlit Cloud (read-only mode)")
                else:
                    st.session_state.editing_summary = True
    
        with col3:
            if st.button("🔄 Regenerate", help="Generate new summary"):
                summarizer = get_summarizer()
                with st.spinner("Generating new summary..."):
                    summary = summarizer.get_or_generate_summary(most_recent_conference, force_regenerate=True)
                    if summary:
                        st.success("Summary regenerated!")
                        st.session_state.editing_summary = False
                        st.rerun()
        
        summarizer = get_summarizer()
        summary = summarizer.get_or_generate_summary(most_recent_conference)
        
        if summary:
            if st.session_state.get("editing_summary", False):
                with st.form(key="edit_summary_form"):
                    edited_summary = st.text_area("Edit Summary",
                        value=summary, height=300, label_visibility="collapsed"
                    )
                    
                    col_save, col_cancel = st.columns(2)
                    
                    with col_save:
                        if st.form_submit_button("💾 Save"):
                            if db.save_conference_summary(most_recent_conference, edited_summary, 
                                                        len(db.get_conference_papers(most_recent_conference))):
                                st.success("Summary updated!")
                                st.session_state.editing_summary = False
                                st.rerun()
                            else:
                                st.error("Failed to save summary")
                    
                    with col_cancel:
                        if st.form_submit_button("❌ Cancel"):
                            st.session_state.editing_summary = False
                            st.rerun()
            else:
                with st.container(border=True):
                    st.markdown(summary)
                
                stored = db.get_conference_summary(most_recent_conference)
                if stored:
                    from datetime import datetime
                    gen_date = datetime.fromisoformat(stored['generated_at'])
                    st.caption(f"_Generated on {gen_date.strftime('%Y-%m-%d %H:%M')} from {stored['paper_count']} papers_")
        else:
            st.info("Unable to generate summary. Add more papers with overviews.")
        
        st.divider()
    
    st.subheader("📋 Recent Papers")
    papers = db.get_all_papers()[:10]
    
    if papers:
        for paper in papers:
            with st.container(border=True):
                col_title, col_pdf, col_edit = st.columns([5, 1, 1])
                
                with col_title:
                    st.markdown(f"**{paper.title}**")
                
                with col_pdf:
                    if paper.pdf_found:
                        st.success("📄")
                    else:
                        st.error("❌")
                
                with col_edit:
                    if st.button("✏️", key=f"edit_overview_home_{paper.paper_id}", help="Edit overview"):
                        st.session_state[f"editing_overview_{paper.paper_id}"] = True
                
                st.caption(paper.get_authors_string())
                
                if st.session_state.get(f"editing_overview_{paper.paper_id}", False):
                    with st.form(key=f"edit_overview_form_{paper.paper_id}"):
                        edited_overview = st.text_area(
                            "Edit Overview",
                            value=paper.overview or "",
                            height=200,
                            label_visibility="collapsed"
                        )
                        
                        col_save, col_cancel = st.columns(2)
                        
                        with col_save:
                            if st.form_submit_button("💾 Save"):
                                if db.update_overview(paper.paper_id, edited_overview):
                                    st.success("Overview updated!")
                                    st.session_state[f"editing_overview_{paper.paper_id}"] = False
                                    st.rerun()
                                else:
                                    st.error("Failed to update overview")
                        
                        with col_cancel:
                            if st.form_submit_button("❌ Cancel"):
                                st.session_state[f"editing_overview_{paper.paper_id}"] = False
                                st.rerun()
                else:
                    if paper.overview:
                        st.write(paper.overview[:250] + "..." if len(paper.overview) > 250 else paper.overview)
    else:
        st.info("No papers yet. Run the extraction pipeline:")
        st.code("python scripts/process_conference.py neurips2025", language="bash")

elif page == "📄 Papers":
    st.title("📄 All Papers")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.write("")
    
    with col2:
        if st.button("📥 Download All Missing PDFs", type="primary"):
            if not download_service:
                st.error("⚠️ Download service unavailable on this deployment")
            else:
                with st.spinner("Downloading missing PDFs..."):
                    stats = download_service.download_all_missing()
                
                if stats['success'] > 0:
                    st.success(f"✓ Downloaded {stats['success']} PDF(s) with detailed overviews")
                
                if stats['failed'] > 0:
                    st.warning(f"⚠️ Failed: {stats['failed']} PDF(s)")
                
                if stats['success'] > 0:
                    st.rerun()
    
    st.divider()
    
    papers = db.get_all_papers()
    
    if not papers:
        st.info("No papers found in database.")
    else:
        col1, col2, col3 = st.columns([2, 2, 1])

        with col1:
            conferences = ["All"] + db.get_all_conferences()
            selected_conference = st.selectbox(
                "Conference",
                options=conferences,
                index=0
            )

        with col2:
            pdf_filter = st.checkbox("Show only papers with PDFs", value=False)

        with col3:
            sort_by = st.selectbox(
                "Sort by",
                ["Title (A-Z)", "Title (Z-A)", "Newest First"],
            )

        filtered = papers.copy()

        if selected_conference != "All":
            filtered = [p for p in filtered if p.conference_name == selected_conference]

        if pdf_filter:
            filtered = [p for p in filtered if p.pdf_found]

        if sort_by == "Title (Z-A)":
            filtered.sort(key=lambda p: p.title, reverse=True)
        elif sort_by == "Title (A-Z)":
            filtered.sort(key=lambda p: p.title)
        else:
            filtered.sort(key=lambda p: p.created_at, reverse=True)
    
        st.write(f"**Showing {len(filtered)} paper(s)**")
        st.divider()
        
        for paper in filtered:
            with st.container(border=True):
                col_img, col_title, col_edit = st.columns([0.5, 9, 0.5], vertical_alignment="center")
                
                with col_img:
                    if paper.source_files:
                        # Convert absolute path to relative path for cross-platform compatibility
                        abs_path = Path(paper.source_files[0])
                        # Try to make it relative to project root
                        try:
                            if 'data' in abs_path.parts:
                                # Extract path starting from 'data' directory as string with forward slashes
                                data_idx = abs_path.parts.index('data')
                                rel_path = '/'.join(abs_path.parts[data_idx:])
                            else:
                                rel_path = str(abs_path)
                        except (ValueError, IndexError):
                            rel_path = str(abs_path)
                        
                        # Show button if it's an image file (trust database, check extension only)
                        if rel_path.lower().endswith(('.png', '.jpg', '.jpeg')):
                            if st.button("🖼️", key=f"zoom_{paper.paper_id}", help="Click to view full image"):
                                st.session_state[f"show_image_{paper.paper_id}"] = not st.session_state.get(f"show_image_{paper.paper_id}", False)
                                st.session_state[f"image_path_{paper.paper_id}"] = rel_path
                                st.rerun()
                        else:
                            st.caption("📄")
                    else:
                        st.caption("📄")
                
                with col_title:
                    st.markdown(f"### {paper.title}")
                
                with col_edit:
                    if st.button("✏️", key=f"edit_overview_papers_{paper.paper_id}", help="Edit overview"):
                        if os.getenv("STREAMLIT_SERVER_HEADLESS") == "true":
                            st.warning("📱 Editing is disabled on Streamlit Cloud (read-only mode)")
                        else:
                            st.session_state[f"editing_overview_{paper.paper_id}"] = True
                
                st.caption(f"👥 {paper.get_authors_string()}")
                
                if st.session_state.get(f"show_image_{paper.paper_id}", False):
                    st.divider()
                    # Use stored path from button click
                    image_path = st.session_state.get(f"image_path_{paper.paper_id}")
                    if image_path:
                        try:
                            st.image(image_path, caption=f"Source: {Path(image_path).name}")
                        except Exception as e:
                            st.error(f"Could not load image: {e}")
                            st.caption(f"Path attempted: {image_path}")
                    st.divider()
                
                if st.session_state.get(f"editing_overview_{paper.paper_id}", False):
                    with st.form(key=f"edit_overview_form_papers_{paper.paper_id}"):
                        edited_overview = st.text_area(
                            "Edit Overview",
                            value=paper.overview or "",
                            height=200,
                            label_visibility="collapsed"
                        )
                        
                        col_save, col_cancel = st.columns(2)
                        
                        with col_save:
                            if st.form_submit_button("💾 Save"):
                                if db.update_overview(paper.paper_id, edited_overview):
                                    st.success("Overview updated!")
                                    st.session_state[f"editing_overview_{paper.paper_id}"] = False
                                    st.rerun()
                                else:
                                    st.error("Failed to update overview")
                        
                        with col_cancel:
                            if st.form_submit_button("❌ Cancel"):
                                st.session_state[f"editing_overview_{paper.paper_id}"] = False
                                st.rerun()
                else:
                    if paper.overview:
                        # preview_text = paper.overview[:150]
                        # if len(paper.overview) > 150:
                        #     preview_text += "..."
                        
                        with st.expander("📝 Overview", expanded=False):
                            st.write(paper.overview)
                        
                        # st.caption(preview_text)
                    else:
                        st.caption("_No overview available_")
                    
                col1, col3, col4 = st.columns(3, vertical_alignment="center")
                
                with col1:
                    if paper.pdf_found:
                        st.success("📄 PDF Available")
                    else:
                        st.error("❌ No PDF")
                
                # with col2:
                #     if paper.source_files and os.getenv("STREAMLIT_SERVER_HEADLESS") != "true":
                #         source = Path(paper.source_files[0]).name
                #         st.caption(f"📁 {source}")
                
                with col3:
                    st.caption(f"🕒 {paper.created_at.strftime('%Y-%m-%d')}")
                    
                with col4:
                    if paper.pdf_url:
                        st.link_button("📥", paper.pdf_url, help="Download PDF from arXiv")
                    elif paper.pdf_found and paper.pdf_path:
                        pdf_path = Path(paper.pdf_path)
                        if pdf_path.exists():
                            with open(pdf_path, "rb") as pdf_file:
                                st.download_button(
                                    label="📥",
                                    data=pdf_file,
                                    file_name=pdf_path.name,
                                    mime="application/pdf",
                                    key=f"dl_{paper.paper_id}",
                                    help="Download PDF"
                                )
                        else:
                            col_a, col_b = st.columns(2)
                            with col_a:
                                if st.button("📥 Auto", key=f"download_{paper.paper_id}", help="Download from arXiv"):
                                    if not download_service:
                                        st.error("⚠️ Download service unavailable on this deployment")
                                    else:
                                        with st.spinner("Searching arXiv..."):
                                            conference_name = paper.conference_name or "neurips2025"
                                            success, message = download_service.download_paper(paper, conference_name)
                                        
                                        if success:
                                            st.success(f"✓ {message}")
                                            if "Overview updated" in message:
                                                st.info("📝 Detailed overview extracted from PDF")
                                            st.rerun()
                                        else:
                                            st.error(f"✗ {message}")
                                            st.session_state[f"show_manual_{paper.paper_id}"] = True
                            
                            with col_b:
                                if st.button("🔗 Manual", key=f"manual_{paper.paper_id}", help="Enter arXiv URL"):
                                    st.session_state[f"show_manual_{paper.paper_id}"] = True
                    else:
                        col_a, col_b = st.columns(2)
                        with col_a:
                            if st.button("📥 Auto", key=f"download_{paper.paper_id}", help="Download from arXiv"):
                                if not download_service:
                                    st.error("⚠️ Download service unavailable on this deployment")
                                else:
                                    with st.spinner("Searching arXiv..."):
                                        conference_name = paper.conference_name or "neurips2025"
                                        success, message = download_service.download_paper(paper, conference_name)
                                    
                                    if success:
                                        st.success(f"✓ {message}")
                                        if "Overview updated" in message:
                                            st.info("📝 Detailed overview extracted from PDF")
                                        st.rerun()
                                    else:
                                        st.error(f"✗ {message}")
                                        st.session_state[f"show_manual_{paper.paper_id}"] = True
                        
                        with col_b:
                            if st.button("🔗 Manual", key=f"manual_{paper.paper_id}", help="Enter arXiv URL"):
                                st.session_state[f"show_manual_{paper.paper_id}"] = True
                        
                        if st.session_state.get(f"show_manual_{paper.paper_id}", False):
                            with st.form(key=f"url_form_{paper.paper_id}"):
                                url = st.text_input(
                                    "Enter arXiv URL",
                                    placeholder="https://arxiv.org/abs/2401.12345 or https://arxiv.org/pdf/2401.12345.pdf",
                                    key=f"url_input_{paper.paper_id}"
                                )
                                
                                col_submit, col_cancel = st.columns(2)
                                
                                with col_submit:
                                    submit = st.form_submit_button("Download")
                                
                                with col_cancel:
                                    cancel = st.form_submit_button("Cancel")
                                
                                if submit and url:
                                    if not download_service:
                                        st.error("⚠️ Download service unavailable on this deployment")
                                    else:
                                        with st.spinner("Downloading from URL..."):
                                            conference_name = paper.conference_name or "neurips2025"
                                            success, message = download_service.download_paper_from_url(paper, conference_name, url)
                                        
                                        if success:
                                            st.success(f"✓ {message}")
                                            st.session_state[f"show_manual_{paper.paper_id}"] = False
                                            st.rerun()
                                        else:
                                            st.error(f"✗ {message}")
                                
                                if cancel:
                                    st.session_state[f"show_manual_{paper.paper_id}"] = False
                                    st.rerun()

elif page == "🔍 Search":
    st.title("🔍 Search Papers")
    
    st.caption("Search across titles, authors, and overviews")
    
    query = st.text_input(
        "Search query",
        placeholder="e.g., 'vision transformer', 'Yann LeCun', 'reinforcement learning'...",
    )
    
    if query:
        with st.spinner("Searching..."):
            results = db.search_papers(query)
        
        st.write(f"**Found {len(results)} result(s)**")
        st.divider()
        
        if results:
            for paper in results:
                with st.container(border=True):
                    st.markdown(f"### {paper.title}")
                    st.caption(f"👥 {paper.get_authors_string()}")
                    
                    if paper.overview:
                        st.write(paper.overview)
                    
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        if paper.pdf_found:
                            st.success("📄 PDF Available")
                        else:
                            st.error("❌ No PDF")
                    
                    with col2:
                        if st.button("View Details", key=f"view_details_{paper.paper_id}"):
                            st.session_state.selected_paper_detail = paper.paper_id
                            st.switch_page("pages/paper_detail.py")  # We'll create this
        else:
            st.info("No papers found matching your search.")
    else:
        st.info("💡 Enter a search term to find papers across titles, authors, and content")
        
        with st.expander("🔍 Search Tips"):
            st.markdown("""
            - Search by **title**: "attention is all you need"
            - Search by **author**: "Geoffrey Hinton"
            - Search by **topic**: "graph neural networks"
            - Search in **overview**: "image segmentation"
            
            *Coming soon: LLM-powered semantic search!*
            """)
            
elif page == "📈 Analytics":
    st.title("📈 Analytics")
    
    papers = db.get_all_papers()
    
    if not papers:
        st.info("No papers to analyze yet.")
    else:
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Total Papers", len(papers))
        
        with col2:
            pdf_pct = (stats['papers_with_pdf'] / stats['total_papers'] * 100) if stats['total_papers'] > 0 else 0
            st.metric("PDF Coverage", f"{pdf_pct:.0f}%")
        
        st.divider()
        
        st.subheader("Good things incoming... later!")
        
        # author_counts = {}
        # for paper in papers:
        #     for author in paper.authors:
        #         author_counts[author.name] = author_counts.get(author.name, 0) + 1
        
        # if author_counts:
        #     top_authors = sorted(author_counts.items(), key=lambda x: x[1], reverse=True)[:15]
            
        #     for author, count in top_authors:
        #         col1, col2 = st.columns([3, 1])
        #         with col1:
        #             st.write(author)
        #         with col2:
        #             st.write(f"{count} paper(s)")
        
        # st.divider()
        
        # no_pdf = [p for p in papers if not p.pdf_found]
        # if no_pdf:
        #     st.subheader(f"⚠️ Papers Missing PDFs ({len(no_pdf)})")
        #     for paper in no_pdf[:10]:
        #         st.write(f"• {paper.title}")
