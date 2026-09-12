import boto3
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
from typing import List, Dict, Any
from backend.app.core.config import settings
from backend.app.core.logging import setup_logger
from shared.models.indexing import IndexedChunk

logger = setup_logger(__name__)

class OpenSearchService:
    def __init__(self, host: str = settings.opensearch_collection_endpoint, region: str = settings.aws_region):
        self.host = host
        self.region = region
        self.index_name = settings.opensearch_index_name
        self.dimension = settings.opensearch_vector_dimension
        self.batch_size = settings.opensearch_bulk_batch_size
        
        credentials = boto3.Session().get_credentials()
        self.awsauth = AWS4Auth(
            credentials.access_key,
            credentials.secret_key,
            region,
            'aoss',
            session_token=credentials.token
        ) if credentials else None
        
        # Determine host format (strip https:// if present)
        host_stripped = self.host.replace("https://", "").strip("/") if self.host else "localhost"
        
        self.client = OpenSearch(
            hosts=[{'host': host_stripped, 'port': 443}],
            http_auth=self.awsauth,
            use_ssl=True,
            verify_certs=True,
            connection_class=RequestsHttpConnection,
            timeout=30
        )

    def initialize_index(self):
        """Create the vector index if it does not exist."""
        if not self.host:
            logger.warning("No OpenSearch host configured, skipping initialization")
            return
            
        try:
            if not self.client.indices.exists(index=self.index_name):
                mapping = {
                    "settings": {
                        "index": {
                            "knn": True
                        }
                    },
                    "mappings": {
                        "properties": {
                            "chunk_id": {"type": "keyword"},
                            "document_id": {"type": "keyword"},
                            "text": {"type": "text"},
                            "embedding": {
                                "type": "knn_vector",
                                "dimension": self.dimension,
                                "method": {
                                    "name": "hnsw",
                                    "engine": "faiss",
                                    "space_type": "cosinesimil"
                                }
                            },
                            "chunk_index": {"type": "integer"},
                            "page_number": {"type": "integer"},
                            "filename": {"type": "keyword"},
                            "owner": {"type": "keyword"},
                            "category": {"type": "keyword"},
                            "access_level": {"type": "keyword"},
                            "version": {"type": "keyword"},
                            "document_status": {"type": "keyword"},
                            "created_at": {"type": "date"},
                            "updated_at": {"type": "date"}
                        }
                    }
                }
                self.client.indices.create(index=self.index_name, body=mapping)
                logger.info(f"Created OpenSearch index: {self.index_name}")
        except Exception as e:
            logger.error(f"Failed to initialize index: {str(e)}")
            raise

    def bulk_index_chunks(self, chunks: List[IndexedChunk]) -> None:
        """Bulk index a list of IndexedChunk documents idempotently using chunk_id."""
        if not chunks:
            return
            
        from opensearchpy import helpers
        
        actions = []
        for chunk in chunks:
            action = {
                "_op_type": "index",
                "_index": self.index_name,
                "_id": chunk.chunk_id,
                "_source": chunk.model_dump()
            }
            actions.append(action)
            
        try:
            # Note: AOSS does not support _bulk fully the same as normal OS, but opensearchpy handles it gracefully for indexing
            success, failed = helpers.bulk(self.client, actions, chunk_size=self.batch_size, raise_on_error=False)
            
            if failed:
                # Explicitly parse the failed items
                error_msgs = []
                for f in failed:
                    op_type = list(f.keys())[0] if isinstance(f, dict) and f else "unknown"
                    err = f.get(op_type, {}).get("error", "Unknown error")
                    error_msgs.append(str(err))
                logger.error(f"Bulk indexing partially failed. Errors: {error_msgs}")
                raise RuntimeError(f"Failed to index {len(failed)} chunks: {error_msgs[0]}")
                
            logger.info(f"Successfully indexed {success} chunks")
        except Exception as e:
            logger.error(f"Bulk indexing operation failed: {str(e)}")
            raise

    def search_similar_chunks(self, embedding: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        """Search for similar chunks using vector similarity."""
        if not embedding:
            return []
            
        try:
            query = {
                "size": top_k,
                "query": {
                    "knn": {
                        "embedding": {
                            "vector": embedding,
                            "k": top_k
                        }
                    }
                }
            }
            
            response = self.client.search(
                index=self.index_name,
                body=query
            )
            
            hits = response.get("hits", {}).get("hits", [])
            
            results = []
            for hit in hits:
                source = hit.get("_source", {})
                score = hit.get("_score", 0.0)
                
                # AOSS cosine similarity scores are often 1 + cosine, mapping [-1, 1] to [0, 2]
                # Sometimes they map to [0, 1] depending on OpenSearch version.
                # Assuming standard OS Serverless knn scoring. We'll pass the raw score back.
                source["_score"] = score
                results.append(source)
                
            return results
            
        except Exception as e:
            logger.error(f"Vector search failed: {str(e)}")
            raise
