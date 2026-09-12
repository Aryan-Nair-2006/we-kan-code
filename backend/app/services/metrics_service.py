"""
MetricsService — Phase 7

Publishes CloudWatch custom metrics for Team Knowledge Finder.

Design principles:
- NEVER raises exceptions — metric failure must not break the application.
- Falls back to structured log when CloudWatch is unavailable (local dev, missing creds).
- All metrics go to the configured namespace (default: TeamKnowledgeFinder).
"""
import logging
import time
from typing import Optional

import boto3
from botocore.exceptions import ClientError, NoCredentialsError

from backend.app.core.config import settings

logger = logging.getLogger(__name__)

# Metric name constants — single source of truth
QUERY_REQUESTS = "QueryRequests"
QUERY_SUCCESS = "QuerySuccess"
QUERY_FAILURE = "QueryFailure"
QUERY_ABSTENTION = "QueryAbstention"
QUERY_LATENCY_MS = "QueryLatencyMs"

DOCUMENT_UPLOADS = "DocumentUploads"
DOCUMENT_PROCESSING_SUCCESS = "DocumentProcessingSuccess"
DOCUMENT_PROCESSING_FAILURE = "DocumentProcessingFailure"

INDEXING_SUCCESS = "IndexingSuccess"
INDEXING_FAILURE = "IndexingFailure"

AUTHORIZATION_DENIED = "AuthorizationDenied"
AUTHENTICATION_FAILURE = "AuthenticationFailure"
STALE_DOCUMENT_REJECTED = "StaleDocumentRejected"
CONFLICTS_DETECTED = "ConflictsDetected"
REVIEW_FLAGS_CREATED = "ReviewFlagsCreated"


class MetricsService:
    """
    Thin wrapper around CloudWatch PutMetricData.
    Falls back to log-only when AWS is not available.
    """

    def __init__(self):
        self.namespace = settings.cloudwatch_namespace
        self._client = None

    def _get_client(self):
        """Lazy CloudWatch client — avoids crashing at import/init time."""
        if self._client is None:
            try:
                self._client = boto3.client("cloudwatch", region_name=settings.aws_region)
            except Exception as e:
                logger.warning(f"[Metrics] Could not create CloudWatch client: {e}")
        return self._client

    # ------------------------------------------------------------------
    # Core
    # ------------------------------------------------------------------

    def put_metric(self, name: str, value: float = 1.0, unit: str = "Count",
                   dimensions: Optional[list] = None) -> None:
        """
        Publish a single metric data point.
        NEVER raises — logs warning on failure.
        """
        metric_data = {
            "MetricName": name,
            "Value": value,
            "Unit": unit,
        }
        if dimensions:
            metric_data["Dimensions"] = dimensions

        try:
            client = self._get_client()
            if client is None:
                logger.info(f"[Metrics:log-only] {name}={value} {unit}")
                return
            client.put_metric_data(
                Namespace=self.namespace,
                MetricData=[metric_data]
            )
            logger.debug(f"[Metrics] Published {name}={value} {unit}")
        except (NoCredentialsError, ClientError) as e:
            # Expected in local dev — log at debug level only
            logger.debug(f"[Metrics:skipped] {name}: {e}")
        except Exception as e:
            logger.warning(f"[Metrics:error] Failed to publish {name}: {e}")

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    def record_query_request(self) -> None:
        self.put_metric(QUERY_REQUESTS)

    def record_query_success(self) -> None:
        self.put_metric(QUERY_SUCCESS)

    def record_query_failure(self) -> None:
        self.put_metric(QUERY_FAILURE)

    def record_abstention(self) -> None:
        self.put_metric(QUERY_ABSTENTION)

    def record_query_latency(self, start_time: float) -> None:
        elapsed_ms = (time.time() - start_time) * 1000
        self.put_metric(QUERY_LATENCY_MS, value=elapsed_ms, unit="Milliseconds")

    def record_document_upload(self) -> None:
        self.put_metric(DOCUMENT_UPLOADS)

    def record_document_processing_success(self) -> None:
        self.put_metric(DOCUMENT_PROCESSING_SUCCESS)

    def record_document_processing_failure(self) -> None:
        self.put_metric(DOCUMENT_PROCESSING_FAILURE)

    def record_indexing_success(self) -> None:
        self.put_metric(INDEXING_SUCCESS)

    def record_indexing_failure(self) -> None:
        self.put_metric(INDEXING_FAILURE)

    def record_auth_denied(self) -> None:
        self.put_metric(AUTHORIZATION_DENIED)

    def record_authentication_failure(self) -> None:
        self.put_metric(AUTHENTICATION_FAILURE)

    def record_stale_rejected(self) -> None:
        self.put_metric(STALE_DOCUMENT_REJECTED)

    def record_conflict_detected(self, count: int = 1) -> None:
        self.put_metric(CONFLICTS_DETECTED, value=float(count))

    def record_review_flag_created(self) -> None:
        self.put_metric(REVIEW_FLAGS_CREATED)
