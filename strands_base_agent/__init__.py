# Copyright 2026 Booz Allen Hamilton Inc.
# SPDX-License-Identifier: Apache-2.0
"""Strands Base Agent - Reference implementation using AWS Strands Agents SDK.

This package provides a complete application bootstrap framework for building
agent-powered applications with clean separation between application logic
and interface implementations.
"""

# Application bootstrap and query processing
from strands_base_agent.application import (
    create_application_container,
    graceful_shutdown,
    setup_signal_handlers,
)
from strands_base_agent.main import process_query

__all__ = [
    # Core query processing
    "process_query",
    # Application bootstrap
    "create_application_container",
    # Lifecycle management
    "setup_signal_handlers",
    "graceful_shutdown",
]
