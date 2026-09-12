import streamlit as st

# 1. Configure page settings (using expanded sidebar state for full shell experience)
st.set_page_config(
    page_title="Team Knowledge Finder",
    page_icon="💡",
    layout="wide",
    initial_sidebar_state="expanded"
)

from frontend.components.design import inject_custom_css
from frontend.services.api import check_health
from frontend.views.home import render_home
from frontend.views.library import render_library
from frontend.views.upload import render_upload
from frontend.views.review import render_review
from frontend.views.analytics import render_analytics

# Available views mapping
VIEWS = {
    "Overview": render_home,
    "Ask Knowledge": render_home, 
    "Knowledge Base": render_library,
    "Upload Documents": render_upload,
    "Analytics": render_analytics,
    "Review Queue": render_review
}

def render_sidebar():
    """Renders the sidebar navigation shell with real system status."""
    with st.sidebar:
        st.markdown("""
        <div style="padding: 0.5rem 0 1.5rem 0; border-bottom: 1px solid var(--tkf-border); margin-bottom: 1rem;">
            <div style="font-weight: 800; font-size: 1.15rem; color: var(--tkf-text-primary); letter-spacing: 0.5px; display: flex; align-items: center; gap: 8px;">
                <span style="color: var(--tkf-orange);">💡</span> KNOWLEDGE FINDER
            </div>
            <div style="font-size: 0.78rem; color: var(--tkf-text-muted); margin-top: 2px;">Team Knowledge Assistant</div>
        </div>
        """, unsafe_allow_html=True)
        
        current = st.session_state.get("current_view", "Overview")
        
        nav_items = [
            ("Overview", "🏠"),
            ("Ask Knowledge", "💬"),
            ("Knowledge Base", "📚"),
            ("Upload Documents", "📤"),
            ("Analytics", "📊"),
            ("Review Queue", "🚩")
        ]
        
        for name, icon in nav_items:
            is_active = (current == name)
            btn_label = f"{icon}  {name}"
            
            if st.button(btn_label, key=f"side_nav_{name}", use_container_width=True, type="primary" if is_active else "secondary"):
                st.session_state.current_view = name
                st.rerun()

        st.markdown("<br><br>", unsafe_allow_html=True)
        
        # System Health Status Widget in Sidebar
        health = check_health()
        is_online = ("error" not in health and health.get("status") == "ok")
        status_color = "var(--tkf-success)" if is_online else "var(--tkf-warning)"
        status_text = "Connected" if is_online else "Local Mode"
        
        st.markdown(f"""
        <div style="background: var(--tkf-surface-2); border: 1px solid var(--tkf-border); border-radius: var(--tkf-radius-sm); padding: 0.85rem; font-size: 0.82rem;">
            <div style="font-weight: 700; color: var(--tkf-text-secondary); margin-bottom: 0.5rem; display: flex; justify-content: space-between; align-items: center;">
                <span>SYSTEM STATUS</span>
                <span style="color: {status_color}; font-size: 0.75rem;">● {status_text}</span>
            </div>
            <div style="color: var(--tkf-text-muted); display: flex; flex-direction: column; gap: 4px;">
                <div>• Storage: <span style="color: var(--tkf-text-secondary);">{status_text}</span></div>
                <div>• Vector Search: <span style="color: var(--tkf-text-secondary);">{status_text}</span></div>
                <div>• AI Model: <span style="color: var(--tkf-text-secondary);">{status_text}</span></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

def render_top_header():
    """Renders the top application header."""
    health = check_health()
    is_online = ("error" not in health and health.get("status") == "ok")
    badge_bg = "rgba(34, 197, 94, 0.12)" if is_online else "rgba(245, 158, 11, 0.12)"
    badge_border = "rgba(34, 197, 94, 0.3)" if is_online else "rgba(245, 158, 11, 0.3)"
    badge_color = "var(--tkf-success)" if is_online else "var(--tkf-warning)"
    badge_text = "Knowledge Base Online" if is_online else "Local Development Mode"
    
    st.markdown(f"""
    <div style="display: flex; justify-content: space-between; align-items: center; padding-bottom: 1rem; border-bottom: 1px solid var(--tkf-border); margin-bottom: 1.5rem;">
        <div>
            <div style="font-size: 1.6rem; font-weight: 800; color: var(--tkf-text-primary); letter-spacing: -0.5px;">
                TEAM KNOWLEDGE FINDER
            </div>
            <div style="font-size: 0.92rem; color: var(--tkf-text-secondary); margin-top: 2px;">
                Trusted knowledge. Grounded answers.
            </div>
        </div>
        <div style="background: {badge_bg}; border: 1px solid {badge_border}; color: {badge_color}; padding: 6px 14px; border-radius: 20px; font-size: 0.82rem; font-weight: 700; display: flex; align-items: center; gap: 8px;">
            <span>●</span> {badge_text}
        </div>
    </div>
    """, unsafe_allow_html=True)

def main():
    inject_custom_css()
    
    if 'current_view' not in st.session_state:
        st.session_state.current_view = "Overview"

    # Render Sidebar Shell
    render_sidebar()
    
    # Render Header
    render_top_header()
    
    # Render Main View Content
    view_func = VIEWS.get(st.session_state.current_view, render_home)
    view_func()
    
    # Footer
    st.markdown("""
        <div style="text-align: center; margin-top: 4rem; padding-bottom: 2rem; color: var(--tkf-text-muted); font-size: 0.82rem; border-top: 1px solid var(--tkf-border); padding-top: 1.5rem;">
            Team Knowledge Finder · Source-grounded AI knowledge platform · Powered by AWS Bedrock & OpenSearch
        </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
