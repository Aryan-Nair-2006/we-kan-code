# AWS Infrastructure
**PHASE 3 STATUS: COMPLETE**

This folder contains the AWS SAM template (`template.yaml`) for deploying the Team Knowledge Finder application AWS resources.

## Current State (Phase 3 — Embeddings + Vector Indexing)
The infrastructure currently provisions and supports:
- **S3 knowledge bucket** (Storage for raw and processed documents).
- **DynamoDB metadata table** (Storage for document metadata and ingestion lifecycle statuses).
- **Ingestion Lambda** (Asynchronous text extraction and chunking worker, triggered by `documents/raw/`).
- **Indexing Lambda** (Asynchronous vector embedding and OpenSearch bulk ingestion worker, triggered by `processed/text/`).
- **OpenSearch Serverless** (Vector collection, strictly bound by Network, Encryption, and Data Access policies).
- **Required IAM permissions** (Least-privilege policies for S3 CRUD, DynamoDB CRUD, Bedrock `InvokeModel`, and AOSS `APIAccessAll`).

## How to deploy
```bash
sam build
sam deploy --guided
```
