# Copyright 2026 Booz Allen Hamilton Inc.
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for A2A error handling and validation scenarios.

Ultra-consolidated comprehensive test for all A2A error handling, configuration validation,
and edge cases for the A2A (Agent-to-Agent) remote server functionality.
"""

import os
from unittest.mock import patch

import pytest

from foundry_agent_core import InvalidConfigurationError
from foundry_strands_agent import AgentConfig, AgentModelConfig


class TestA2AErrorHandlingUltraConsolidated:
    """Ultra-consolidated comprehensive A2A error handling and validation tests."""

    @pytest.mark.parametrize(
        "test_category,test_scenario,test_config,expected_behavior,expected_values",
        [
            # Configuration validation errors
            (
                "config_validation",
                "invalid_port",
                {"env_vars": {"STRANDS_AGENT_PORT": "invalid_port"}},
                {"should_raise": InvalidConfigurationError, "error_contains": "must be a valid integer"},
                {},
            ),
            # Data format validation errors
            (
                "data_format",
                "invalid_json_agent_state",
                {
                    "env_vars": {
                        "STRANDS_AGENT_STATE_INITIAL_VALUES": "invalid json {",
                    }
                },
                {"should_raise": InvalidConfigurationError, "error_contains": "must be valid JSON"},
                {},
            ),
            (
                "data_format",
                "invalid_conversation_window",
                {"env_vars": {"STRANDS_CONVERSATION_WINDOW_SIZE": "invalid"}},
                {"should_raise": InvalidConfigurationError, "error_contains": "must be a valid integer"},
                {},
            ),
            # Component configuration errors
            (
                "component_config",
                "empty_session_id",
                {"direct_config": {"session_id": "  "}},
                {"should_raise": (InvalidConfigurationError, ValueError, Exception), "error_contains": None},
                {},
            ),
            (
                "component_config",
                "memory_without_knowledge_base",
                {"direct_config": {"enable_memory": True, "knowledge_base_id": None}},
                {
                    "should_raise": InvalidConfigurationError,
                    "error_contains": "knowledge_base_id is required when enable_memory is True",
                },
                {},
            ),
            # System validation and recovery
            (
                "system_validation",
                "valid_boundary_values",
                {"env_vars": {"STRANDS_CONVERSATION_WINDOW_SIZE": "1", "STRANDS_AGENT_PORT": "1"}},
                {"should_succeed": True},
                {"conversation_window_size": 1, "agent_port": 1},
            ),
            (
                "system_validation",
                "valid_type_coercion",
                {
                    "env_vars": {
                        "STRANDS_AGENT_PORT": "8080",
                        "STRANDS_CONVERSATION_TRUNCATE_RESULTS": "true",
                        "STRANDS_TEMPERATURE": "0.3",
                    }
                },
                {"should_succeed": True},
                {"agent_port": 8080, "conversation_truncate_results": True, "model.temperature": 0.3},
            ),
            # Edge cases
            (
                "edge_cases",
                "zero_temperature",
                {"env_vars": {"STRANDS_TEMPERATURE": "0.0"}},
                {"should_succeed": True},
                {"model.temperature": 0.0},
            ),
        ],
    )
    def test_a2a_error_handling_comprehensive(
        self, test_category: str, test_scenario: str, test_config: dict, expected_behavior: dict, expected_values: dict
    ) -> None:
        """Ultra-comprehensive test for all A2A error handling and validation scenarios."""
        # Handle environment variable-based tests
        if test_config.get("env_vars"):
            with patch.dict(os.environ, test_config["env_vars"], clear=True):
                if expected_behavior.get("should_raise"):
                    with pytest.raises(Exception):
                        AgentConfig.from_env()
                else:
                    # Success scenario
                    config = AgentConfig.from_env()
                    assert config is not None

                    # Verify expected values
                    for field, expected_value in expected_values.items():
                        if "." in field:  # Handle nested fields like model.temperature
                            obj, attr = field.split(".", 1)
                            actual_value = getattr(getattr(config, obj), attr)
                            assert actual_value == expected_value, (
                                f"{field}: expected {expected_value}, got {actual_value}"
                            )
                        else:
                            actual_value = getattr(config, field)
                            assert actual_value == expected_value, (
                                f"{field}: expected {expected_value}, got {actual_value}"
                            )

        # Handle direct configuration-based tests
        elif test_config.get("direct_config"):
            model_config = AgentModelConfig()

            if expected_behavior.get("should_raise"):
                with pytest.raises(expected_behavior["should_raise"]) as exc_info:
                    AgentConfig(model=model_config, **test_config["direct_config"])

                error_msg = str(exc_info.value)
                if expected_behavior.get("error_contains"):
                    assert expected_behavior["error_contains"] in error_msg
                if expected_behavior.get("error_context"):
                    for context in expected_behavior["error_context"]:
                        assert context in error_msg
            else:
                # Success scenario
                config = AgentConfig(model=model_config, **test_config["direct_config"])
                assert config is not None

                # Verify expected values
                for field, expected_value in expected_values.items():
                    if "." in field:  # Handle nested fields like model.temperature
                        obj, attr = field.split(".", 1)
                        actual_value = getattr(getattr(config, obj), attr)
                        assert actual_value == expected_value, f"{field}: expected {expected_value}, got {actual_value}"
                    else:
                        actual_value = getattr(config, field)
                        assert actual_value == expected_value, f"{field}: expected {expected_value}, got {actual_value}"
