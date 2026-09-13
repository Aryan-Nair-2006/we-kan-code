import sys
from pathlib import Path

# Ensure root directory is on sys.path so 'frontend' and 'backend' packages are importable
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import streamlit as st

# 1. Configure page settings (using expanded sidebar state for full shell experience)
st.set_page_config(
    page_title="Team Knowledge Finder",
    page_icon="💡",
    layout="wide",
    initial_sidebar_state="expanded"
)

from frontend.components.design import inject_custom_css
from frontend.services.api import check_health, get_auth_me
from frontend.services.auth_service import login_with_cognito, login_local
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
    """Renders the sidebar navigation shell with real system status and authentication controls."""
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

        st.markdown("<hr style='border-color: var(--tkf-border); margin: 1.25rem 0;'>", unsafe_allow_html=True)

        # -------------------------------------------------------------------
        # Phase 8: Authentication / Cognito Identity Widget
        # -------------------------------------------------------------------
        auth_token = st.session_state.get("auth_token")
        username = st.session_state.get("username", "Guest")
        role = st.session_state.get("user_role", "public")
        
        if auth_token:
            role_badge_bg = "rgba(59, 130, 246, 0.15)" if role in ("developer", "admin") else "rgba(100, 116, 139, 0.15)"
            role_badge_color = "#60a5fa" if role in ("developer", "admin") else "#94a3b8"
            
            st.markdown(f"""
            <div style="background: var(--tkf-surface-2); border: 1px solid var(--tkf-border); border-radius: var(--tkf-radius-sm); padding: 0.85rem; margin-bottom: 1rem;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                    <span style="font-weight: 700; font-size: 0.82rem; color: var(--tkf-text-primary);">👤 {username}</span>
                    <span style="background: {role_badge_bg}; color: {role_badge_color}; font-size: 0.72rem; padding: 2px 8px; border-radius: 12px; font-weight: 700; text-transform: uppercase;">{role}</span>
                </div>
                <div style="font-size: 0.75rem; color: var(--tkf-text-muted);">Cognito Authenticated Session</div>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("🚪 Sign Out", key="auth_sign_out_btn", use_container_width=True, type="secondary"):
                st.session_state.pop("auth_token", None)
                st.session_state.pop("id_token", None)
                st.session_state.pop("username", None)
                st.session_state.pop("user_role", None)
                st.rerun()
        else:
            with st.expander("🔐 Sign In / Cognito", expanded=False):
                login_mode = st.radio("Mode", ["Cognito User Pool", "Local Dev Role"], horizontal=True, label_visibility="collapsed", key="auth_login_mode")
                
                if login_mode == "Cognito User Pool":
                    c_user = st.text_input("Username / Email", key="cognito_user_input")
                    c_pass = st.text_input("Password", type="password", key="cognito_pass_input")
                    if st.button("Sign In with Cognito", key="cognito_submit_btn", use_container_width=True, type="primary"):
                        if c_user and c_pass:
                            with st.spinner("Authenticating with AWS Cognito..."):
                                res = login_with_cognito(c_user, c_pass)
                                if res.get("success"):
                                    st.session_state.auth_token = res.get("id_token") or res.get("access_token")
                                    st.session_state.id_token = res.get("id_token")
                                    st.session_state.username = res.get("username")
                                    st.session_state.user_role = res.get("role")
                                    st.success(f"Signed in as {res.get('username')}")
                                    st.rerun()
                                else:
                                    st.error(res.get("error", "Sign in failed"))
                        else:
                            st.warning("Please enter username and password")
                else:
                    dev_name = st.text_input("Username", value="dev-tester", key="local_user_input")
                    dev_role = st.selectbox("Role", ["admin", "developer", "team", "public"], index=1, key="local_role_select")
                    if st.button("Set Dev Identity", key="local_submit_btn", use_container_width=True, type="secondary"):
                        res = login_local(dev_name, dev_role)
                        st.session_state.auth_token = res["id_token"]
                        st.session_state.username = res["username"]
                        st.session_state.user_role = res["role"]
                        st.success(f"Identity set to {dev_name} ({dev_role})")
                        st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)
        
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
