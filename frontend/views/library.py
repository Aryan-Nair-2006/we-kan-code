import streamlit as st
from frontend.components.design import inject_custom_css
from frontend.services.api import list_documents, get_document_status
from frontend.components.ui import render_empty_state

def render_library():
    inject_custom_css()
    
    st.markdown('<div class="tkf-eyebrow">APPROVED KNOWLEDGE</div>', unsafe_allow_html=True)
    st.markdown('<div class="tkf-hero-title">Knowledge Base</div>', unsafe_allow_html=True)
    st.markdown('<div class="tkf-hero-subtitle">Browse, filter, and inspect approved team documents and vector processing states.</div>', unsafe_allow_html=True)
    
    # Top Action Row
    c1, c2 = st.columns([7.5, 2.5])
    with c2:
        if st.button("📤 Upload Document →", type="primary", use_container_width=True):
            st.session_state.current_view = "Upload Documents"
            st.rerun()

    # Search & Filters Card
    st.markdown('<div class="tkf-card">', unsafe_allow_html=True)
    f1, f2, f3, f4 = st.columns(4)
    with f1:
        search_query = st.text_input("Search Documents", placeholder="Filename, category, or owner...", key="lib_search")
    with f2:
        status_filter = st.selectbox("Status", ["All", "READY", "PROCESSING", "FAILED", "PENDING_REVIEW"], key="lib_status")
    with f3:
        access_filter = st.selectbox("Access Level", ["All", "Public", "Team", "Developer", "Admin"], key="lib_access")
    with f4:
        sort_by = st.selectbox("Sort By", ["Newest", "Filename", "Status"], key="lib_sort")
    st.markdown('</div>', unsafe_allow_html=True)

    with st.spinner("Fetching knowledge base documents..."):
        try:
            docs = list_documents()
        except Exception as e:
            st.error(f"Failed to load documents: {e}")
            return

    if not docs:
        render_empty_state("No Documents Added Yet", "Upload your first team document to populate the knowledge base.", "📚")
        return

    # Filter Logic
    filtered = []
    for d in docs:
        fname = str(d.get("filename", "")).lower()
        owner = str(d.get("owner", "")).lower()
        category = str(d.get("category", "")).lower()
        doc_id = str(d.get("document_id", "")).lower()
        
        if search_query:
            sq = search_query.lower()
            if sq not in fname and sq not in owner and sq not in category and sq not in doc_id:
                continue
                
        if status_filter != "All" and str(d.get("status", "")).upper() != status_filter:
            continue
            
        if access_filter != "All" and str(d.get("access_level", "")).lower() != access_filter.lower():
            continue
            
        filtered.append(d)

    # Sort Logic
    if sort_by == "Filename":
        filtered.sort(key=lambda x: str(x.get("filename", "")).lower())
    elif sort_by == "Status":
        filtered.sort(key=lambda x: str(x.get("status", "")))
    
    if not filtered:
        st.info("No documents match your current filter criteria.")
        return

    st.markdown(f'<div style="font-size: 0.88rem; color: var(--tkf-text-muted); margin: 1rem 0 0.75rem 0;">Showing {len(filtered)} document(s)</div>', unsafe_allow_html=True)

    for doc in filtered:
        status_raw = str(doc.get("status", "unknown")).lower()
        if status_raw == "ready":
            badge = '<span class="badge ready">READY</span>'
        elif status_raw in ["processing", "uploaded"]:
            badge = '<span class="badge processing">PROCESSING</span>'
        else:
            badge = '<span class="badge failed">FAILED</span>'

        filename = doc.get("filename", "Unknown")
        ext = filename.split(".")[-1].lower() if "." in filename else ""
        icon_map = {"pdf": "📄", "docx": "📝", "txt": "📃", "xlsx": "📊", "csv": "🔢", "pptx": "📽️"}
        icon = icon_map.get(ext, "📄")
        
        chunks = doc.get("chunk_count", 0)
        chunk_text = f"{chunks} Chunks" if chunks else "0 Chunks"
        doc_id = doc.get("document_id", "Unknown ID")
        
        with st.expander(f"{icon}  {filename}  —  {doc.get('category', 'General')}  |  v{doc.get('version', '1.0')}"):
            st.markdown(f"""
            <div style="background: var(--tkf-surface-2); padding: 1rem; border-radius: 8px; border: 1px solid var(--tkf-border); margin-bottom: 1rem;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;">
                    <div>
                        <div style="font-weight: 700; font-size: 1.1rem; color: var(--tkf-text-primary);">{filename}</div>
                        <div style="font-size: 0.82rem; color: var(--tkf-text-muted);">Document ID: {doc_id}</div>
                    </div>
                    <div>{badge}</div>
                </div>
                <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; font-size: 0.88rem; color: var(--tkf-text-secondary);">
                    <div>👤 <strong>Owner:</strong> {doc.get('owner', 'Team')}</div>
                    <div>🏷️ <strong>Category:</strong> {doc.get('category', 'General')}</div>
                    <div>🔖 <strong>Version:</strong> v{doc.get('version', '1.0')}</div>
                    <div>🔒 <strong>Access:</strong> {str(doc.get('access_level', 'Team')).capitalize()}</div>
                    <div>📑 <strong>Chunks:</strong> {chunk_text}</div>
                    <div>🕒 <strong>Created:</strong> {str(doc.get('created_at', 'N/A'))[:10]}</div>
                    <div>🔄 <strong>Updated:</strong> {str(doc.get('updated_at', 'N/A'))[:10]}</div>
                    <div>📦 <strong>S3 Key:</strong> {doc.get('s3_key') or 'Local'}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Processing Stage Timeline
            st.markdown('<div style="font-size: 0.85rem; font-weight: 600; color: var(--tkf-text-muted); margin-bottom: 0.5rem;">PROCESSING TIMELINE</div>', unsafe_allow_html=True)
            if status_raw == "ready":
                timeline_html = """
                <div style="display: flex; gap: 8px; align-items: center; font-size: 0.85rem; color: var(--tkf-success);">
                    <span>✓ Uploaded</span> → <span>✓ Extracted</span> → <span>✓ Embedded (Titan 1536d)</span> → <span>✓ Vector Indexed (OpenSearch)</span>
                </div>
                """
            elif status_raw in ["processing", "uploaded"]:
                timeline_html = """
                <div style="display: flex; gap: 8px; align-items: center; font-size: 0.85rem; color: var(--tkf-warning);">
                    <span>✓ Uploaded</span> → <span>⏳ Extracting Chunks</span> → <span>⏳ Generating Embeddings</span> → <span>⏳ Indexing</span>
                </div>
                """
            else:
                err_msg = doc.get("processing_error") or "Failed to process document"
                timeline_html = f"""
                <div style="color: var(--tkf-error); font-size: 0.85rem;">
                    ✖ Processing Error: {err_msg}
                </div>
                """
            st.markdown(timeline_html, unsafe_allow_html=True)
