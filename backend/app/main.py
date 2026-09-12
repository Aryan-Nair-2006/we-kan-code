from fastapi import FastAPI
from fastapi.responses import JSONResponse
import sys
import os

# Add parent dir to path to allow importing shared modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.app.core.logging import setup_logger

logger = setup_logger("api_main")

from backend.app.api.documents import router as documents_router
from backend.app.api.endpoints import analytics

app = FastAPI(title="Team Knowledge Finder API", version="0.1.0")

app.include_router(documents_router)
app.include_router(analytics.router)

@app.get("/health")
def health_check():
    logger.info("Health check endpoint called")
    return {"status": "ok", "service": "team-knowledge-finder"}

from shared.models.query import QueryRequest, QueryResponse
from backend.app.services.query_service import QueryService
from fastapi import HTTPException

@app.post("/query", response_model=QueryResponse)
def query_knowledge(request: QueryRequest):
    try:
        svc = QueryService()
        response = svc.query(request)
        return response
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

from backend.app.services.review_service import ReviewService, FlagSubmission, ReviewUpdateRequest

review_service = ReviewService()

@app.post("/flags", response_model=FlagSubmission)
def flag_knowledge(flag: FlagSubmission):
    try:
        return review_service.create_flag(flag)
    except Exception as e:
        logger.error(f"Error creating flag: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to record flag")

@app.get("/reviews", response_model=list[FlagSubmission])
def list_reviews(status: str = "All"):
    try:
        return review_service.list_flags(status_filter=status)
    except Exception as e:
        logger.error(f"Error listing reviews: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to list reviews")

@app.patch("/reviews/{flag_id}", response_model=FlagSubmission)
def update_review(flag_id: str, update_req: ReviewUpdateRequest):
    res = review_service.update_flag_status(flag_id, update_req)
    if not res:
        raise HTTPException(status_code=404, detail="Review flag not found")
    return res

