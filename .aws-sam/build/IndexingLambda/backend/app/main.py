from fastapi import FastAPI
from fastapi.responses import JSONResponse
import sys
import os

# Add parent dir to path to allow importing shared modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.app.core.logging import setup_logger

logger = setup_logger("api_main")

from backend.app.api.documents import router as documents_router

app = FastAPI(title="Team Knowledge Finder API", version="0.1.0")

app.include_router(documents_router)

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

@app.post("/flags")
def flag_knowledge():
    return {"status": "not_implemented", "phase": 1}

@app.get("/reviews")
def list_reviews():
    return {"status": "not_implemented", "phase": 1}
