import streamlit as st
import re
from typing import Dict, Any, List
from frontend.services.api import submit_flag

def render_answer(question: str, result: dict):
    answer = result.get("answer", "")
    grounded = result.get("grounded", False)
    confidence = result.get("confidence", 0.0)
    sources = result.get("sources", [])
    
    st.markdown('<div class="tkf-eyebrow">QUESTION</div>', unsafe_allow_html=True)
    st.markdown(f'<div style="font-size: 1.4rem; font-weight: 600; color: var(--tkf-text-primary); margin-bottom: 1.5rem; line-height: 1.4;">{question}</div>', unsafe_allow_html=True)
    
    # ABSTENTION STATE: If not grounded or insufficient evidence
    if not grounded or not answer or "couldn't find" in answer.lower() or "insufficient" in answer.lower():
        st.markdown("""
        <div class="tkf-card" style="border-left: 4px solid var(--tkf-warning); margin-bottom: 1.5rem;">
            <div style="font-weight: 700; color: var(--tkf-warning); font-size: 1.15rem; display: flex; align-items: center; gap: 8px;">
                <span>⚠️</span> INSUFFICIENT EVIDENCE
            </div>
            <div style="margin-top: 0.5rem; font-size: 1rem; color: var(--tkf-text-primary); line-height: 1.5;">
                I couldn't find enough approved information in the knowledge base to answer this question reliably.
            </div>
            <div style="margin-top: 0.4rem; font-size: 0.88rem; color: var(--tkf-text-muted);">
                Try uploading a relevant project document or asking a more specific question.
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        c1, c2, _ = st.columns([2, 2, 4])
        with c1:
            if st.button("📤 Upload Document", use_container_width=True, key="abstain_upload"):
                st.session_state.current_view = "Upload"
                st.rerun()
        with c2:
            if st.button("📚 Browse Documents", use_container_width=True, key="abstain_browse"):
                st.session_state.current_view = "Documents"
                st.rerun()
        return

    # GROUNDED ANSWER STATE
    st.markdown('<div class="tkf-eyebrow">VERIFIED ANSWER</div>', unsafe_allow_html=True)

    # Trust indicator & Confidence badge
    conf_percent = int(confidence * 100) if confidence <= 1.0 else int(confidence)
    conf_badge_color = "var(--tkf-success)" if conf_percent >= 70 else "var(--tkf-warning)"
    
    st.markdown(f"""
    <div class="trust-indicator" style="display: flex; justify-content: space-between; align-items: center;">
        <div style="display: flex; align-items: center; gap: 10px;">
            <span class="trust-icon">✓</span>
            <div>
                <div class="trust-text">GROUNDED IN APPROVED PROJECT DOCUMENTS</div>
                <div style="font-size: 0.82rem; color: var(--tkf-text-muted);">{len(sources)} verified source citation(s)</div>
            </div>
        </div>
        <div style="background: rgba(15, 23, 42, 0.6); padding: 4px 12px; border-radius: 20px; border: 1px solid var(--tkf-border); font-size: 0.85rem; font-weight: 600; color: {conf_badge_color};">
            Confidence: {conf_percent}%
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Format Answer Text with Citation Badges
    formatted_answer = re.sub(
        r'\[S(\d+)\]',
        r'<span class="source-badge" style="margin: 0 3px;">S\1</span>',
        answer
    )
    
    st.markdown(f"""
    <div class="tkf-card" style="font-size: 1.08rem; color: var(--tkf-text-primary); line-height: 1.7; margin-bottom: 2rem;">
        {formatted_answer}
    </div>
    """, unsafe_allow_html=True)
    
    # SOURCES & EVIDENCE
    if sources:
        st.markdown('<div class="tkf-section-title">📄 Sources & Evidence</div>', unsafe_allow_html=True)
        
        for i, src in enumerate(sources):
            similarity = src.get("similarity", src.get("score", 0.0))
            filename = src.get("filename") or "Document"
            text = src.get("text", "")
            owner = src.get("owner") or "Team"
            version = src.get("version") or "1.0"
            access = str(src.get("access_level") or "Team").capitalize()
            page = src.get("page_number")
            
            page_str = f"Page {page}" if page else "Page info unavailable"
            match_str = f"Relevance: {int(similarity * 100)}%" if similarity else ""
            
            st.markdown(f"""
            <div class="source-card">
                <div class="source-header">
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <span class="source-badge">S{i+1}</span>
                        <span style="font-weight: 600; color: var(--tkf-text-primary); font-size: 0.98rem;">{filename}</span>
                    </div>
                    <span style="font-size: 0.8rem; color: var(--tkf-cyan); font-weight: 600;">{match_str}</span>
                </div>
                <div style="font-size: 0.83rem; color: var(--tkf-text-muted); margin-bottom: 10px; display: flex; gap: 14px; flex-wrap: wrap;">
                    <span>👤 Owner: {owner}</span>
                    <span>🔖 Version: v{version}</span>
                    <span>🔒 Access: {access}</span>
                    <span>📍 {page_str}</span>
                </div>
                <div style="font-size: 0.92rem; color: var(--tkf-text-secondary); background: var(--tkf-surface-2); padding: 10px 14px; border-radius: 6px; border-left: 3px solid var(--tkf-cyan);">
                    "{text[:250]}{'...' if len(text) > 250 else ''}"
                </div>
            </div>
            """, unsafe_allow_html=True)

            if len(text) > 250:
                with st.expander(f"View full supporting passage (S{i+1})"):
                    st.write(text)

    # FEEDBACK & FLAGGING SECTION
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="tkf-section-title">Feedback & Quality Review</div>', unsafe_allow_html=True)
    
    f_col1, f_col2, f_col3, _ = st.columns([1.5, 1.5, 2, 3])
    with f_col1:
        if st.button("👍 Helpful", key="fb_helpful", use_container_width=True):
            st.toast("Thank you for your feedback!", icon="👍")
    with f_col2:
        if st.button("👎 Not Helpful", key="fb_unhelpful", use_container_width=True):
            st.toast("Thank you for your feedback!", icon="👎")
    with f_col3:
        flag_clicked = st.button("🚩 Flag Answer", key="fb_flag", use_container_width=True)

    if flag_clicked or st.session_state.get("show_flag_modal"):
        st.session_state.show_flag_modal = True
        with st.expander("🚩 Submit Answer Flag for Review", expanded=True):
            reason = st.selectbox(
                "Reason for flagging",
                ["Incorrect information", "Outdated information", "Wrong source", "Missing evidence", "Other"],
                key="flag_reason"
            )
            details = st.text_area("Additional details (optional)", placeholder="Explain why this answer needs human review...", key="flag_details")
            
            if st.button("Submit Flag to Review Queue", type="primary", key="flag_submit"):
                first_src = sources[0] if sources else {}
                flag_payload = {
                    "document_id": first_src.get("document_id", "DOC-UNKNOWN"),
                    "chunk_id": first_src.get("chunk_id"),
                    "reason": reason,
                    "details": details,
                    "question": question,
                    "answer": answer,
                    "source_filename": first_src.get("filename", "Unknown"),
                    "supporting_passage": first_src.get("text", "")[:300]
                }
                res = submit_flag(flag_payload)
                if "error" not in res:
                    st.success("Thanks! This answer has been sent to the Review Queue.")
                    st.session_state.show_flag_modal = False
                else:
                    st.error(f"Failed to submit flag: {res.get('error')}")

def render_empty_state(title: str, description: str, icon: str = "📚"):
    """Renders a polished empty state container."""
    st.markdown(f"""
    <div style="text-align: center; padding: 3.5rem 2rem; background: var(--tkf-card); border: 1px dashed var(--tkf-border); border-radius: var(--tkf-radius); margin-top: 1rem;">
        <div style="font-size: 2.8rem; margin-bottom: 0.75rem; color: var(--tkf-text-muted);">{icon}</div>
        <h3 style="color: var(--tkf-text-primary); margin-bottom: 0.4rem; font-weight: 600;">{title}</h3>
        <p style="color: var(--tkf-text-secondary); max-width: 480px; margin: 0 auto; font-size: 0.95rem;">{description}</p>
    </div>
    """, unsafe_allow_html=True)
