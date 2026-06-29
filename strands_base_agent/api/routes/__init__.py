# Copyright 2026 Booz Allen Hamilton Inc.
# SPDX-License-Identifier: Apache-2.0
"""API routes package for HTTP endpoint definitions."""

from strands_base_agent.api.routes.chat_history import router as chat_history_router
from strands_base_agent.api.routes.query import router as query_router

__all__ = [
    "chat_history_router",
    "query_router",
]
