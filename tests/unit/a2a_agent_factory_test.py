# Copyright 2026 Booz Allen Hamilton Inc.
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for A2A agent factory functionality.

Consolidated tests for A2A-specific agent creation functions, configuration processing,
and factory methods for remote operation mode.
"""

from unittest.mock import Mock, patch

import pytest

from foundry_agent_core import FunctionalDependencyContainer
from foundry_strands_agent import AgentConfig, AgentModelConfig, StrandsAgentFactory


class TestA2AAgentFactoryConsolidated:
    """Consolidated A2A agent factory tests."""

    @pytest.fixture
    def mock_container(self) -> FunctionalDependencyContainer:
        """Create mock dependency container for A2A testing."""
        container = FunctionalDependencyContainer()
        # Register AgentConfig factory with A2A configuration
        a2a_config = AgentConfig(
            model=AgentModelConfig(),
            agent_name="test-a2a-agent",
            agent_description="Test A2A agent description",
            agent_version="2.0.0",
            agent_port=8090,
        )
        container.register_factory(AgentConfig, lambda: a2a_config)

        return container

    @pytest.fixture
    def a2a_agent_factory(self, mock_container: FunctionalDependencyContainer) -> StrandsAgentFactory:
        """Create agent factory instance for A2A testing."""
        return StrandsAgentFactory(mock_container)

    @pytest.mark.parametrize(
        "test_scenario,config_params,expected_results,validation_checks",
        [
            # Configuration processing scenarios
            (
                "a2a_config_dict_conversion",
                {
                    "model": AgentModelConfig(
                        provider="bedrock", model_id="us.anthropic.claude-sonnet-4-20250514-v1:0"
                    ),
                    "agent_name": "a2a-test-agent",
                    "agent_description": "A2A test agent for unit testing",
                    "agent_version": "3.1.0",
                    "agent_port": 9090,
                },
                {
                    "model_provider": "bedrock",
                    "model_id": "us.anthropic.claude-sonnet-4-20250514-v1:0",
                    "excludes_a2a_fields": True,  # A2A fields should not be in config dict
                },
                ["model"],
            ),
            # Session configuration processing
            (
                "a2a_session_configuration",
                {
                    "model": AgentModelConfig(),
                    "agent_name": "session-a2a-agent",
                    "agent_version": "1.5.0",
                    "session_id": "a2a_session_123",
                    "session_type": "file",
                    "session_storage_dir": "/tmp/a2a_sessions",
                },
                {"session_id": "a2a_session_123", "session_type": "file", "session_storage_dir": "/tmp/a2a_sessions"},
                ["session_id", "session_type", "session_storage_dir"],
            ),
            # Agent state configuration processing
            (
                "a2a_agent_state_configuration",
                {
                    "model": AgentModelConfig(),
                    "agent_name": "stateful-a2a-agent",
                    "agent_version": "1.0.0",
                    "conversation_window_size": 50,
                    "conversation_truncate_results": True,
                    "agent_state_initial_values": {
                        "mode": "remote",
                        "agent_type": "a2a",
                        "capabilities": ["tool_execution", "multi_agent_communication"],
                    },
                },
                {
                    "conversation_window_size": 50,
                    "conversation_truncate_results": True,
                    "agent_state_values": {
                        "mode": "remote",
                        "agent_type": "a2a",
                        "capabilities": ["tool_execution", "multi_agent_communication"],
                    },
                },
                ["conversation_window_size", "conversation_truncate_results", "agent_state_initial_values"],
            ),
        ],
    )
    def test_a2a_configuration_processing(
        self,
        a2a_agent_factory: StrandsAgentFactory,
        test_scenario: str,
        config_params: dict,
        expected_results: dict,
        validation_checks: list,
    ) -> None:
        """Test comprehensive A2A configuration processing scenarios."""
        config = AgentConfig(**config_params)
        result = a2a_agent_factory._config_to_dict(config)

        # Scenario-specific validations
        if test_scenario == "a2a_config_dict_conversion":
            # Verify A2A fields are not directly in the config dict
            assert "agent_name" not in result
            assert "agent_description" not in result
            assert "agent_version" not in result
            assert "agent_port" not in result

            # But verify that the basic config fields are present
            assert result["model"]["provider"] == expected_results["model_provider"]
            assert result["model"]["model_id"] == expected_results["model_id"]

        elif test_scenario == "a2a_session_configuration":
            # Verify session fields are included
            for field, expected_value in expected_results.items():
                assert result[field] == expected_value

        elif test_scenario == "a2a_agent_state_configuration":
            # Verify agent state fields are included
            assert result["conversation_window_size"] == expected_results["conversation_window_size"]
            assert result["conversation_truncate_results"] == expected_results["conversation_truncate_results"]
            assert result["agent_state_initial_values"] == expected_results["agent_state_values"]

        # Verify field accessibility for validation checks
        for field in validation_checks:
            assert field in result or hasattr(config, field), f"Missing field: {field}"

    @pytest.mark.parametrize(
        "creation_scenario,config_params,tools,config_overrides,expected_behavior",
        [
            # Agent creation with A2A configuration
            (
                "a2a_configuration_creation",
                {
                    "model": AgentModelConfig(
                        provider="bedrock", model_id="us.anthropic.claude-sonnet-4-20250514-v1:0", temperature=0.2
                    ),
                    "agent_name": "production-a2a-agent",
                    "agent_description": "Production A2A agent for multi-agent communication",
                    "agent_version": "2.5.0",
                    "agent_port": 8080,
                    "system_prompt": "You are an A2A-enabled agent designed for multi-agent collaboration.",
                    "conversation_window_size": 75,
                    "agent_state_initial_values": {"agent_type": "a2a", "mode": "production"},
                },
                None,
                None,
                {
                    "agent_created": True,
                    "verify_system_prompt": "You are an A2A-enabled agent designed for multi-agent collaboration.",
                },
            ),
            # Agent creation with A2A tools
            (
                "a2a_tools_creation",
                {
                    "model": AgentModelConfig(),
                    "agent_name": "tools-a2a-agent",
                    "agent_version": "1.0.0",
                },
                [
                    lambda message, target_agent: f"Sent '{message}' to {target_agent}",  # a2a_communication_tool
                    lambda: ["agent1", "agent2", "agent3"],  # a2a_discovery_tool
                ],
                None,
                {"agent_created": True, "verify_tools_count": 2},
            ),
            # Agent creation with config overrides
            (
                "a2a_config_overrides_creation",
                {
                    "model": AgentModelConfig(),
                    "agent_name": "override-a2a-agent",
                    "agent_version": "1.0.0",
                },
                None,
                {
                    "system_prompt": "You are an A2A agent specialized in financial analysis.",
                    "conversation_window_size": 100,
                    "agent_state_initial_values": {
                        "agent_type": "a2a",
                        "specialization": "financial",
                        "version": "3.0.0",
                    },
                },
                {"agent_created": True, "verify_override_prompt": "financial analysis"},
            ),
        ],
    )
    @pytest.mark.asyncio
    async def test_a2a_agent_creation(
        self, creation_scenario: str, config_params: dict, tools: list, config_overrides: dict, expected_behavior: dict
    ) -> None:
        """Test comprehensive A2A agent creation scenarios."""
        # Setup container with A2A-specific configuration
        container = FunctionalDependencyContainer()
        a2a_config = AgentConfig(**config_params)
        container.register_factory(AgentConfig, lambda: a2a_config)

        agent_factory = StrandsAgentFactory(container)

        with patch("foundry_strands_agent.factory.Agent") as mock_agent_class:
            mock_agent_instance = Mock()
            mock_agent_class.return_value = mock_agent_instance

            # Execute agent creation
            if tools and config_overrides:
                result = await agent_factory.create_agent(tools=tools, config_overrides=config_overrides)
            elif tools:
                result = await agent_factory.create_agent(tools=tools)
            elif config_overrides:
                result = await agent_factory.create_agent(config_overrides=config_overrides)
            else:
                result = await agent_factory.create_agent()

            # Verify creation
            if expected_behavior.get("agent_created"):
                assert result is mock_agent_instance
                mock_agent_class.assert_called_once()

                # Get call arguments for verification
                call_kwargs = mock_agent_class.call_args[1]

                # Scenario-specific verifications
                if creation_scenario == "a2a_configuration_creation":
                    # Verify that the system prompt matches what we expect
                    assert call_kwargs["system_prompt"] == expected_behavior["verify_system_prompt"]
                    assert call_kwargs["state"] is not None
                    assert call_kwargs["conversation_manager"] is not None
                    assert call_kwargs["model"] is not None
                    assert "tools" in call_kwargs

                elif creation_scenario == "a2a_tools_creation":
                    assert call_kwargs["tools"] == tools
                    assert len(call_kwargs["tools"]) == expected_behavior["verify_tools_count"]

                elif creation_scenario == "a2a_config_overrides_creation":
                    assert expected_behavior["verify_override_prompt"] in call_kwargs["system_prompt"]

    @pytest.mark.parametrize(
        "validation_scenario,test_data,expected_outcome",
        [
            # Configuration validation - valid A2A config
            (
                "valid_a2a_configuration",
                {
                    "config": {
                        "model": {
                            "provider": "bedrock",
                            "model_id": "us.anthropic.claude-sonnet-4-20250514-v1:0",
                            "temperature": 0.3,
                        },
                        "system_prompt": "You are an A2A-enabled agent for multi-agent coordination.",
                        "tools": [],
                        "conversation_window_size": 50,
                        "agent_state_initial_values": {"mode": "a2a", "type": "coordinator"},
                    }
                },
                {"valid": True, "no_errors": True, "no_temperature_warnings": True},
            ),
            # Configuration validation - invalid temperature
            (
                "invalid_a2a_temperature",
                {
                    "config": {
                        "model": {
                            "provider": "bedrock",
                            "model_id": "us.anthropic.claude-sonnet-4-20250514-v1:0",
                            "temperature": 3.0,
                        },
                        "system_prompt": "You are an A2A agent.",
                        "tools": [],
                    }
                },
                {"valid": False, "temperature_error": True},
            ),
            # Session manager creation - file-based
            (
                "file_session_manager_creation",
                {
                    "config": {
                        "agent_name": "session-a2a-agent",
                        "session_id": "a2a_session_456",
                        "session_type": "file",
                        "session_storage_dir": "/tmp/a2a_sessions",
                    }
                },
                {"session_manager_created": True, "session_type": "file"},
            ),
            # Session manager creation - S3-based
            (
                "s3_session_manager_creation",
                {
                    "config": {
                        "agent_name": "s3-a2a-agent",
                        "session_id": "a2a_s3_session_789",
                        "session_type": "s3",
                        "session_s3_bucket": "a2a-agent-sessions",
                        "session_s3_prefix": "remote-agents/",
                    }
                },
                {"session_manager_created": True, "session_type": "s3"},
            ),
        ],
    )
    def test_a2a_factory_methods_and_validation(
        self, validation_scenario: str, test_data: dict, expected_outcome: dict
    ) -> None:
        """Test comprehensive A2A factory methods and validation scenarios."""
        if validation_scenario in ["valid_a2a_configuration", "invalid_a2a_temperature"]:
            container = FunctionalDependencyContainer()
            agent_factory = StrandsAgentFactory(container)
            validation_result = agent_factory.validate_agent_configuration(test_data["config"])

            if expected_outcome.get("valid"):
                assert validation_result["valid"] is True
                assert len(validation_result["errors"]) == 0
                if expected_outcome.get("no_temperature_warnings"):
                    temperature_warnings = [w for w in validation_result["warnings"] if "temperature" in w.lower()]
                    assert len(temperature_warnings) == 0
            else:
                assert validation_result["valid"] is False
                if expected_outcome.get("temperature_error"):
                    assert any("temperature" in error.lower() for error in validation_result["errors"])

        elif validation_scenario in ["file_session_manager_creation", "s3_session_manager_creation"]:
            config = AgentConfig(model=AgentModelConfig(), **test_data["config"])
            container = FunctionalDependencyContainer()
            container.register_factory(AgentConfig, lambda: config)
            agent_factory = StrandsAgentFactory(container)

            if expected_outcome["session_type"] == "file":
                with (
                    patch("foundry_strands_agent.factory.EncryptedFileSessionManager") as mock_file_session,
                    patch("foundry_strands_agent.factory.load_encryption_key", return_value=b"\x00" * 32),
                ):
                    mock_session_instance = Mock()
                    mock_file_session.return_value = mock_session_instance

                    session_repository = agent_factory._create_session_manager(
                        session_id="a2a_session_456", session_type="file"
                    )

                    assert session_repository is mock_session_instance

            elif expected_outcome["session_type"] == "s3":
                with patch("foundry_strands_agent.factory.S3SessionManager") as mock_s3_session:
                    mock_session_instance = Mock()
                    mock_s3_session.return_value = mock_session_instance

                    session_repository = agent_factory._create_session_repository(config)

                    assert session_repository is mock_session_instance
                    mock_s3_session.assert_called_once_with(
                        session_id="a2a_s3_session_789",
                        bucket="a2a-agent-sessions",
                        prefix="remote-agents/",
                        region=None,
                    )
