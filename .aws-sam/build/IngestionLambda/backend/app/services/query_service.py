import re
from typing import List, Dict, Any, Tuple
from backend.app.core.config import settings
from backend.app.core.logging import setup_logger
from backend.app.services.embedding_service import EmbeddingService
from backend.app.services.opensearch_service import OpenSearchService
from backend.app.services.generation_service import GenerationService
from shared.models.query import QueryRequest, QueryResponse, SourceCitation

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
        self.min_relevance = settings.rag_min_relevance_score
        self.max_context_chunks = settings.rag_max_context_chunks

    def query(self, request: QueryRequest) -> QueryResponse:
        """
        Executes the full RAG pipeline:
        1. Embed question
        2. Retrieve chunks
        3. Validate/filter chunks
        4. Check sufficiency
        5. Generate grounded answer
        6. Validate citations
        """
        logger.info(f"Processing query: {request.question}")

        # 1. Embed question
        try:
            query_embedding = self.embedding_service.embed_text(request.question)
        except Exception as e:
            logger.error(f"Failed to embed question: {str(e)}")
            raise

        # 2. Retrieve chunks
        try:
            raw_hits = self.opensearch_service.search_similar_chunks(
                embedding=query_embedding,
                top_k=settings.rag_top_k
            )
        except Exception as e:
            logger.error(f"Failed to search chunks: {str(e)}")
            raise

        # 3. Validate/filter chunks
        valid_sources = self._validate_and_filter_sources(raw_hits)

        # 4. Check sufficiency
        if not valid_sources:
            logger.info("No sufficient evidence found, abstaining.")
            return QueryResponse(
                question=request.question,
                answer="I couldn't find sufficient evidence in the approved project documents to answer this question.",
                grounded=False,
                confidence=0.0,
                sources=[]
            )

        # Truncate to max context chunks if necessary
        sources_to_use = valid_sources[:self.max_context_chunks]

        # 5. Generate grounded answer
        try:
            raw_answer = self.generation_service.generate_grounded_answer(request.question, sources_to_use)
        except Exception as e:
            logger.error(f"Generation failed: {str(e)}")
            raise

        # 6. Validate citations
        final_answer, final_sources = self._validate_citations(raw_answer, sources_to_use)

        # Calculate confidence simply based on top similarity score for now
        # If citations were completely stripped, we abstain.
        if not final_sources:
            logger.info("Answer contained no valid citations. Abstaining.")
            return QueryResponse(
                question=request.question,
                answer="I couldn't produce a sufficiently supported answer from the approved project documents.",
                grounded=False,
                confidence=0.0,
                sources=[]
            )

        confidence = float(final_sources[0].similarity)

        return QueryResponse(
            question=request.question,
            answer=final_answer,
            grounded=True,
            confidence=confidence,
            sources=final_sources
        )

    def _validate_and_filter_sources(self, raw_hits: List[Dict[str, Any]]) -> List[SourceCitation]:
        """
        Filters out low relevance scores, missing fields, and handles mapping.
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
        source_mapping = {} # Old S-ID to New S-ID if we want to renumber, but keeping it simple for now
        
        for idx in sorted(list(cited_indices)):
            if 0 <= idx < len(supplied_sources):
                valid_sources.append(supplied_sources[idx])
                
        # If model hallucinated citations that don't exist, we could remove them from text.
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
