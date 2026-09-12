import re
import time
from typing import List, Dict, Any, Tuple, Optional
from backend.app.core.config import settings
from backend.app.core.logging import setup_logger, generate_request_id, log_structured
from backend.app.services.embedding_service import EmbeddingService
from backend.app.services.opensearch_service import OpenSearchService
from backend.app.services.generation_service import GenerationService
from backend.app.services.dynamodb_service import DynamoDBService
from backend.app.services.metrics_service import MetricsService
from shared.constants.document_status import DocumentStatus
from shared.models.query import QueryRequest, QueryResponse, SourceCitation
from backend.app.models.auth import AuthContext

logger = setup_logger(__name__)

import math

def normalize_relevance_score(raw_score: Any) -> float:
    """
    Validates OpenSearch raw _score.
    OpenSearch cosinesimil maps cosine [-1, 1] to a (1+cosine)/2 equivalent
    score inherently if properly configured, yielding [0, 1].
    If score is outside [0,1], NaN, or infinity, we reject it (return 0.0).
    """
    try:
        score = float(raw_score)
    except (ValueError, TypeError):
        return 0.0
        
    if math.isnan(score) or math.isinf(score):
        return 0.0
        
    if score < 0.0 or score > 1.0:
        return 0.0
        
    return score

class QueryService:
    def __init__(self):
        self.embedding_service = EmbeddingService()
        self.opensearch_service = OpenSearchService()
        self.generation_service = GenerationService()
        self.dynamodb_service = DynamoDBService()
        self.metrics = MetricsService()
        self.min_relevance = settings.rag_min_relevance_score
        self.max_context_chunks = settings.rag_max_context_chunks

    def query(self, request: QueryRequest, auth_context: Optional[AuthContext] = None) -> QueryResponse:
        """
        Executes the full RAG pipeline:
        1. Derive access levels from AuthContext (backend-authoritative)
        2. Embed question
        3. Retrieve chunks
        4. Validate/filter chunks (access level + document status)
        5. Live DynamoDB freshness/status re-check
        6. Conflict awareness check
        7. Check sufficiency
        8. Generate grounded answer
        9. Validate citations

        auth_context: Server-side AuthContext — if None, falls back to request.access_levels
                      (acceptable in local dev; never acceptable in production).
        """
        request_id = generate_request_id()
        start_time = time.time()
        user_id = auth_context.user_id if auth_context else "anonymous"

        log_structured(
            logger, "info", "Query started",
            operation="query", request_id=request_id, status="started", user_id=user_id
        )
        self.metrics.record_query_request()

        # 1. Derive access levels — backend always wins
        if auth_context is not None:
            allowed_access_levels = {
                str(lvl.value if hasattr(lvl, "value") else lvl).lower()
                for lvl in auth_context.access_levels
            }
        else:
            import os
            env = os.getenv("ENVIRONMENT", settings.environment).lower()
            if env != "local":
                logger.error("Query attempted in non-local environment without AuthContext — denying (fail-closed)")
                self.metrics.record_authentication_failure()
                raise ValueError("Authentication context is required in production environment")
            # Fallback: trust request.access_levels (only safe in local dev)
            allowed_access_levels = {
                str(level.value if hasattr(level, "value") else level).lower()
                for level in request.access_levels
            }

        # 2. Embed question
        try:
            query_embedding = self.embedding_service.embed_text(request.question)
        except Exception as e:
            logger.error(f"Failed to embed question: {str(e)}")
            self.metrics.record_query_failure()
            raise

        # 3. Retrieve chunks — over-fetch to compensate for filtering
        retrieval_pool_size = settings.rag_top_k * settings.rag_retrieval_pool_multiplier
        try:
            raw_hits = self.opensearch_service.search_similar_chunks(
                embedding=query_embedding,
                top_k=retrieval_pool_size
            )
        except Exception as e:
            logger.error(f"Failed to search chunks: {str(e)}")
            self.metrics.record_query_failure()
            raise

        # 4. Validate/filter chunks (relevance, index-time document status, access level)
        valid_sources = self._validate_and_filter_sources(raw_hits, allowed_access_levels)

        # 5. Re-check LIVE document status in DynamoDB (stale vector protection)
        valid_sources = self._filter_by_live_status(valid_sources, request_id=request_id)

        # 6. Check for known conflicts among the evidence
        conflict_warning = False
        conflict_details = None
        if valid_sources:
            conflict_warning, conflict_details = self._check_for_conflicts(valid_sources)

        # 7. Check sufficiency
        if not valid_sources:
            log_structured(logger, "info", "No sufficient evidence found, abstaining",
                           operation="query", request_id=request_id, status="abstention", user_id=user_id)
            self.metrics.record_abstention()
            self.metrics.record_query_latency(start_time)
            return QueryResponse(
                question=request.question,
                answer="I couldn't find sufficient evidence in the approved project documents to answer this question.",
                grounded=False,
                confidence=0.0,
                sources=[],
                user_id=user_id,
            )

        # Truncate to max context chunks if necessary
        sources_to_use = valid_sources[:self.max_context_chunks]

        # 8. Generate grounded answer — include conflict context if needed
        try:
            if conflict_warning and conflict_details:
                raw_answer = self.generation_service.generate_grounded_answer(
                    request.question, sources_to_use, conflict_context=conflict_details
                )
            else:
                raw_answer = self.generation_service.generate_grounded_answer(
                    request.question, sources_to_use
                )
        except Exception as e:
            logger.error(f"Generation failed: {str(e)}")
            self.metrics.record_query_failure()
            raise

        # 9. Validate citations
        final_answer, final_sources = self._validate_citations(raw_answer, sources_to_use)

        # If citations were completely stripped, abstain
        if not final_sources:
            log_structured(logger, "info", "Answer contained no valid citations. Abstaining.",
                           operation="query", request_id=request_id, status="abstention", user_id=user_id)
            self.metrics.record_abstention()
            self.metrics.record_query_latency(start_time)
            return QueryResponse(
                question=request.question,
                answer="I couldn't produce a sufficiently supported answer from the approved project documents.",
                grounded=False,
                confidence=0.0,
                sources=[],
                user_id=user_id,
            )

        confidence = float(final_sources[0].similarity)
        duration_ms = (time.time() - start_time) * 1000

        log_structured(
            logger, "info", "Query completed successfully",
            operation="query", request_id=request_id, status="success",
            user_id=user_id, duration_ms=duration_ms
        )
        self.metrics.record_query_success()
        self.metrics.record_query_latency(start_time)

        return QueryResponse(
            question=request.question,
            answer=final_answer,
            grounded=True,
            confidence=confidence,
            sources=final_sources,
            conflict_warning=conflict_warning,
            conflict_details=conflict_details,
            user_id=user_id,
        )

    def _validate_and_filter_sources(self, raw_hits: List[Dict[str, Any]],
                                      allowed_access_levels: set) -> List[SourceCitation]:
        """
        Filters out low relevance scores, missing fields, access-restricted chunks,
        and handles mapping.
        """
        sources = []
        seen_chunks = set()
        
        for hit in raw_hits:
            raw_score = hit.get('_score', 0.0)
            score = normalize_relevance_score(raw_score)
            
            # Simple relevance filter using normalized similarity
            if score < self.min_relevance:
                continue
                
            chunk_id = hit.get('chunk_id')
            document_id = hit.get('document_id')
            text = hit.get('text')
            
            # Missing mandatory fields
            if not chunk_id or not document_id or not text or not str(text).strip():
                continue
                
            # Valid document status only (FAIL-CLOSED)
            status = hit.get('document_status')
            if not status or status.upper() != 'READY':
                continue

            # Access-level visibility (FAIL-CLOSED): a chunk with a missing or
            # unrecognized access_level is never returned, even if the requester
            # claims broad clearance.
            chunk_access_level = hit.get('access_level')
            if not chunk_access_level or str(chunk_access_level).lower() not in allowed_access_levels:
                continue
                
            # Deduplicate just in case
            if chunk_id in seen_chunks:
                continue
            seen_chunks.add(chunk_id)
            
            source = SourceCitation(
                chunk_id=str(chunk_id),
                document_id=str(document_id),
                text=str(text).strip(),
                filename=hit.get('filename'),
                page_number=hit.get('page_number'),
                owner=hit.get('owner'),
                category=hit.get('category'),
                access_level=hit.get('access_level'),
                version=hit.get('version'),
                similarity=float(score)
            )
            sources.append(source)
            
        # Sort by similarity descending
        sources.sort(key=lambda x: x.similarity, reverse=True)
        return sources

    def _filter_by_live_status(
        self, sources: List[SourceCitation], request_id: str = ""
    ) -> List[SourceCitation]:
        """
        Drops sources whose document is no longer READY right now (e.g. it was
        flagged for review, archived, or superseded after indexing). One DynamoDB
        lookup per unique document among the candidates, cached for this request.

        Phase 7: also rejects superseded documents (is_current=False).
        """
        if not sources:
            return sources

        status_cache: Dict[str, Any] = {}
        filtered = []
        for source in sources:
            doc_id = source.document_id
            if doc_id not in status_cache:
                try:
                    doc = self.dynamodb_service.get_document(doc_id)
                    status_cache[doc_id] = doc
                except Exception as e:
                    logger.warning(f"Could not verify live status for document {doc_id}: {str(e)}")
                    status_cache[doc_id] = None  # FAIL-CLOSED

            doc = status_cache[doc_id]

            if doc is None:
                log_structured(logger, "info", f"Excluding chunk: document {doc_id} not found",
                               operation="freshness_filter", request_id=request_id)
                self.metrics.record_stale_rejected()
                continue

            if doc.status != DocumentStatus.READY:
                log_structured(logger, "info",
                               f"Excluding chunk from {doc_id}: live status is {doc.status}, not READY",
                               operation="freshness_filter", request_id=request_id,
                               document_id=doc_id)
                self.metrics.record_stale_rejected()
                continue

            # Phase 7: also reject superseded documents
            if not doc.is_current:
                log_structured(logger, "info",
                               f"Excluding chunk from {doc_id}: document is superseded by {doc.superseded_by}",
                               operation="freshness_filter", request_id=request_id,
                               document_id=doc_id)
                self.metrics.record_stale_rejected()
                continue

            filtered.append(source)

        return filtered

    def _check_for_conflicts(
        self, sources: List[SourceCitation]
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if there are known open conflicts among the evidence sources.
        Returns (conflict_warning, conflict_details_string).
        Fail-open: any error returns (False, None) so the query is not blocked.
        """
        try:
            from backend.app.services.conflict_service import ConflictService
            conflict_svc = ConflictService()
            doc_ids = list({s.document_id for s in sources})
            conflicts = conflict_svc.get_conflicts_for_document_ids(doc_ids)
            if not conflicts:
                return False, None

            # Summarize the conflicts for the answer context
            details_parts = []
            for c in conflicts[:3]:  # Cap at 3 for prompt brevity
                details_parts.append(
                    f"Document '{c.source_document_id}' (chunk {c.source_chunk_id}) may contradict "
                    f"document '{c.conflicting_document_id}' (chunk {c.conflicting_chunk_id}) "
                    f"with confidence {c.confidence:.0%}. Reason: {c.topic or 'unspecified'}."
                )

            conflict_details = " | ".join(details_parts)
            logger.info(f"Found {len(conflicts)} open conflict(s) among evidence sources")
            return True, conflict_details
        except Exception as e:
            logger.warning(f"Conflict check failed (non-blocking): {e}")
            return False, None

    def _validate_citations(self, answer: str, supplied_sources: List[SourceCitation]) -> Tuple[str, List[SourceCitation]]:
        """
        Finds [S#] tags in the answer and ensures they map to supplied_sources.
        Returns the sanitized answer and the actual sources that were cited.
        """
        # Find all cited IDs like [S1], [S2]
        citation_matches = re.findall(r'\[S(\d+)\]', answer)
        cited_indices = set()
        
        for match in citation_matches:
            try:
                idx = int(match) - 1 # S1 maps to index 0
                cited_indices.add(idx)
            except ValueError:
                pass
                
        valid_sources = []
        
        for idx in sorted(list(cited_indices)):
            if 0 <= idx < len(supplied_sources):
                valid_sources.append(supplied_sources[idx])
                
        # Simple cleanup: remove [S#] if # is out of bounds.
        def clean_hallucinated(match):
            try:
                idx = int(match.group(1)) - 1
                if 0 <= idx < len(supplied_sources):
                    return match.group(0) # Keep valid
            except ValueError:
                pass
            return "" # Remove invalid
            
        sanitized_answer = re.sub(r'\[S(\d+)\]', clean_hallucinated, answer)
        
        # We strictly return ONLY the cited sources.
        final_sources = valid_sources
        
        return sanitized_answer.strip(), final_sources
