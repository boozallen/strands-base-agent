# Copyright 2026 Booz Allen Hamilton Inc.
# SPDX-License-Identifier: Apache-2.0
"""Application layer for Strands Base Agent bootstrap and lifecycle management.

This module provides application factory functions and lifecycle management
for coordinating all infrastructure components built in previous phases.
"""

from strands_base_agent.application.factory import create_application_container
from strands_base_agent.application.lifecycle import (
    graceful_shutdown,
    setup_signal_handlers,
)

__all__ = [
    "create_application_container",
    "setup_signal_handlers",
    "graceful_shutdown",
]
