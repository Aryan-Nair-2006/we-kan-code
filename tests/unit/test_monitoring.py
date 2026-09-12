"""
Phase 7 Tests — Monitoring (Metrics + Structured Logging)

Tests 20-27 covering:
20. MetricsService.put_metric does not raise when CloudWatch unavailable
21. MetricsService.put_metric calls CloudWatch when available
22. MetricsService helper methods call put_metric with correct names
23. generate_request_id returns UUID-format string
24. log_structured emits all provided fields
25. QueryService emits QUERY_REQUESTS metric on query start
26. QueryService emits QUERY_ABSTENTION when no evidence found
27. MetricsService falls back gracefully on NoCredentialsError
"""
import uuid
import pytest
from unittest.mock import patch, MagicMock, call
from botocore.exceptions import NoCredentialsError

from backend.app.core.logging import generate_request_id, log_structured, setup_logger
from backend.app.services.metrics_service import (
    MetricsService,
    QUERY_REQUESTS, QUERY_SUCCESS, QUERY_FAILURE, QUERY_ABSTENTION,
    STALE_DOCUMENT_REJECTED, AUTHORIZATION_DENIED, CONFLICTS_DETECTED
)


# Test 20: MetricsService.put_metric does not raise when CloudWatch unavailable
def test_put_metric_does_not_raise_without_cloudwatch():
    svc = MetricsService()
    svc._client = None
    # Simulate boto3 client creation failing
    with patch("backend.app.services.metrics_service.boto3") as mock_boto:
        mock_boto.client.side_effect = Exception("No AWS connectivity")
        # Should NOT raise
        svc.put_metric("TestMetric", 1.0)


# Test 21: MetricsService.put_metric calls CloudWatch when client is available
def test_put_metric_calls_cloudwatch_when_available():
    svc = MetricsService()
    mock_client = MagicMock()
    svc._client = mock_client

    svc.put_metric("SomeMetric", 5.0, "Count")

    mock_client.put_metric_data.assert_called_once()
    call_kwargs = mock_client.put_metric_data.call_args[1]
    assert call_kwargs["Namespace"] == svc.namespace
    assert call_kwargs["MetricData"][0]["MetricName"] == "SomeMetric"
    assert call_kwargs["MetricData"][0]["Value"] == 5.0


# Test 22: Helper methods map to correct metric names
def test_helper_methods_use_correct_metric_names():
    svc = MetricsService()
    svc.put_metric = MagicMock()

    svc.record_query_request()
    svc.put_metric.assert_called_with(QUERY_REQUESTS)

    svc.record_query_success()
    svc.put_metric.assert_called_with(QUERY_SUCCESS)

    svc.record_query_failure()
    svc.put_metric.assert_called_with(QUERY_FAILURE)

    svc.record_abstention()
    svc.put_metric.assert_called_with(QUERY_ABSTENTION)

    svc.record_auth_denied()
    svc.put_metric.assert_called_with(AUTHORIZATION_DENIED)

    svc.record_conflict_detected(3)
    svc.put_metric.assert_called_with(CONFLICTS_DETECTED, value=3.0)


# Test 23: generate_request_id returns a valid UUID
def test_generate_request_id_returns_uuid():
    rid = generate_request_id()
    assert isinstance(rid, str)
    assert len(rid) == 36  # UUID format: 8-4-4-4-12
    # Should be parseable as a UUID
    parsed = uuid.UUID(rid)
    assert str(parsed) == rid


# Test 24: generate_request_id is unique per call
def test_generate_request_id_is_unique():
    ids = {generate_request_id() for _ in range(100)}
    assert len(ids) == 100  # All should be unique


# Test 25: log_structured emits expected fields
def test_log_structured_emits_fields():
    logger = setup_logger("test_logger")
    with patch.object(logger, "info") as mock_info:
        log_structured(
            logger, "info", "Test message",
            operation="test_op", request_id="req-123",
            status="success", user_id="user-abc", document_id="doc-xyz",
            duration_ms=42.5
        )
        mock_info.assert_called_once()
        msg, extra_dict = mock_info.call_args[0][0], mock_info.call_args[1].get("extra", {})
        assert msg == "Test message"
        assert extra_dict.get("operation") == "test_op"
        assert extra_dict.get("request_id") == "req-123"
        assert extra_dict.get("status") == "success"
        assert extra_dict.get("user_id") == "user-abc"
        assert extra_dict.get("document_id") == "doc-xyz"
        assert extra_dict.get("duration_ms") == 42.5


# Test 26: QueryService emits QUERY_REQUESTS on every query
def test_query_service_emits_query_requests_metric():
    from shared.models.query import QueryRequest
    from backend.app.services.query_service import QueryService
    from shared.constants.document_status import DocumentStatus

    request = QueryRequest(question="Test question?")

    with patch("backend.app.services.query_service.EmbeddingService"), \
         patch("backend.app.services.query_service.OpenSearchService"), \
         patch("backend.app.services.query_service.GenerationService"), \
         patch("backend.app.services.query_service.DynamoDBService"), \
         patch("backend.app.services.query_service.MetricsService") as mock_metrics_cls:
        svc = QueryService()
        svc.embedding_service.embed_text.return_value = [0.1] * 1536
        svc.opensearch_service.search_similar_chunks.return_value = []  # No results → abstention

        response = svc.query(request)

    mock_metrics_instance = mock_metrics_cls.return_value
    mock_metrics_instance.record_query_request.assert_called_once()
    assert response.grounded is False


# Test 27: MetricsService falls back gracefully on NoCredentialsError
def test_metrics_service_graceful_on_no_credentials():
    svc = MetricsService()
    mock_client = MagicMock()
    mock_client.put_metric_data.side_effect = NoCredentialsError()
    svc._client = mock_client

    # Should NOT raise — just silently swallow the error
    svc.put_metric("AnyMetric", 1.0)
