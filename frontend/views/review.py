import streamlit as st
from frontend.components.design import inject_custom_css
from frontend.components.ui import render_empty_state
from frontend.services.api import list_reviews, resolve_review


def render_review():
    inject_custom_css()
    
    st.markdown('<div class="tkf-eyebrow">QUALITY ASSURANCE & MANAGEMENT</div>', unsafe_allow_html=True)
    st.markdown('<div class="tkf-hero-title">Review &amp; Feedback Queue</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="tkf-hero-subtitle">Review knowledge quality flags, investigate reported inaccuracies or outdated documents, and take resolution actions.</div>',
        unsafe_allow_html=True,
    )

    tab_open, tab_resolved = st.tabs(["🚩 Open Flags", "✓ Resolved Flags"])

    with tab_open:
        with st.spinner("Fetching open review items..."):
            open_flags = list_reviews(status="OPEN")
            
        if not open_flags:
            render_empty_state(
                title="No Items in Review Queue",
                description="When users flag answers or report outdated document passages, they will appear here for team review.",
                icon="✓"
            )
        else:
            st.markdown(f'<div style="font-size: 0.88rem; color: var(--tkf-text-muted); margin-bottom: 1rem;">Showing {len(open_flags)} open flagged item(s)</div>', unsafe_allow_html=True)
            for flag in open_flags:
                flag_id = flag.get("flag_id", "FLAG-UNKNOWN")
                doc_id = flag.get("document_id", "DOC-UNKNOWN")
                chunk_id = flag.get("chunk_id")
                reason = flag.get("reason", "Reported Issue")
                flagged_by = flag.get("flagged_by", "anonymous")
                created_at = flag.get("created_at", "")[:19].replace("T", " ")
                
                question = flag.get("question")
                answer = flag.get("answer")
                details = flag.get("details")
                src_filename = flag.get("source_filename")
                passage = flag.get("supporting_passage")

                with st.container(border=True):
                    st.markdown(f"""
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                        <div style="display: flex; align-items: center; gap: 10px;">
                            <span style="font-weight: 700; color: var(--tkf-text-primary); font-size: 1rem;">🚩 {flag_id}</span>
                            <span style="font-size: 0.8rem; color: var(--tkf-orange); font-weight: 600; background: var(--tkf-orange-glow); padding: 2px 8px; border-radius: 4px;">{reason}</span>
                        </div>
                        <div style="font-size: 0.78rem; color: var(--tkf-error); font-weight: 700; border: 1px solid var(--tkf-error); padding: 2px 8px; border-radius: 12px;">
                            OPEN
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    st.markdown(f"**Document ID:** `{doc_id}`" + (f"  ·  **Chunk ID:** `{chunk_id}`" if chunk_id else "") + (f"  ·  **Source:** {src_filename}" if src_filename else ""))
                    st.caption(f"Flagged by: **{flagged_by}** · Reported at: {created_at}")

                    if question or answer:
                        st.markdown(f"""
                        <div style="background: var(--tkf-surface-2); padding: 0.85rem; border-radius: 6px; margin: 0.75rem 0; border: 1px solid var(--tkf-border);">
                            {f'<div style="font-size: 0.8rem; font-weight: 600; color: var(--tkf-text-muted);">QUESTION</div><div style="font-weight: 600; color: var(--tkf-text-primary); margin-bottom: 0.5rem;">{question}</div>' if question else ''}
                            {f'<div style="font-size: 0.8rem; font-weight: 600; color: var(--tkf-text-muted);">GENERATED ANSWER</div><div style="font-size: 0.92rem; color: var(--tkf-text-secondary); margin-bottom: 0.5rem;">{answer}</div>' if answer else ''}
                            {f'<div style="font-size: 0.85rem; color: var(--tkf-warning);"><strong>Reporter Notes:</strong> {details}</div>' if details else ''}
                        </div>
                        """, unsafe_allow_html=True)

                    if passage:
                        with st.expander("📄 View Supporting Evidence Passage"):
                            st.write(passage)

                    col1, col2, col3, col4 = st.columns([1.5, 1.2, 1.5, 2.5])
                    reviewer = col4.text_input("Reviewer", value="Admin", key=f"rev_name_{flag_id}", label_visibility="collapsed")
                    
                    if col1.button("✓ Mark Corrected", key=f"rev_corr_{flag_id}", type="primary", use_container_width=True):
                        result = resolve_review(flag_id, "CORRECTED", reviewer=reviewer)
                        _show_result(result, flag_id)
                    if col2.button("✖ Dismiss", key=f"rev_dism_{flag_id}", use_container_width=True):
                        result = resolve_review(flag_id, "DISMISSED", reviewer=reviewer)
                        _show_result(result, flag_id)
                    if col3.button("📦 Archive Doc", key=f"rev_arch_{flag_id}", use_container_width=True):
                        result = resolve_review(flag_id, "ARCHIVE_DOCUMENT", reviewer=reviewer)
                        _show_result(result, flag_id)

    with tab_resolved:
        with st.spinner("Fetching resolved review items..."):
            resolved_flags = list_reviews(status="RESOLVED")
            
        if not resolved_flags:
            render_empty_state(
                title="No Resolved Items",
                description="Flags that have been resolved, corrected, or archived will be archived in this history tab.",
                icon="📁"
            )
        else:
            st.markdown(f'<div style="font-size: 0.88rem; color: var(--tkf-text-muted); margin-bottom: 1rem;">Showing {len(resolved_flags)} resolved item(s)</div>', unsafe_allow_html=True)
            for flag in resolved_flags:
                flag_id = flag.get("flag_id", "FLAG-UNKNOWN")
                doc_id = flag.get("document_id", "DOC-UNKNOWN")
                resolution = flag.get("resolution", "RESOLVED")
                reviewer = flag.get("reviewer", "unknown")
                resolved_at = flag.get("resolved_at", "")[:19].replace("T", " ")
                
                with st.container(border=True):
                    st.markdown(f"**Flag:** `{flag_id}` · **Document:** `{doc_id}` — resolved as **`{resolution}`**")
                    st.caption(f"Resolved by **{reviewer}** · {resolved_at}")


def _show_result(result: dict, flag_id: str):
    if "error" in result:
        st.error(f"Couldn't update flag {flag_id}: {result['error']}")
    else:
        st.success(f"Flag {flag_id} successfully resolved.")
        st.rerun()
