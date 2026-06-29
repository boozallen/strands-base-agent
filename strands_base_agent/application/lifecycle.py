# Copyright 2026 Booz Allen Hamilton Inc.
# SPDX-License-Identifier: Apache-2.0
"""Application lifecycle management and shutdown coordination.

Implements startup and shutdown orchestration functions that coordinate service
lifecycle using existing AgentService.service_lifecycle() context manager
patterns, with signal handling for graceful shutdown.
"""

import asyncio
import logging
import os
import signal
from pathlib import Path
from time import gmtime
from types import FrameType

from dotenv import load_dotenv

# Global shutdown event for coordinated shutdown signaling
_shutdown_event: asyncio.Event | None = None


def _load_environment_config() -> None:
    """Load configuration from .env file if it exists."""
    env_file = Path(".env")
    if env_file.exists():
        load_dotenv(env_file)


def _initialize_logging() -> None:
    log_level = os.getenv("LOG_LEVEL", "DEBUG").upper()

    # ISO 8601:
    logging.Formatter.converter = gmtime
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s.%(msecs)03dZ %(threadName)-11s %(levelname)-5s %(name)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )


def boot_system() -> None:
    """Perform application system bootstrapping."""
    if not os.getenv("STRANDS_IGNORE_DOTENV", False):
        _load_environment_config()

    _initialize_logging()


def setup_signal_handlers() -> asyncio.Event:
    """Setup signal handlers for graceful shutdown.

    Registers signal handlers for SIGTERM and SIGINT that coordinate
    application shutdown through an asyncio Event.

    Returns:
        asyncio.Event that will be set when shutdown is requested

    Note:
        This function should be called once during application startup
    """
    global _shutdown_event
    _shutdown_event = asyncio.Event()

    original_handlers = {}

    def signal_handler(signum: int, frame: FrameType | None) -> None:
        """Handle shutdown signals by setting the shutdown event."""
        logging.info("Received signal %s, initiating graceful shutdown", signum)
        if _shutdown_event:
            _shutdown_event.set()
        if signum in original_handlers and original_handlers[signum]:
            original_handlers[signum](signum, frame)

    # Register handlers for common shutdown signals
    original_handlers[signal.SIGTERM] = signal.signal(signal.SIGTERM, signal_handler)
    original_handlers[signal.SIGINT] = signal.signal(signal.SIGINT, signal_handler)

    logging.info("Signal handlers registered for graceful shutdown")
    return _shutdown_event


async def graceful_shutdown() -> None:
    """Perform graceful shutdown of application resources.

    Coordinates shutdown of application components with proper logging
    for operational monitoring. This function should be called after
    receiving a shutdown signal.

    Note:
        This function handles general application cleanup. Specific service
        cleanup should be handled by the AgentService.service_lifecycle()
        context manager.
    """
    logging.info("Beginning graceful shutdown...")

    try:
        # Application-level cleanup would go here
        # Service-specific cleanup is handled by service_lifecycle() context managers
        logging.info("Application cleanup completed")

    except Exception as e:
        logging.error("Error during graceful shutdown: %s", e)
        raise

    finally:
        logging.info("Graceful shutdown completed")
