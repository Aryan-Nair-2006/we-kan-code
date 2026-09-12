import streamlit as st
import pandas as pd
from frontend.components.design import inject_custom_css
from frontend.services.api import get_analytics, list_documents, list_reviews
from frontend.components.ui import render_empty_state

def render_analytics():
    inject_custom_css()
    
    st.markdown('<div class="tkf-eyebrow">METRICS & HEALTH</div>', unsafe_allow_html=True)
    st.markdown('<div class="tkf-hero-title">Knowledge Analytics</div>', unsafe_allow_html=True)
    st.markdown('<div class="tkf-hero-subtitle">Real-time metrics on your team\'s knowledge base coverage, indexing progress, and vector health.</div>', unsafe_allow_html=True)
    
    with st.spinner("Loading analytics metrics..."):
        analytics_data = get_analytics()
        
    if "error" in analytics_data:
        st.error(f"Failed to load analytics: {analytics_data['error']}")
        return
        
    total_docs = analytics_data.get("total_documents", 0)
    
    if total_docs == 0:
        render_empty_state(
            title="No Analytics Data Yet",
            description="Upload documents to generate real-time metrics on document coverage, file types, and knowledge health.",
            icon="📊"
        )
        if st.button("📤 Upload First Document", type="primary", key="an_upload_btn"):
            st.session_state.current_view = "Upload Documents"
            st.rerun()
        return
        
    # Overview Metric Cards
    m1, m2, m3, m4, m5 = st.columns(5)
    with m1:
        st.markdown(f"""
        <div class="metric-card">
            <div>
                <div class="metric-value">{total_docs}</div>
                <div class="metric-label">Total Documents</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    with m2:
        st.markdown(f"""
        <div class="metric-card">
            <div>
                <div class="metric-value" style="color: var(--tkf-success);">{analytics_data.get("ready_documents", 0)}</div>
                <div class="metric-label">Ready for Search</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    with m3:
        st.markdown(f"""
        <div class="metric-card">
            <div>
                <div class="metric-value" style="color: var(--tkf-warning);">{analytics_data.get("processing_documents", 0)}</div>
                <div class="metric-label">Processing</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    with m4:
        st.markdown(f"""
        <div class="metric-card">
            <div>
                <div class="metric-value" style="color: var(--tkf-error);">{analytics_data.get("failed_documents", 0)}</div>
                <div class="metric-label">Failed Ingestion</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    with m5:
        st.markdown(f"""
        <div class="metric-card">
            <div>
                <div class="metric-value" style="color: var(--tkf-cyan);">{analytics_data.get("total_chunks", 0)}</div>
                <div class="metric-label">Indexed Chunks</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Knowledge Health Summary Box
    ready_cnt = analytics_data.get("ready_documents", 0)
    success_rate = (ready_cnt / total_docs * 100) if total_docs > 0 else 0.0
    
    st.markdown('<div class="tkf-section-title">🏥 Knowledge Base Health</div>', unsafe_allow_html=True)
    st.markdown(f"""
    <div class="tkf-card" style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 1.5rem; text-align: center;">
        <div>
            <div style="font-size: 1.6rem; font-weight: 700; color: var(--tkf-success);">{success_rate:.1f}%</div>
            <div style="font-size: 0.82rem; color: var(--tkf-text-muted); font-weight: 600; text-transform: uppercase;">Processing Success Rate</div>
        </div>
        <div>
            <div style="font-size: 1.6rem; font-weight: 700; color: var(--tkf-cyan);">Titan 1536d</div>
            <div style="font-size: 0.82rem; color: var(--tkf-text-muted); font-weight: 600; text-transform: uppercase;">Embedding Model</div>
        </div>
        <div>
            <div style="font-size: 1.6rem; font-weight: 700; color: var(--tkf-orange);">OpenSearch HNSW</div>
            <div style="font-size: 0.82rem; color: var(--tkf-text-muted); font-weight: 600; text-transform: uppercase;">Vector Index</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Breakdown Charts Grid
    chart_col1, chart_col2 = st.columns(2)
    
    with chart_col1:
        st.markdown('<div class="tkf-section-title">Documents by Category</div>', unsafe_allow_html=True)
        st.markdown('<div class="tkf-card">', unsafe_allow_html=True)
        categories = analytics_data.get("by_category", {})
        if categories:
            df_cat = pd.DataFrame(list(categories.items()), columns=["Category", "Count"])
            st.bar_chart(df_cat.set_index("Category"), color="#F97316")
        else:
            st.write("No category data available.")
        st.markdown('</div>', unsafe_allow_html=True)
        
    with chart_col2:
        st.markdown('<div class="tkf-section-title">Documents by Access Level</div>', unsafe_allow_html=True)
        st.markdown('<div class="tkf-card">', unsafe_allow_html=True)
        access_levels = analytics_data.get("by_access_level", {})
        if access_levels:
            df_access = pd.DataFrame(list(access_levels.items()), columns=["Access Level", "Count"])
            st.bar_chart(df_access.set_index("Access Level"), color="#38BDF8")
        else:
            st.write("No access level data available.")
        st.markdown('</div>', unsafe_allow_html=True)
        
    st.markdown("<br>", unsafe_allow_html=True)
    
    st.markdown('<div class="tkf-section-title">Documents by File Type</div>', unsafe_allow_html=True)
    st.markdown('<div class="tkf-card">', unsafe_allow_html=True)
    file_types = analytics_data.get("by_file_type", {})
    if file_types:
        df_types = pd.DataFrame(list(file_types.items()), columns=["File Type", "Count"])
        st.bar_chart(df_types.set_index("File Type"), color="#22C55E")
    else:
        st.write("No file type data available.")
    st.markdown('</div>', unsafe_allow_html=True)
