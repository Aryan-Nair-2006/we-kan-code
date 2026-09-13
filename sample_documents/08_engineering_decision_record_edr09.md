# Atlas Knowledge Platform — Engineering Decision Record (EDR-09)

**Document ID**: DOC-ATLAS-EDR-08  
**Version**: 1.0  
**Owner**: AI Platform Engineering  
**Access Level**: developer  
**Status**: ACTIVE  

## 1. Decision
Adopt Amazon Bedrock Titan Text Express (`amazon.titan-text-express-v1`) as the primary text generation model and Amazon OpenSearch Serverless with Cosine Similarity vector indexing.

## 2. Rationale
Titan Text Express provides deterministic instruction following with minimal hallucination rates when bound to strict evidence context prompts. Cosine similarity provides superior ranking accuracy for 1536-dimensional Titan embeddings compared to Euclidean distance.
