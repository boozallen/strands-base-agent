# Copyright 2026 Booz Allen Hamilton Inc.
# SPDX-License-Identifier: Apache-2.0
"""Process-wide dependency container for FastAPI and other entrypoints.

Using a dedicated module avoids a subtle bug when the app is started with
``python -m strands_base_agent.server``: that executes ``server.py`` as
``__main__``, while ``from strands_base_agent.server import ...`` loads a
*second* module object. A ``container`` global on ``server`` would only be set
on one of those; handlers would read ``None`` from the other.

This module is imported once under a stable name, so the singleton is shared.
"""

from __future__ import annotations

from foundry_agent_core import DependencyContainer

_app_container: DependencyContainer | None = None


def set_runtime_container(container: DependencyContainer) -> None:
    """Store the application container after it is created at startup."""
    global _app_container
    _app_container = container


def get_dependency_container() -> DependencyContainer:
    """Return the container set by :func:`set_runtime_container`.

    Raises:
        RuntimeError: If the container has not been set (server not started).
    """
    if _app_container is None:
        raise RuntimeError("Dependency container not initialized. Ensure application has started properly.")
    return _app_container
