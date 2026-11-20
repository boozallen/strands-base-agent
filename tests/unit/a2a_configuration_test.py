# Copyright 2026 Booz Allen Hamilton Inc.
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for A2A configuration functionality.

Tests the specific A2A-related configuration processing functions, environment variable
parsing, and agent identity configuration for remote operation mode.
"""

import os
from unittest.mock import patch

import pytest

from foundry_agent_core import InvalidConfigurationError
from foundry_strands_agent import AgentConfig, AgentModelConfig


class TestA2AConfigurationComprehensive:
    """Comprehensive test for all A2A configuration scenarios."""

    @pytest.mark.parametrize(
        "test_scenario,env_vars,expected_results,should_raise,validation_checks",
        [
            # Complete A2A configuration scenarios
            (
                "complete_remote_config",
                {
                    "STRANDS_AGENT_NAME": "financial-analyzer",
                    "STRANDS_AGENT_DESCRIPTION": "AI agent for financial analysis and reporting",
                    "STRANDS_AGENT_VERSION": "2.1.0",
                    "STRANDS_AGENT_PORT": "8080",
                    "STRANDS_SYSTEM_PROMPT": "You are a financial agent",
                    "STRANDS_MODEL_PROVIDER": "bedrock",
                },
                {
                    "agent_name": "financial-analyzer",
                    "agent_description": "AI agent for financial analysis and reporting",
                    "agent_version": "2.1.0",
                    "agent_port": 8080,
                    "system_prompt": "You are a financial agent",
                    "model.provider": "bedrock",
                },
                False,
                ["agent_name", "agent_description", "agent_version", "agent_port"],
            ),
            # Default configuration (no environment variables)
            (
                "default_config",
                {},
                {
                    "agent_name": "strands-base-agent",
                    "agent_description": "A general-purpose AI agent powered by AWS Strands Agent framework",
                    "agent_version": "1.0",
                    "agent_port": None,
                },
                False,
                ["agent_name", "agent_description", "agent_version"],
            ),
            # Port parsing scenarios
            ("valid_port", {"STRANDS_AGENT_PORT": "8080"}, {"agent_port": 8080}, False, ["agent_port"]),
            ("invalid_port", {"STRANDS_AGENT_PORT": "invalid_port"}, {}, True, []),
            # Edge case scenarios
            (
                "empty_string_values",
                {
                    "STRANDS_OPERATION_MODE": "remote",
                    "STRANDS_AGENT_NAME": "",
                    "STRANDS_AGENT_VERSION": "",
                },
                {},
                True,
                [],
            ),
        ],
    )
    def test_a2a_configuration_comprehensive(
        self, test_scenario: str, env_vars: dict, expected_results: dict, should_raise: bool, validation_checks: list
    ) -> None:
        """Comprehensive test for all A2A configuration scenarios."""
        with patch.dict(os.environ, env_vars, clear=True):
            if should_raise:
                with pytest.raises((InvalidConfigurationError, ValueError, Exception)):
                    AgentConfig.from_env()
            else:
                config = AgentConfig.from_env()

                # Verify expected results
                for field, expected_value in expected_results.items():
                    if "." in field:  # Handle nested fields like model.provider
                        obj, attr = field.split(".", 1)
                        actual_value = getattr(getattr(config, obj), attr)
                    else:
                        actual_value = getattr(config, field)

                    assert actual_value == expected_value, (
                        f"Field {field}: expected {expected_value}, got {actual_value}"
                    )

                # Verify field accessibility for validation checks
                for field in validation_checks:
                    assert hasattr(config, field), f"Config missing field: {field}"

    def test_a2a_agent_config_direct_validation(self) -> None:
        """Test direct AgentConfig creation with A2A fields."""
        model_config = AgentModelConfig()

        # Test valid configuration with all A2A fields
        config = AgentConfig(
            model=model_config,
            agent_name="test-agent",
            agent_description="Test A2A agent",
            agent_version="1.5.0",
            agent_port=9000,
        )

        # Verify all A2A fields are accessible and correct
        assert hasattr(config, "agent_name")
        assert hasattr(config, "agent_description")
        assert hasattr(config, "agent_version")
        assert hasattr(config, "agent_port")

        # Verify values are correct
        assert config.agent_name == "test-agent"
        assert config.agent_description == "Test A2A agent"
        assert config.agent_version == "1.5.0"
        assert config.agent_port == 9000
