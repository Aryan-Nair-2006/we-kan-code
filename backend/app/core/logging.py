"""
Structured logging for Team Knowledge Finder — Phase 7.

Provides:
- JSON-structured log output (CloudWatch-friendly)
- Request ID generation + propagation
- Typed log helper that includes operation, status, duration, user/document context
- NEVER logs passwords, tokens, credentials, or full document content
"""
import logging
import json
import os
import uuid
import time
from typing import Optional, Any


def generate_request_id() -> str:
    """Generate a unique request correlation ID."""
    return str(uuid.uuid4())


class JsonFormatter(logging.Formatter):
    """
    Formats log records as JSON for structured CloudWatch Logs ingestion.
    """

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Propagate Phase 7 structured fields if present
        for field in ("request_id", "operation", "status", "user_id",
                      "document_id", "duration_ms", "error_code"):
            if hasattr(record, field):
                log_entry[field] = getattr(record, field)

        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, default=str)


def setup_logger(name: str) -> logging.Logger:
    """
    Create (or retrieve) a named logger.
    Uses JSON formatting when LOG_FORMAT=json (set in Lambda / production).
    Falls back to human-readable format for local development.
    """
    logger = logging.getLogger(name)
    log_level_str = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, log_level_str, logging.INFO)
    logger.setLevel(level)

    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setLevel(level)

        log_format = os.getenv("LOG_FORMAT", "text").lower()
        if log_format == "json":
            handler.setFormatter(JsonFormatter())
        else:
            handler.setFormatter(
                logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            )
        logger.addHandler(handler)

    return logger


def log_structured(
    logger: logging.Logger,
    level: str,
    message: str,
    operation: Optional[str] = None,
    request_id: Optional[str] = None,
    status: Optional[str] = None,
    user_id: Optional[str] = None,
    document_id: Optional[str] = None,
    duration_ms: Optional[float] = None,
    error_code: Optional[str] = None,
) -> None:
    """
    Emit a structured log entry with Phase 7 context fields.

    Security note: user_id is safe to log as an identifier.
    Do NOT pass email, tokens, passwords, or document text here.
    """
    extra: dict[str, Any] = {}
    if operation:
        extra["operation"] = operation
    if request_id:
        extra["request_id"] = request_id
    if status:
        extra["status"] = status
    if user_id:
        extra["user_id"] = user_id
    if document_id:
        extra["document_id"] = document_id
    if duration_ms is not None:
        extra["duration_ms"] = round(duration_ms, 2)
    if error_code:
        extra["error_code"] = error_code

    log_func = getattr(logger, level.lower(), logger.info)
    log_func(message, extra=extra)


logger = setup_logger(__name__)
