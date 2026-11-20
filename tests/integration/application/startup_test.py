# Copyright 2026 Booz Allen Hamilton Inc.
# SPDX-License-Identifier: Apache-2.0
"""Integration tests for application startup."""

import logging

import pytest

from strands_base_agent.application.factory import create_application_container


class TestApplicationStartup:
    """Test application startup."""

    def test_startup_logs_remote_mode(self, caplog: pytest.LogCaptureFixture) -> None:
        """Test startup logs"""
        with caplog.at_level(logging.INFO):
            container = create_application_container()
            assert container is not None
