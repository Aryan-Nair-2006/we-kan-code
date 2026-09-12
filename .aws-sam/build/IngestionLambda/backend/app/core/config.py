from pydantic_settings import BaseSettings
from pydantic import model_validator

class Settings(BaseSettings):
    aws_region: str = "us-east-1"
    s3_bucket_name: str = "test-bucket"
    dynamodb_table_name: str = "test-table"
    log_level: str = "INFO"
    max_upload_size_mb: int = 25
    chunk_size_words: int = 600
    chunk_overlap_words: int = 80
    
    # Phase 3 Configuration
    bedrock_embedding_model_id: str = "amazon.titan-embed-text-v1"
    opensearch_collection_endpoint: str = ""
    opensearch_index_name: str = "knowledge_chunks"
    opensearch_vector_dimension: int = 1536
    opensearch_bulk_batch_size: int = 50
    bedrock_max_retries: int = 3
    
    # Phase 4 Configuration
    bedrock_generation_model_id: str = "amazon.titan-text-express-v1"
    rag_top_k: int = 5
    rag_min_relevance_score: float = 0.5
    rag_max_context_chunks: int = 5
    
    @model_validator(mode='after')
    def validate_chunks(self) -> 'Settings':
        if self.chunk_size_words <= 0:
            raise ValueError("chunk_size_words must be greater than 0")
        if self.chunk_overlap_words < 0:
            raise ValueError("chunk_overlap_words must be 0 or greater")
        if self.chunk_overlap_words >= self.chunk_size_words:
            raise ValueError("chunk_overlap_words must be strictly less than chunk_size_words")
        return self
    
    model_config = {
        "env_file": ".env",
        "extra": "ignore"
    }

settings = Settings()
