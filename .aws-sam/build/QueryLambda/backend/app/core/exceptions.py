class ApplicationError(Exception):
    """Base class for application exceptions."""
    pass

class ConfigurationError(ApplicationError):
    """Raised when there is a configuration error."""
    pass

class DocumentProcessingError(ApplicationError):
    """Raised when document processing fails."""
    pass

class StorageError(ApplicationError):
    """Raised when a storage operation fails."""
    pass

class ValidationError(ApplicationError):
    """Raised when validation fails."""
    pass

class SearchError(ApplicationError):
    """Raised when search operations fail."""
    pass

class AIServiceError(ApplicationError):
    """Raised when Bedrock or other AI services fail."""
    pass
