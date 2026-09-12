import streamlit as st
import time
from frontend.components.design import inject_custom_css
from frontend.services.api import upload_document, get_document_status

def render_upload():
    inject_custom_css()
    
    st.markdown('<div class="tkf-eyebrow">KNOWLEDGE MANAGEMENT</div>', unsafe_allow_html=True)
    st.markdown('<div class="tkf-hero-title">Add Team Knowledge</div>', unsafe_allow_html=True)
    st.markdown('<div class="tkf-hero-subtitle">Upload approved project documents (PDF, DOCX, TXT, XLSX, CSV, PPTX, MD) to ingest and index them for grounded QA.</div>', unsafe_allow_html=True)
    
    # File Uploader
    uploaded_file = st.file_uploader(
        "Choose files to upload",
        type=["pdf", "docx", "txt", "xlsx", "csv", "pptx", "md"],
        accept_multiple_files=False,
        key="upload_file_widget"
    )
    
    st.markdown("""
    <div style="font-size: 0.82rem; color: var(--tkf-text-muted); margin-bottom: 1.5rem;">
        Supported file formats: PDF · DOCX · TXT · XLSX · CSV · PPTX · MD (Max size: 25MB)
    </div>
    """, unsafe_allow_html=True)
    
    if uploaded_file:
        st.markdown('<div class="tkf-section-title">📝 Document Metadata</div>', unsafe_allow_html=True)
        st.markdown('<div class="tkf-card">', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            owner = st.text_input("Owner / Team", value="Engineering Team", placeholder="e.g. Architecture Team", key="upload_owner")
            version = st.text_input("Version", value="1.0", placeholder="e.g. 1.0", key="upload_version")
        with col2:
            category = st.selectbox(
                "Category",
                ["Requirements", "Architecture", "Engineering", "Project Management", "Meetings", "Policies", "Reports", "Other"],
                index=1,
                key="upload_category"
            )
            access_level = st.selectbox(
                "Access Level",
                ["Public", "Team", "Developer", "Admin"],
                index=1,
                key="upload_access"
            )
            
        st.markdown("<br>", unsafe_allow_html=True)
        
        if st.button("Upload & Process Document", type="primary", use_container_width=True, key="upload_submit_btn"):
            if not owner or not category:
                st.warning("Please fill in all required metadata fields.")
            else:
                with st.status("Uploading & Processing Document...", expanded=True) as status_box:
                    st.write("✓ Preparing document metadata...")
                    meta = {
                        "owner": owner,
                        "category": category,
                        "access_level": access_level.lower(),
                        "version": version
                    }
                    
                    st.write("✓ Uploading file to secure storage (S3)...")
                    res = upload_document(uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type or "application/octet-stream", meta)
                    
                    if "error" in res:
                        status_box.update(label="✖ Upload Failed", state="error", expanded=True)
                        st.error(f"Upload failed: {res['error']}")
                    else:
                        doc_id = res.get("document_id")
                        st.write(f"✓ Document created with ID: `{doc_id}`")
                        st.write("⏳ Polling ingestion & vector indexing pipeline...")
                        
                        # Background status polling
                        max_retries = 10
                        success = False
                        for _ in range(max_retries):
                            time.sleep(1.5)
                            poll_res = get_document_status(doc_id)
                            if "error" not in poll_res:
                                doc_status = str(poll_res.get("status", "")).lower()
                                if doc_status == "ready":
                                    status_box.update(label="✓ Document Ready for Search!", state="complete", expanded=False)
                                    st.success(f"🎉 **{uploaded_file.name}** has been processed and indexed successfully into OpenSearch vector index!")
                                    success = True
                                    break
                                elif doc_status == "failed":
                                    status_box.update(label="✖ Processing Failed", state="error", expanded=True)
                                    st.error(f"Processing error: {poll_res.get('processing_error', 'Unknown failure')}")
                                    success = True
                                    break
                        
                        if not success:
                            status_box.update(label="Uploaded — Processing in Background", state="complete", expanded=False)
                            st.info("The document was uploaded successfully and is processing in the background. Check status anytime in the Knowledge Base tab.")
        st.markdown('</div>', unsafe_allow_html=True)
