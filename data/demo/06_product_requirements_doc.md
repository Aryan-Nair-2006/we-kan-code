# Atlas Knowledge Platform — Product Requirements Document (PRD)

**Document ID**: DOC-ATLAS-PRD-06  
**Version**: 1.8  
**Owner**: Product Management  
**Access Level**: team  
**Status**: ACTIVE  

## 1. Grounded Answering Requirements
- **Citation Passages**: Every answer provided by the AI must link directly to the underlying document chunk with line or character boundaries.
- **Confidence Scoring**: Answers below a cosine similarity threshold of 0.5 must trigger explicit system abstention.
- **Human-in-the-Loop**: Users can flag inaccurate answers with reasons such as "Outdated information", "Incorrect fact", or "Policy violation".
