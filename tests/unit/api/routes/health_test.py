# Copyright 2026 Booz Allen Hamilton Inc.
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for health check endpoint."""

from foundry_agent_fastapi.routes.health import health_check


class TestHealthCheckEndpoint:
    async def test_health_check_success(self):
        result = await health_check()
        assert result == {"status": "healthy"}
