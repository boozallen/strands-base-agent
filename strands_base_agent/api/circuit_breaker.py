# Copyright 2026 Booz Allen Hamilton Inc.
# SPDX-License-Identifier: Apache-2.0
"""MCP circuit breaker used by the /api/v1/query route."""

import enum
import logging
import threading
import time

logger = logging.getLogger(__name__)


class McpCircuitOpenError(RuntimeError):
    """Raised when the MCP circuit breaker is open."""


class _CircuitState(enum.Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class _CircuitBreaker:
    """Three-state circuit breaker: closed, open, half-open."""

    def __init__(self, threshold: int = 5, reset_interval: float = 60.0):
        self._lock = threading.RLock()
        self._threshold = threshold
        self._reset_interval = reset_interval
        self._failure_count = 0
        self._state = _CircuitState.CLOSED
        self._opened_at: float = 0.0

    @property
    def state(self) -> _CircuitState:
        with self._lock:
            return self._state

    @property
    def failure_count(self) -> int:
        with self._lock:
            return self._failure_count

    def check(self) -> None:
        with self._lock:
            if self._state == _CircuitState.CLOSED:
                return
            if self._state == _CircuitState.HALF_OPEN:
                return
            elapsed = time.monotonic() - self._opened_at
            if elapsed >= self._reset_interval:
                self._state = _CircuitState.HALF_OPEN
                logger.info("MCP circuit breaker transitioning to half-open")
                return
            raise McpCircuitOpenError(f"MCP circuit breaker is open ({elapsed:.0f}s / {self._reset_interval:.0f}s)")

    def record_failure(self) -> None:
        with self._lock:
            self._failure_count += 1
            if self._failure_count >= self._threshold:
                self._state = _CircuitState.OPEN
                self._opened_at = time.monotonic()
                logger.warning(
                    "MCP circuit breaker opened after %d consecutive failures",
                    self._failure_count,
                )

    def record_success(self) -> None:
        with self._lock:
            if self._failure_count > 0 or self._state != _CircuitState.CLOSED:
                logger.info("MCP circuit breaker closed after successful recreation")
            self._failure_count = 0
            self._state = _CircuitState.CLOSED
