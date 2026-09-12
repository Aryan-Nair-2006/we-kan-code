import streamlit as st
from frontend.components.design import inject_custom_css
from frontend.services.api import query_knowledge, list_documents, list_reviews
from frontend.components.ui import render_answer

def render_home():
    inject_custom_css()
    
    if "run_query" not in st.session_state:
        st.session_state.run_query = None
        
    st.markdown('<div class="tkf-eyebrow">TEAM KNOWLEDGE FINDER</div>', unsafe_allow_html=True)
    st.markdown('<div class="tkf-hero-title">Find Reliable Project Knowledge Faster</div>', unsafe_allow_html=True)
    st.markdown('<div class="tkf-hero-subtitle">Ask questions across approved team documents and verify every answer with evidence.</div>', unsafe_allow_html=True)
    
    # Question Composer Container
    st.markdown('<div class="tkf-card">', unsafe_allow_html=True)
    
    question_input = st.text_input(
        "Ask a Question",
        placeholder="🔍 Ask anything about your team's documents (e.g. How is authentication handled?)...",
        label_visibility="collapsed",
        key="home_question_input"
    )
    
    c_btn, _ = st.columns([2.5, 7.5])
    with c_btn:
        if st.button("Ask Knowledge →", type="primary", use_container_width=True, key="home_ask_btn"):
            if question_input and question_input.strip():
                st.session_state.run_query = question_input.strip()
                st.rerun()
                
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Suggested Question Pills
    st.markdown('<div style="font-size: 0.85rem; color: var(--tkf-text-muted); margin-bottom: 0.5rem; font-weight: 500;">SUGGESTED QUESTIONS:</div>', unsafe_allow_html=True)
    sug_cols = st.columns(4)
    suggestions = [
        "How is authentication configured?",
        "What database is used for metadata?",
        "What are our deployment steps?",
        "What vector dimension is indexed?"
    ]
    for col, sug in zip(sug_cols, suggestions):
        with col:
            if st.button(f"💡 {sug}", key=f"sug_{sug}", use_container_width=True, type="secondary"):
                st.session_state.run_query = sug
                st.rerun()
                
    st.markdown("<br>", unsafe_allow_html=True)

    if question_input and question_input != st.session_state.run_query and question_input.strip() != "":
        st.session_state.run_query = question_input.strip()

    # --- QUERY RESULTS STATE ---
    if st.session_state.run_query:
        st.markdown("<hr style='border-color: var(--tkf-border); margin: 2rem 0;'>", unsafe_allow_html=True)
        with st.spinner("Searching approved knowledge base..."):
            result = query_knowledge(st.session_state.run_query)
            if "error" in result:
                st.error(f"Error querying knowledge base: {result['error']}")
            else:
                render_answer(st.session_state.run_query, result)
        
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("← Back to Overview Dashboard", key="back_to_dash"):
            st.session_state.run_query = None
            st.rerun()
            
    # --- DEFAULT OVERVIEW DASHBOARD STATE ---
    else:
        # Fetch Real Backend Data
        try:
            docs = list_documents()
            total_docs = len(docs)
            ready_docs = sum(1 for d in docs if str(d.get("status", "")).lower() == "ready")
            processing_docs = sum(1 for d in docs if str(d.get("status", "")).lower() in ["uploaded", "processing"])
            total_chunks = sum(int(d.get("chunk_count", 0)) for d in docs if d.get("chunk_count") is not None)
        except Exception:
            docs = []
            total_docs, ready_docs, processing_docs, total_chunks = 0, 0, 0, 0
            
        try:
            reviews = list_reviews(status="Pending")
            needs_review_count = len(reviews)
        except Exception:
            needs_review_count = 0
            
        # KPI Metric Cards
        m1, m2, m3, m4, m5 = st.columns(5)
        with m1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-icon">📄</div>
                <div>
                    <div class="metric-value">{total_docs}</div>
                    <div class="metric-label">Documents</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        with m2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-icon" style="color: var(--tkf-success);">✓</div>
                <div>
                    <div class="metric-value" style="color: var(--tkf-success);">{ready_docs}</div>
                    <div class="metric-label">Ready</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        with m3:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-icon" style="color: var(--tkf-warning);">⏳</div>
                <div>
                    <div class="metric-value" style="color: var(--tkf-warning);">{processing_docs}</div>
                    <div class="metric-label">Processing</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        with m4:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-icon" style="color: var(--tkf-error);">🚩</div>
                <div>
                    <div class="metric-value" style="color: var(--tkf-error);">{needs_review_count}</div>
                    <div class="metric-label">Needs Review</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        with m5:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-icon" style="color: var(--tkf-cyan);">📑</div>
                <div>
                    <div class="metric-value" style="color: var(--tkf-cyan);">{total_chunks}</div>
                    <div class="metric-label">Chunks</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Recent Documents & Quick Actions Grid
        d_col, q_col = st.columns([2.2, 1])
        
        with d_col:
            st.markdown('<div class="tkf-section-title">📂 Recent Documents</div>', unsafe_allow_html=True)
            if not docs:
                st.info("No approved documents uploaded yet. Add your first document to get started!")
            else:
                for doc in docs[:4]:
                    status = str(doc.get("status", "unknown")).lower()
                    if status == "ready":
                        badge = '<span class="badge ready">READY</span>'
                    elif status in ["processing", "uploaded"]:
                        badge = '<span class="badge processing">PROCESSING</span>'
                    else:
                        badge = '<span class="badge failed">FAILED</span>'
                        
                    filename = doc.get("filename", "Document")
                    ext = filename.split(".")[-1].lower() if "." in filename else ""
                    icon_map = {"pdf": "📄", "docx": "📝", "txt": "📃", "xlsx": "📊", "csv": "🔢", "pptx": "📽️"}
                    icon = icon_map.get(ext, "📄")
                    
                    st.markdown(f"""
                    <div style="background: var(--tkf-card); border: 1px solid var(--tkf-border); border-radius: var(--tkf-radius-sm); padding: 0.95rem 1.25rem; margin-bottom: 0.6rem; display: flex; justify-content: space-between; align-items: center;">
                        <div style="display: flex; gap: 1rem; align-items: center;">
                            <div style="font-size: 1.6rem;">{icon}</div>
                            <div>
                                <div style="font-weight: 600; font-size: 0.98rem; color: var(--tkf-text-primary);">{filename}</div>
                                <div style="font-size: 0.82rem; color: var(--tkf-text-muted); margin-top: 2px;">
                                    Owner: {doc.get('owner', 'Team')} · v{doc.get('version', '1.0')} · Access: {str(doc.get('access_level', 'Team')).capitalize()}
                                </div>
                            </div>
                        </div>
                        <div>{badge}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
        with q_col:
            st.markdown('<div class="tkf-section-title">⚡ Quick Actions</div>', unsafe_allow_html=True)
            st.markdown('<div class="tkf-card">', unsafe_allow_html=True)
            if st.button("💬 Ask Knowledge Question", use_container_width=True, type="primary"):
                st.session_state.current_view = "Ask Knowledge"
                st.rerun()
            st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
            if st.button("📤 Upload New Document", use_container_width=True, type="secondary"):
                st.session_state.current_view = "Upload Documents"
                st.rerun()
            st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
            if st.button("📚 Browse Knowledge Base", use_container_width=True, type="secondary"):
                st.session_state.current_view = "Knowledge Base"
                st.rerun()
            st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
            if st.button("📊 View Knowledge Analytics", use_container_width=True, type="secondary"):
                st.session_state.current_view = "Analytics"
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
