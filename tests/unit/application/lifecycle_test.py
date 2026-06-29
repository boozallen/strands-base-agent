# Copyright 2026 Booz Allen Hamilton Inc.
# SPDX-License-Identifier: Apache-2.0
"""Tests for application lifecycle management."""

import asyncio
import logging
import signal
from unittest.mock import patch

import pytest

from strands_base_agent.application.lifecycle import (
    boot_system,
    graceful_shutdown,
    setup_signal_handlers,
)


class TestBootSystem:
    def test_boot_system_loads_env_and_logging(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        env_file = tmp_path / ".env"
        env_file.write_text("TEST_VAR=hello\n")
        monkeypatch.delenv("STRANDS_IGNORE_DOTENV", raising=False)

        boot_system()

    def test_boot_system_skips_dotenv_when_ignore_set(self, monkeypatch):
        monkeypatch.setenv("STRANDS_IGNORE_DOTENV", "1")

        with patch("strands_base_agent.application.lifecycle._load_environment_config") as mock_load:
            boot_system()
            mock_load.assert_not_called()


class TestSetupSignalHandlers:
    def test_returns_asyncio_event(self):
        event = setup_signal_handlers()
        assert isinstance(event, asyncio.Event)
        assert not event.is_set()

    def test_signal_handler_sets_event(self):
        event = setup_signal_handlers()

        # Simulate SIGTERM signal
        handler = signal.getsignal(signal.SIGTERM)
        handler(signal.SIGTERM, None)

        assert event.is_set()

    def test_signal_handler_calls_original_handler(self):
        original_called = []

        def original_handler(signum, _frame):
            original_called.append(signum)

        signal.signal(signal.SIGTERM, original_handler)
        event = setup_signal_handlers()

        handler = signal.getsignal(signal.SIGTERM)
        handler(signal.SIGTERM, None)

        assert event.is_set()
        assert signal.SIGTERM in original_called

    def test_registers_both_sigterm_and_sigint(self):
        setup_signal_handlers()

        sigterm_handler = signal.getsignal(signal.SIGTERM)
        sigint_handler = signal.getsignal(signal.SIGINT)

        assert sigterm_handler is not signal.SIG_DFL
        assert sigint_handler is not signal.SIG_DFL


class TestGracefulShutdown:
    @pytest.mark.asyncio
    async def test_graceful_shutdown_completes(self, caplog):
        with caplog.at_level(logging.INFO):
            await graceful_shutdown()

        assert "Beginning graceful shutdown..." in caplog.text
        assert "Graceful shutdown completed" in caplog.text

    @pytest.mark.asyncio
    async def test_graceful_shutdown_logs_completion(self, caplog):
        with caplog.at_level(logging.INFO):
            await graceful_shutdown()

        assert "Application cleanup completed" in caplog.text
