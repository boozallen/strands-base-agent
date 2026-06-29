# Copyright 2026 Booz Allen Hamilton Inc.
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for router configuration."""

from foundry_agent_fastapi import health_router

from strands_base_agent.api.routes.query import router as query_router


class TestRouterConfiguration:
    def test_query_router_prefix_and_tags(self):
        assert query_router.prefix == "/api/v1/query"
        assert "query" in query_router.tags

    def test_query_router_has_query_endpoint(self):
        route_paths = [route.path for route in query_router.routes]
        assert any("/query" in path or path == "" for path in route_paths)

    def test_health_router_has_health_endpoint(self):
        route_paths = [route.path for route in health_router.routes]
        assert any("/health" in path for path in route_paths)
