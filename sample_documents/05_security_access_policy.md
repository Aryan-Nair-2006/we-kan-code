# Atlas Knowledge Platform — Security & Access Control Policy

**Document ID**: DOC-ATLAS-SEC-05  
**Version**: 2.1  
**Owner**: Chief Information Security Officer (CISO)  
**Access Level**: admin  
**Status**: ACTIVE  

## 1. Role-Based Access Control (RBAC)
User permissions are strictly hierarchical:
- `admin`: Full administrative access to all documents, reviews, flags, conflicts, and system configuration.
- `developer`: Access to public, team, and developer technical specifications, database schemas, and metrics.
- `team`: Access to public and team product documentation, meeting notes, and project summaries.
- `public`: Access to public onboarding documents and FAQs only.

## 2. Prompt Injection Defense
Retrieved document chunks are strictly enclosed within `<evidence>` delimiters and treated purely as passive data. The LLM is instructed to reject any instruction inside retrieved text that attempts to override system guidelines or reveal system configuration.
