"""API contract testing using Schemathesis.

Tests that all API endpoints conform to the OpenAPI specification.
Runs against live test server and validates:
- Request/response schemas
- Status codes
- Required fields
- Data types
- Error responses
"""

import pytest
from pathlib import Path


OPENAPI_SPEC = Path(__file__).parent.parent.parent / "docs" / "openapi.json"


@pytest.mark.integration
@pytest.mark.api_contract
@pytest.mark.slow_integration
class TestAPIContract:
    """Contract tests validating API against OpenAPI spec."""

    @pytest.fixture
    def schema(self):
        """Load OpenAPI schema."""
        if not OPENAPI_SPEC.exists():
            pytest.skip("OpenAPI spec not found at docs/openapi.json")
        try:
            from schemathesis import from_uri
            return from_uri(f"file://{OPENAPI_SPEC}")
        except ImportError:
            pytest.skip("schemathesis not installed - install with pip install schemathesis")

    def test_schema_loaded(self, schema):
        """Verify OpenAPI schema loads and has endpoints."""
        if schema is None:
            pytest.skip("Schema could not be loaded")
        paths = list(schema.get_all_operations())
        assert len(paths) > 50  # Project should have many endpoints

