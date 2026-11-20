# Copyright 2026 Booz Allen Hamilton Inc.
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for the bearer-auth exemption predicate used by the server middleware."""

import pytest

from strands_base_agent.server import is_auth_exempt


class TestIsAuthExempt:
    @pytest.mark.parametrize(
        "path",
        [
            "/.well-known/agent.json",
            "/.well-known/agent-card.json",
        ],
    )
    def test_both_a2a_discovery_documents_pass_unauthenticated(self, path):
        assert is_auth_exempt("GET", path)

    @pytest.mark.parametrize(
        "path",
        [
            "/.well-known/agent.json/",
            "/.well-known/agent-card.json/",
        ],
    )
    def test_exemption_survives_trailing_slash_normalization(self, path):
        assert is_auth_exempt("GET", path)

    def test_health_probe_passes_unauthenticated(self):
        assert is_auth_exempt("GET", "/api/v1/health")

    def test_options_preflight_passes_unauthenticated(self):
        assert is_auth_exempt("OPTIONS", "/api/v1/query")

    @pytest.mark.parametrize(
        "path",
        [
            "/api/v1/query",
            "/api/v1/chat-history",
            "/.well-known/other.json",
            "/",
        ],
    )
    def test_everything_else_requires_auth(self, path):
        assert not is_auth_exempt("GET", path)
