# Atlas Knowledge Platform — Architecture Overview

**Document ID**: DOC-ATLAS-ARCH-01  
**Version**: 2.0  
**Owner**: Platform Architecture Team  
**Access Level**: team  
**Status**: ACTIVE  

## 1. System Overview
The Atlas Knowledge Platform is an enterprise-grade AI knowledge discovery platform built on serverless AWS infrastructure. It provides strict evidence-grounded question answering over verified organization documents.

## 2. Core Architectural Components
- **Frontend User Interface**: Built with Python and Streamlit, featuring an immersive dark-mode interface with source passage inspection.
- **API Gateway**: AWS Serverless HTTP/REST API with integrated Amazon Cognito User Pool Authorizer validating cryptographically signed JWT tokens.
- **Compute Layer**: AWS Lambda functions running Python 3.11 for document ingestion, OpenSearch indexing, RAG query processing, and administrative API routes.
- **Storage Layer**: 
  - **Amazon S3**: Bucket `team-knowledge-finder-knowledge-bucket` for raw documents and extracted chunk payloads.
  - **Amazon DynamoDB**: Tables for document metadata, review flags, and detected semantic contradictions.
- **Vector Search Engine**: Amazon OpenSearch Serverless collection `team-knowledge-finder-kb` utilizing vector dimension 1536 and cosine similarity metric.
- **Foundation Models**: Amazon Bedrock hosting `amazon.titan-embed-text-v1` for text embeddings and `amazon.titan-text-express-v1` for grounded answer generation.

## 3. Grounded Retrieval-Augmented Generation (RAG)
All queries perform similarity search against vector embeddings, filter chunks according to user role access levels (`public`, `team`, `developer`, `admin`), evaluate document freshness, and inject top-ranked passages into Bedrock with prompt-injection defense wrappers.
