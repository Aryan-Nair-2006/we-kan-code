from fastapi import APIRouter
from backend.app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["analytics"])
analytics_service = AnalyticsService()

@router.get("/overview")
def get_analytics_overview():
    return analytics_service.get_overview()
