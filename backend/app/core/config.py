import os
os.environ.setdefault("AWS_EC2_METADATA_DISABLED", "true")

from pydantic_settings import BaseSettings
from pydantic import model_validator

class Settings(BaseSettings):
    aws_region: str = "us-east-1"
    s3_bucket_name: str = "test-bucket"
    dynamodb_table_name: str = "test-table"
    reviews_table_name: str = "test-reviews-table"
    log_level: str = "INFO"
    max_upload_size_mb: int = 25
    chunk_size_words: int = 600
    chunk_overlap_words: int = 100
    allowed_file_types: list[str] = ["pdf", "docx", "txt", "md", "csv", "xlsx", "pptx"]
    
    # Bedrock models
    bedrock_model_id: str = "amazon.titan-embed-text-v1"
    bedrock_embedding_model_id: str = "amazon.titan-embed-text-v1"
    bedrock_generation_model_id: str = "amazon.titan-text-express-v1"
    bedrock_max_retries: int = 3
    bedrock_base_backoff_seconds: float = 1.0

    # OpenSearch
    vector_dimension: int = 1536
    opensearch_endpoint: str = "https://localhost:9200"
    opensearch_collection_endpoint: str = ""
    opensearch_index: str = "rag-chunks"
    opensearch_index_name: str = "knowledge_chunks"
    opensearch_vector_dimension: int = 1536
    opensearch_bulk_batch_size: int = 50

    # RAG
    rag_top_k: int = 5
    rag_min_relevance_score: float = 0.5
    rag_max_context_chunks: int = 5
    rag_retrieval_pool_multiplier: int = 4

    # Phase 7 — Auth / Environment
    environment: str = "local"      # "local" | "production"
    dev_user_id: str = "demo-user"  # Only used when environment=local
    dev_role: str = "developer"     # Only used when environment=local

    # Phase 7 — Conflict Detection
    conflicts_table_name: str = "test-conflicts-table"
    conflict_detection_enabled: bool = True
    conflict_confidence_threshold: float = 0.75
    conflict_max_candidates: int = 5

    # Phase 7 — Monitoring / CloudWatch
    cloudwatch_namespace: str = "TeamKnowledgeFinder"

    @model_validator(mode='after')
    def validate_chunks(self) -> 'Settings':
        if not self.aws_region or not self.aws_region.strip():
            self.aws_region = "us-east-1"
        if not self.dynamodb_table_name or not self.dynamodb_table_name.strip():
            self.dynamodb_table_name = "test-table"
        if not self.s3_bucket_name or not self.s3_bucket_name.strip():
            self.s3_bucket_name = "test-bucket"
        if not self.reviews_table_name or not self.reviews_table_name.strip():
            self.reviews_table_name = "test-reviews-table"
        if not self.conflicts_table_name or not self.conflicts_table_name.strip():
            self.conflicts_table_name = "test-conflicts-table"
        if self.chunk_size_words <= 0:
            raise ValueError("chunk_size_words must be greater than 0")
        if self.chunk_overlap_words < 0:
            raise ValueError("chunk_overlap_words cannot be negative")
        if self.chunk_overlap_words >= self.chunk_size_words:
            raise ValueError("chunk_overlap_words must be strictly less than chunk_size_words")
        return self
    
    model_config = {
        "env_file": ".env",
        "extra": "ignore"
    }

settings = Settings()
