from unittest.mock import MagicMock

import pytest
from opentelemetry import trace

from infrastructure.tracing.processors.span import DependencyNameFixer


class TestDependencyNameFixer:
    @pytest.fixture
    def fixer(self):
        return DependencyNameFixer()

    @pytest.fixture
    def mock_span(self):
        span = MagicMock(spec=trace.Span)
        span.is_recording.return_value = True
        # Use a real dict for attributes to test getattr(span, "attributes", {})
        span.attributes = {}
        # Simple mock for span kind
        kind = MagicMock()
        kind.name = "CLIENT"
        span.kind = kind
        return span

    def test_fixer_replaces_generic_get_name(self, fixer, mock_span):
        mock_span.name = "GET"
        mock_span.attributes = {"http.url": "https://api.example.com/v1/data"}

        fixer.on_start(mock_span)

        mock_span.update_name.assert_called_with("GET api.example.com")

    def test_fixer_replaces_generic_post_name(self, fixer, mock_span):
        mock_span.name = "POST"
        mock_span.attributes = {"url.full": "https://auth.example.com/login"}

        fixer.on_start(mock_span)

        mock_span.update_name.assert_called_with("POST auth.example.com")

    def test_fixer_uses_server_address(self, fixer, mock_span):
        mock_span.name = "HTTP"
        mock_span.attributes = {"http.request.method": "PUT", "server.address": "storage.example.com"}

        fixer.on_start(mock_span)

        mock_span.update_name.assert_called_with("PUT storage.example.com")

    def test_fixer_fallback_to_dependency_name(self, fixer, mock_span):
        mock_span.name = "POST"
        mock_span.attributes = {}  # Missing host/url

        fixer.on_start(mock_span)

        # falls back to '<METHOD> Dependency' using mock_span.name
        mock_span.update_name.assert_called_with("POST Dependency")

    def test_fixer_ignores_descriptive_names(self, fixer, mock_span):
        mock_span.name = "Custom Span Name"

        fixer.on_start(mock_span)

        mock_span.update_name.assert_not_called()

    def test_fixer_handles_peer_address(self, fixer, mock_span):
        mock_span.name = "GET"
        mock_span.attributes = {"network.peer.address": "1.2.3.4", "http.method": "GET"}

        fixer.on_start(mock_span)

        mock_span.update_name.assert_called_with("GET 1.2.3.4")
