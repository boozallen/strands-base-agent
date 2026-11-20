# Copyright 2026 Booz Allen Hamilton Inc.
# SPDX-License-Identifier: Apache-2.0
"""Tests for runtime container singleton."""

from unittest.mock import MagicMock

import pytest

from strands_base_agent.application.runtime_container import (
    get_dependency_container,
    set_runtime_container,
)


class TestRuntimeContainer:
    def test_get_container_raises_when_not_initialized(self, monkeypatch):
        import strands_base_agent.application.runtime_container as mod

        monkeypatch.setattr(mod, "_app_container", None)

        with pytest.raises(RuntimeError, match="Dependency container not initialized"):
            get_dependency_container()

    def test_set_and_get_container(self, monkeypatch):
        import strands_base_agent.application.runtime_container as mod

        monkeypatch.setattr(mod, "_app_container", None)

        mock_container = MagicMock()
        set_runtime_container(mock_container)
        result = get_dependency_container()
        assert result is mock_container

        # Cleanup
        monkeypatch.setattr(mod, "_app_container", None)
