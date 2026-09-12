import boto3
from typing import Optional, List
from shared.models.document import DocumentMetadata
from backend.app.core.config import settings
from backend.app.core.exceptions import StorageError
from backend.app.core.logging import setup_logger

logger = setup_logger(__name__)

class DynamoDBService:
    def __init__(self, table_name: str = settings.dynamodb_table_name):
        self.table_name = table_name
        self.dynamodb = boto3.resource('dynamodb', region_name=settings.aws_region)
        self.table = self.dynamodb.Table(self.table_name)
        
    def create_document(self, metadata: DocumentMetadata) -> DocumentMetadata:
        try:
            item = metadata.model_dump(mode='json')
            self.table.put_item(Item=item)
            return metadata
        except Exception as e:
            logger.error(f"Failed to create document in DynamoDB: {str(e)}")
            raise StorageError(f"DynamoDB error: {str(e)}")

    def get_document(self, document_id: str) -> Optional[DocumentMetadata]:
        try:
            response = self.table.get_item(Key={'document_id': document_id})
            item = response.get('Item')
            if item:
                return DocumentMetadata(**item)
            return None
        except Exception as e:
            logger.error(f"Failed to get document from DynamoDB: {str(e)}")
            raise StorageError(f"DynamoDB error: {str(e)}")

    def update_document(self, metadata: DocumentMetadata) -> DocumentMetadata:
        return self.create_document(metadata)
        
    def list_documents(self) -> List[DocumentMetadata]:
        try:
            response = self.table.scan()
            items = response.get('Items', [])
            return [DocumentMetadata(**item) for item in items]
        except Exception as e:
            logger.error(f"Failed to list documents: {str(e)}")
            raise StorageError(f"DynamoDB scan error: {str(e)}")
