"""
tests/unit/test_router.py

Unit tests for CompiledRouter trie.
Validates:
  - Exact static routing.
  - Parameterized routing ({job_id}).
  - Duplicate route rejection during initialization.
  - Ambiguous parameter route rejection.
  - 404 RouteNotFoundError and 405 MethodNotAllowedError.
"""

import pytest

from pulse.core.router import CompiledRouter
from pulse.core.errors import RouteNotFoundError, MethodNotAllowedError


class TestCompiledRouter:
    def test_static_and_param_route_matching(self):
        router = CompiledRouter()
        router.add_route("GET", "/api/v1/health", "health_handler")
        router.add_route("GET", "/api/v1/jobs/{job_id}", "get_job_handler")
        router.add_route("POST", "/api/v1/jobs", "create_job_handler")

        # Static match
        h1, p1 = router.match("GET", "/api/v1/health")
        assert h1 == "health_handler"
        assert p1 == {}

        # Param match
        h2, p2 = router.match("GET", "/api/v1/jobs/job_12345")
        assert h2 == "get_job_handler"
        assert p2 == {"job_id": "job_12345"}

    def test_duplicate_route_rejection(self):
        router = CompiledRouter()
        router.add_route("POST", "/api/v1/jobs", "handler_1")
        with pytest.raises(ValueError, match="Duplicate route detected"):
            router.add_route("POST", "/api/v1/jobs", "handler_2")

    def test_ambiguous_parameter_conflict_rejection(self):
        router = CompiledRouter()
        router.add_route("GET", "/items/{item_id}", "h1")
        with pytest.raises(ValueError, match="Ambiguous route pattern"):
            router.add_route("GET", "/items/{product_id}", "h2")

    def test_not_found_error(self):
        router = CompiledRouter()
        router.add_route("GET", "/api/v1/health", "h1")
        with pytest.raises(RouteNotFoundError):
            router.match("GET", "/api/v1/nonexistent")

    def test_method_not_allowed_error(self):
        router = CompiledRouter()
        router.add_route("GET", "/api/v1/health", "h1")
        with pytest.raises(MethodNotAllowedError):
            router.match("POST", "/api/v1/health")
