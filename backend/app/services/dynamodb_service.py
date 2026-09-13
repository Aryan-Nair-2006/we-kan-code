from typing import Optional, List, Dict
from shared.models.document import DocumentMetadata
from backend.app.core.config import settings
from backend.app.core.exceptions import StorageError
from backend.app.core.logging import setup_logger
from backend.app.core.aws import has_valid_aws_credentials, get_boto3_resource
from backend.app.core.local_cache import DOCS_FILE, load_json, save_json

logger = setup_logger(__name__)

# Fallback store for local development without live DynamoDB
_LOCAL_DOCS_STORE: Dict[str, DocumentMetadata] = {}

def _init_docs_store():
    data = load_json(DOCS_FILE)
    for doc_id, doc_dict in data.items():
        try:
            _LOCAL_DOCS_STORE[doc_id] = DocumentMetadata(**doc_dict)
        except Exception:
            pass

_init_docs_store()

class DynamoDBService:
    def __init__(self, table_name: str = settings.dynamodb_table_name):
        self.table_name = table_name or "test-table"
        self.table = None
        if has_valid_aws_credentials():
            try:
                self.dynamodb = get_boto3_resource('dynamodb', region_name=settings.aws_region or "us-east-1")
                if self.dynamodb:
                    self.table = self.dynamodb.Table(self.table_name)
            except Exception as e:
                logger.warning(f"DynamoDB resource initialization warning: {e}")
                self.table = None
        
    def create_document(self, metadata: DocumentMetadata) -> DocumentMetadata:
        _LOCAL_DOCS_STORE[metadata.document_id] = metadata
        save_json(DOCS_FILE, {k: v.model_dump(mode='json') for k, v in _LOCAL_DOCS_STORE.items()})
        try:
            if self.table:
                item = metadata.model_dump(mode='json')
                self.table.put_item(Item=item)
            return metadata
        except Exception as e:
            logger.warning(f"Failed to create document in DynamoDB (using local store fallback): {str(e)}")
            return metadata

    def get_document(self, document_id: str) -> Optional[DocumentMetadata]:
        try:
            if self.table:
                response = self.table.get_item(Key={'document_id': document_id})
                item = response.get('Item')
                if item:
                    return DocumentMetadata(**item)
        except Exception as e:
            logger.warning(f"DynamoDB get error (checking local store fallback): {str(e)}")
            
        return _LOCAL_DOCS_STORE.get(document_id)

    def update_document(self, metadata: DocumentMetadata) -> DocumentMetadata:
        return self.create_document(metadata)
        
    def list_documents(self) -> List[DocumentMetadata]:
        try:
            if self.table:
                response = self.table.scan()
                items = response.get('Items', [])
                if items:
                    docs = [DocumentMetadata(**item) for item in items]
                    # Update local store with scanned items
                    for d in docs:
                        _LOCAL_DOCS_STORE[d.document_id] = d
                    save_json(DOCS_FILE, {k: v.model_dump(mode='json') for k, v in _LOCAL_DOCS_STORE.items()})
                    return docs
        except Exception as e:
            logger.warning(f"DynamoDB scan warning (using local store fallback): {str(e)}")
            
        return list(_LOCAL_DOCS_STORE.values())
