import streamlit as st
from frontend.components.design import inject_custom_css

def render_settings():
    inject_custom_css()
    
    st.markdown('<div class="eyebrow">MANAGEMENT</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-title">Settings</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-subtitle">Manage application preferences.</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="tkf-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Application</div>', unsafe_allow_html=True)
    st.markdown('<div style="font-size: 0.95rem; color: var(--tkf-ink-soft); margin-bottom: 1rem;">Customize your local experience.</div>', unsafe_allow_html=True)
    
    st.checkbox("Show detailed source metadata on Ask page", value=True)
    st.checkbox("Use compact document cards in Library", value=False)
    
    st.markdown('<div class="section-title" style="margin-top: 2rem;">About</div>', unsafe_allow_html=True)
    st.markdown('<div style="font-size: 0.95rem; color: var(--tkf-ink-soft); margin-bottom: 1rem;">Team Knowledge Finder v1.5.0<br>Powered by AWS Bedrock & OpenSearch Serverless</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
