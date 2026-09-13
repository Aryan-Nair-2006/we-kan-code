# Atlas Knowledge Platform — API Specification v2.0

**Document ID**: DOC-ATLAS-API-02  
**Version**: 2.0  
**Owner**: Backend Engineering Team  
**Access Level**: team  
**Status**: ACTIVE  
**Release Deadline**: December 25, 2026  

## 1. Authentication
All endpoints (except health probes) require an `Authorization: Bearer <JWT_TOKEN>` header containing a valid Cognito Identity Token.

## 2. Primary Endpoints
- `POST /query`: Submits a user question to the grounded RAG pipeline.
  - Request body: `{"question": string, "access_levels": [string]}`
  - Response: `{"answer": string, "sources": list, "confidence_score": float, "is_grounded": boolean}`
- `POST /documents/upload`: Multipart upload for raw documents (PDF, DOCX, TXT, MD, CSV, XLSX, PPTX).
- `GET /documents`: Lists all accessible documents for the caller's role.
- `GET /documents/{document_id}/freshness`: Returns version history, content hash, and superseded status.
- `POST /flags`: Creates a human-in-the-loop review flag for inaccurate or disputed answers.
- `GET /reviews`: Lists flagged items awaiting reviewer resolution.
- `POST /reviews/{flag_id}/resolve`: Resolves a flagged item (`dismissed`, `corrected`, `archived`).
- `GET /conflicts`: Returns detected cross-document semantic contradictions.
