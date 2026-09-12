import streamlit as st
from frontend.components.design import inject_custom_css
from frontend.services.api import list_reviews, update_review_status
from frontend.components.ui import render_empty_state

def render_review():
    inject_custom_css()
    
    st.markdown('<div class="tkf-eyebrow">QUALITY ASSURANCE</div>', unsafe_allow_html=True)
    st.markdown('<div class="tkf-hero-title">Review Queue</div>', unsafe_allow_html=True)
    st.markdown('<div class="tkf-hero-subtitle">Review knowledge quality flags, investigate reported inaccuracies, and approve or reject content updates.</div>', unsafe_allow_html=True)
    
    # Filter Controls
    st.markdown('<div class="tkf-card">', unsafe_allow_html=True)
    status_filter = st.selectbox("Filter by Status", ["All", "Pending", "Under Review", "Resolved", "Rejected"], key="rev_status_filter")
    st.markdown('</div>', unsafe_allow_html=True)

    with st.spinner("Fetching flagged review items..."):
        reviews = list_reviews(status=status_filter)

    if not reviews:
        render_empty_state(
            title="No Items in Review Queue",
            description="When users flag answers or report outdated document passages, they will appear here for team review.",
            icon="✓"
        )
        return

    st.markdown(f'<div style="font-size: 0.88rem; color: var(--tkf-text-muted); margin-bottom: 1rem;">Showing {len(reviews)} flagged item(s)</div>', unsafe_allow_html=True)

    for item in reviews:
        flag_id = item.get("flag_id", "FLAG-UNKNOWN")
        status = item.get("status", "Pending")
        reason = item.get("reason", "Reported Issue")
        details = item.get("details", "")
        question = item.get("question", "")
        answer = item.get("answer", "")
        src_file = item.get("source_filename", "Unknown Document")
        passage = item.get("supporting_passage", "")
        created_at = item.get("created_at", "")[:19].replace("T", " ")
        
        status_color = {
            "Pending": "var(--tkf-error)",
            "Under Review": "var(--tkf-warning)",
            "Resolved": "var(--tkf-success)",
            "Rejected": "var(--tkf-text-muted)"
        }.get(status, "var(--tkf-cyan)")
        
        st.markdown(f"""
        <div class="tkf-card" style="border-left: 4px solid {status_color}; margin-bottom: 1.2rem;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <span style="font-weight: 700; color: var(--tkf-text-primary); font-size: 1rem;">🚩 {flag_id}</span>
                    <span style="font-size: 0.8rem; color: var(--tkf-orange); font-weight: 600; background: var(--tkf-orange-glow); padding: 2px 8px; border-radius: 4px;">{reason}</span>
                </div>
                <div style="font-size: 0.8rem; color: {status_color}; font-weight: 700; border: 1px solid {status_color}; padding: 2px 10px; border-radius: 12px;">
                    {status.upper()}
                </div>
            </div>
            
            <div style="font-size: 0.85rem; color: var(--tkf-text-muted); margin-bottom: 0.75rem;">Reported at: {created_at}</div>
            
            <div style="background: var(--tkf-surface-2); padding: 0.85rem; border-radius: 6px; margin-bottom: 0.75rem; border: 1px solid var(--tkf-border);">
                <div style="font-size: 0.82rem; font-weight: 600; color: var(--tkf-text-muted);">QUESTION</div>
                <div style="font-weight: 600; color: var(--tkf-text-primary); margin-bottom: 0.5rem;">{question or "N/A"}</div>
                
                <div style="font-size: 0.82rem; font-weight: 600; color: var(--tkf-text-muted);">GENERATED ANSWER</div>
                <div style="font-size: 0.92rem; color: var(--tkf-text-secondary);">{answer or "N/A"}</div>
            </div>
            
            {f'<div style="font-size: 0.9rem; color: var(--tkf-warning); margin-bottom: 0.75rem;"><strong>Reporter Note:</strong> {details}</div>' if details else ''}
            
            <div style="font-size: 0.83rem; color: var(--tkf-text-secondary); margin-bottom: 0.75rem;">
                <strong>Source File:</strong> {src_file}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Action Buttons for Pending/Under Review items
        b_col1, b_col2, b_col3, _ = st.columns([1.5, 1.5, 1.5, 4.5])
        with b_col1:
            if st.button("✓ Resolve", key=f"rev_resolve_{flag_id}", type="primary", use_container_width=True):
                update_review_status(flag_id, "Resolved", reviewer="Admin")
                st.toast(f"Flag {flag_id} marked as Resolved", icon="✓")
                st.rerun()
        with b_col2:
            if st.button("👀 Reviewing", key=f"rev_under_{flag_id}", use_container_width=True):
                update_review_status(flag_id, "Under Review", reviewer="Admin")
                st.toast(f"Flag {flag_id} set to Under Review", icon="👀")
                st.rerun()
        with b_col3:
            if st.button("✖ Reject Flag", key=f"rev_reject_{flag_id}", use_container_width=True):
                update_review_status(flag_id, "Rejected", reviewer="Admin")
                st.toast(f"Flag {flag_id} Rejected", icon="✖")
                st.rerun()
