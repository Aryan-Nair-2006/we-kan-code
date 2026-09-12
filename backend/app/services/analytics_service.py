from backend.app.services.dynamodb_service import DynamoDBService
from collections import Counter

class AnalyticsService:
    def __init__(self):
        self.dynamodb_service = DynamoDBService()

    def get_overview(self) -> dict:
        docs = self.dynamodb_service.list_documents()
        
        overview = {
            "total_documents": len(docs),
            "ready_documents": 0,
            "processing_documents": 0,
            "failed_documents": 0,
            "total_chunks": 0,
            "by_category": Counter(),
            "by_file_type": Counter(),
            "by_access_level": Counter()
        }
        
        for doc in docs:
            status = doc.status.value.lower()
            if status == "ready":
                overview["ready_documents"] += 1
                overview["total_chunks"] += (doc.chunk_count or 0)
            elif status in ["processing", "uploaded"]:
                overview["processing_documents"] += 1
            else:
                overview["failed_documents"] += 1
                
            # Category
            cat = doc.category if doc.category else "Uncategorized"
            overview["by_category"][cat] += 1
            
            # File Type
            ft = doc.file_type if doc.file_type else "unknown"
            overview["by_file_type"][ft.upper()] += 1
            
            # Access Level
            al = doc.access_level.value if hasattr(doc.access_level, 'value') else str(doc.access_level)
            overview["by_access_level"][al.capitalize()] += 1
            
        # Convert Counters to dicts for JSON serialization
        overview["by_category"] = dict(overview["by_category"])
        overview["by_file_type"] = dict(overview["by_file_type"])
        overview["by_access_level"] = dict(overview["by_access_level"])
        
        return overview
