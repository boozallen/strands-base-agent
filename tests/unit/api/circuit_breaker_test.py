# Copyright 2026 Booz Allen Hamilton Inc.
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for _CircuitBreaker, used by the /api/v1/query route."""

from unittest.mock import patch

import pytest

from strands_base_agent.api.circuit_breaker import McpCircuitOpenError, _CircuitBreaker, _CircuitState


class TestCircuitBreakerClosedState:
    def test_circuit_remains_closed_below_threshold(self):
        circuit = _CircuitBreaker(threshold=5)
        for _ in range(4):
            circuit.record_failure()

        assert circuit.state == _CircuitState.CLOSED
        assert circuit.failure_count == 4
        circuit.check()

    def test_success_resets_failure_counter(self):
        circuit = _CircuitBreaker(threshold=5)
        for _ in range(3):
            circuit.record_failure()

        circuit.record_success()

        assert circuit.failure_count == 0
        assert circuit.state == _CircuitState.CLOSED


class TestCircuitBreakerOpenState:
    def test_circuit_opens_after_threshold_failures(self):
        circuit = _CircuitBreaker(threshold=3)
        for _ in range(3):
            circuit.record_failure()

        assert circuit.state == _CircuitState.OPEN

    def test_open_circuit_rejects_check(self):
        circuit = _CircuitBreaker(threshold=1, reset_interval=60.0)
        circuit.record_failure()

        with pytest.raises(McpCircuitOpenError, match="open"):
            circuit.check()


class TestCircuitBreakerHalfOpenState:
    def test_transitions_to_half_open_after_reset_interval(self):
        with patch("strands_base_agent.api.circuit_breaker.time.monotonic", return_value=100.0):
            circuit = _CircuitBreaker(threshold=1, reset_interval=60.0)
            circuit.record_failure()

        with patch("strands_base_agent.api.circuit_breaker.time.monotonic", return_value=161.0):
            circuit.check()

        assert circuit.state == _CircuitState.HALF_OPEN

    def test_successful_probe_closes_circuit(self):
        with patch("strands_base_agent.api.circuit_breaker.time.monotonic", return_value=100.0):
            circuit = _CircuitBreaker(threshold=1, reset_interval=60.0)
            circuit.record_failure()

        with patch("strands_base_agent.api.circuit_breaker.time.monotonic", return_value=161.0):
            circuit.check()
            circuit.record_success()

        assert circuit.state == _CircuitState.CLOSED
        assert circuit.failure_count == 0

    def test_failed_probe_reopens_circuit(self):
        with patch("strands_base_agent.api.circuit_breaker.time.monotonic", return_value=100.0):
            circuit = _CircuitBreaker(threshold=1, reset_interval=60.0)
            circuit.record_failure()

        with patch("strands_base_agent.api.circuit_breaker.time.monotonic", return_value=161.0):
            circuit.check()
            circuit.record_failure()

        assert circuit.state == _CircuitState.OPEN
        with patch("strands_base_agent.api.circuit_breaker.time.monotonic", return_value=170.0):
            with pytest.raises(McpCircuitOpenError):
                circuit.check()
