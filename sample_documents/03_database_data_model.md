# Atlas Knowledge Platform — Database & Data Model

**Document ID**: DOC-ATLAS-DB-03  
**Version**: 1.5  
**Owner**: Data Engineering Team  
**Access Level**: developer  
**Status**: ACTIVE  

## 1. DynamoDB Tables
1. **MetadataTable (`team-knowledge-finder-metadata`)**:
   - Primary Key: `document_id` (String)
   - Attributes: `filename`, `content_hash`, `version`, `is_current`, `access_level`, `status`, `indexing_status`, `chunk_count`, `created_at`, `updated_at`.
2. **ReviewsTable (`team-knowledge-finder-reviews`)**:
   - Primary Key: `flag_id` (String)
   - Attributes: `document_id`, `chunk_id`, `reason`, `status` (`pending`, `resolved`), `resolution` (`dismissed`, `corrected`, `archived`), `flagged_by`, `reviewer`, `created_at`, `resolved_at`.
3. **ConflictsTable (`team-knowledge-finder-conflicts`)**:
   - Primary Key: `conflict_id` (String)
   - Attributes: `source_document_id`, `target_document_id`, `source_chunk_id`, `target_chunk_id`, `similarity_score`, `contradiction_reason`, `created_at`.
