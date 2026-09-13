# Synthetic Demo Questions & Expected Scenarios

These questions demonstrate the core capabilities of **Team Knowledge Finder**:

### Scenario 1: Direct Factual Retrieval
- **Question**: "What vector dimension and similarity metric are used for OpenSearch?"
- **Expected Answer**: Vector dimension 1536 and Cosine Similarity metric.
- **Source Document**: `01_project_architecture_overview.md` (DOC-ATLAS-ARCH-01)

### Scenario 2: Release & Freshness Verification
- **Question**: "What is the release deadline for the API Specification v2.0?"
- **Expected Answer**: December 25, 2026. (The older superseded v1.0 date of Dec 20, 2026 is rejected).
- **Source Document**: `02_api_specification_v2.md` (DOC-ATLAS-API-02)

### Scenario 3: Database & Table Schema
- **Question**: "What DynamoDB tables exist and what are their primary keys?"
- **Expected Answer**: `MetadataTable` (`document_id`), `ReviewsTable` (`flag_id`), and `ConflictsTable` (`conflict_id`).
- **Source Document**: `03_database_data_model.md` (DOC-ATLAS-DB-03)

### Scenario 4: Operational Schedule & Conflict Scenario
- **Question**: "When are production deployments scheduled according to standard operations?"
- **Expected Answer**: Tuesday at 03:00 UTC (from `04_deployment_runbook.md`). 
- **Conflict Note**: Notice `11_emergency_deployment_override.md` specifies Friday 18:00 UTC emergency override, detected by the conflict service.

### Scenario 5: Security & RBAC Hierarchy
- **Question**: "What are the four user access levels in the RBAC hierarchy?"
- **Expected Answer**: `admin`, `developer`, `team`, and `public`.
- **Source Document**: `05_security_access_policy.md` (DOC-ATLAS-SEC-05)

### Scenario 6: Incident Post-Mortem
- **Question**: "What caused the elevated query latency in INC-402 and how was it resolved?"
- **Expected Answer**: A restrictive VPC security group rule blocked HTTPS egress; updating the rule restored 250ms latency.
- **Source Document**: `07_incident_report_inc_402.md` (DOC-ATLAS-INC-07)

### Scenario 7: Supported File Formats
- **Question**: "What file types can be uploaded to Team Knowledge Finder?"
- **Expected Answer**: PDF, DOCX, MD, TXT, CSV, XLSX, and PPTX up to 25MB.
- **Source Document**: `10_project_faq.md` (DOC-ATLAS-FAQ-10)

### Scenario 8: Clean System Abstention (No Hallucination)
- **Question**: "Who is the CEO of OpenAI and what was their revenue in 2024?"
- **Expected Answer**: The system abstains: *"I couldn't find enough information in the approved team documents to answer this question."*
- **Reason**: The approved knowledge base contains zero external company data.
