# Copyright 2026 Booz Allen Hamilton Inc.
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for A2A server functionality.

Consolidated tests for A2A server startup logic, configuration, port/host selection,
and error handling scenarios.
"""

import os
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, Mock, patch

import pytest
from strands.multiagent.a2a.executor import StrandsA2AExecutor

from foundry_strands_agent import AgentConfig

from strands_base_agent.server import start_server


class TestA2AServerConsolidated:
    """Consolidated A2A server startup and configuration tests."""

    @pytest.mark.parametrize(
        "test_scenario,config_params,env_vars,expected_behavior,expected_values",
        [
            # A2A server startup scenarios
            (
                "custom_port_startup",
                {
                    "agent_name": "test-agent",
                    "agent_description": "Test agent description",
                    "agent_version": "2.1.0",
                    "agent_port": 9090,
                },
                {"HOST": "127.0.0.1", "PORT": "8000"},
                "successful_startup",
                {"host": "127.0.0.1", "port": 9090, "version": "2.1.0"},
            ),
            # Port priority scenarios
            (
                "port_priority_agent_over_env",
                {"agent_version": "1.0", "agent_port": 9999},
                {"PORT": "8080"},
                "successful_startup",
                {"host": "0.0.0.0", "port": 9999, "version": "1.0"},
            ),
            (
                "port_fallback_to_env",
                {"agent_version": "1.0", "agent_port": None},
                {"PORT": "7777"},
                "successful_startup",
                {"host": "0.0.0.0", "port": 7777, "version": "1.0"},
            ),
            (
                "port_fallback_to_default",
                {"agent_version": "1.0", "agent_port": None},
                {},
                "successful_startup",
                {"host": "0.0.0.0", "port": 8000, "version": "1.0"},
            ),
            # Host configuration scenarios
            (
                "custom_host_from_env",
                {"agent_version": "1.0", "agent_port": None},
                {"HOST": "192.168.1.100"},
                "successful_startup",
                {"host": "192.168.1.100", "port": 8000, "version": "1.0"},
            ),
            (
                "default_host_no_env",
                {"agent_version": "1.0", "agent_port": None},
                {},
                "successful_startup",
                {"host": "0.0.0.0", "port": 8000, "version": "1.0"},
            ),
            # Combined scenarios
            (
                "custom_host_and_agent_port",
                {"agent_version": "2.0", "agent_port": 8090},
                {"HOST": "127.0.0.1", "PORT": "3000"},
                "successful_startup",
                {"host": "127.0.0.1", "port": 8090, "version": "2.0"},
            ),
            # Edge cases
            (
                "zero_port_edge_case",
                {"agent_version": "1.5", "agent_port": 0},
                {"HOST": "localhost"},
                "successful_startup",
                {"host": "localhost", "port": 0, "version": "1.5"},
            ),
            (
                "large_port_edge_case",
                {"agent_version": "1.8", "agent_port": 65535},
                {},
                "successful_startup",
                {"host": "0.0.0.0", "port": 65535, "version": "1.8"},
            ),
        ],
    )
    @patch("uvicorn.run")
    @patch("strands_base_agent.server._BearerCardA2AServer")
    @patch("strands_base_agent.server.create_application_container")
    def test_a2a_server_startup_and_configuration(
        self,
        mock_container,
        mock_a2a_server,
        mock_uvicorn_run,
        test_scenario: str,
        config_params: dict,
        env_vars: dict,
        expected_behavior: str,
        expected_values: dict,
    ) -> None:
        """Test comprehensive A2A server startup and configuration scenarios."""
        # Setup mock configuration
        mock_config_instance = Mock()
        if "agent_name" not in config_params:
            mock_config_instance.agent_name = "strands-base-agent"
        for key, value in config_params.items():
            setattr(mock_config_instance, key, value)

        # Setup mock dependencies
        mock_container_instance = Mock()
        mock_container.return_value = mock_container_instance
        mock_factory_instance = Mock()
        mock_container_instance.resolve.side_effect = lambda protocol: (
            mock_config_instance if protocol is AgentConfig else mock_factory_instance
        )
        mock_server_instance = Mock()
        mock_a2a_server.return_value = mock_server_instance

        mock_fastapi_app = Mock()
        mock_fastapi_app.include_router = Mock()
        mock_server_instance.to_fastapi_app.return_value = mock_fastapi_app

        with patch.dict(
            os.environ,
            {"STRANDS_TLS_MODE": "off", **env_vars},
            clear=True,
        ):
            start_server()

        # Calculate expected http_url based on agent_name and port
        agent_name = config_params.get("agent_name", "strands-base-agent")
        expected_http_url = f"http://{agent_name}:{expected_values['port']}"

        # Verify A2A server created with correct parameters
        mock_a2a_server.assert_called_once()
        kwargs = mock_a2a_server.call_args.kwargs

        assert kwargs["host"] == expected_values["host"]
        assert kwargs["port"] == expected_values["port"]
        assert kwargs["http_url"] == expected_http_url
        assert kwargs["version"] == expected_values["version"]

        # Per-context mode: a factory, never a single shared agent.
        assert "agent" not in kwargs
        assert callable(kwargs["agent_factory"])
        assert kwargs["max_contexts"] == StrandsA2AExecutor.DEFAULT_MAX_CONTEXTS
        assert kwargs["enable_a2a_compliant_streaming"] is True

        # Verify uvicorn.run was called with the FastAPI app
        mock_uvicorn_run.assert_called_once_with(
            mock_fastapi_app, host=expected_values["host"], port=expected_values["port"]
        )

        mock_server_instance.to_fastapi_app.assert_called_once()
        assert mock_fastapi_app.include_router.call_count == 3

    def test_a2a_server_error_handling_invalid_config(self) -> None:
        """Test server startup handles invalid configuration gracefully."""
        mock_config_instance = Mock()
        mock_config_instance.agent_port = None

        with patch("strands_base_agent.server.create_application_container") as mock_container:
            mock_container_instance = Mock()
            mock_container.return_value = mock_container_instance
            mock_container_instance.resolve.return_value = mock_config_instance

            with patch("uvicorn.run"):  # Add: patch uvicorn.run
                with patch("strands_base_agent.server._BearerCardA2AServer"):  # Fix: correct path
                    with patch.dict(os.environ, {"HOST": "127.0.0.1", "PORT": "invalid_port"}):
                        with pytest.raises(ValueError):
                            start_server()

    def test_a2a_server_error_handling_agent_creation_failure(self) -> None:
        """start_server() does not build any agent; the builder is created in the lifespan."""
        from strands_base_agent.server import start_server

        # Agent creation now happens in the async lifespan, not during start_server().
        # The agent builder is created in the lifespan, so no agent exists until the app starts.
        # This test verifies start_server() itself doesn't crash (agent is deferred).
        mock_config_instance = Mock()
        mock_config_instance.agent_version = "1.0.0"
        mock_config_instance.agent_port = None
        mock_config_instance.agent_name = "test-agent"

        with patch("uvicorn.run"):
            with patch("strands_base_agent.server._BearerCardA2AServer") as mock_a2a:
                mock_server = Mock()
                mock_fastapi_app = Mock()
                mock_fastapi_app.include_router = Mock()
                mock_server.to_fastapi_app.return_value = mock_fastapi_app
                mock_a2a.return_value = mock_server

                with patch("strands_base_agent.server.create_application_container") as mock_container:
                    mock_container_instance = Mock()
                    mock_container.return_value = mock_container_instance
                    mock_container_instance.resolve.return_value = mock_config_instance
                    with patch.dict(os.environ, {"HOST": "127.0.0.1", "PORT": "8000", "STRANDS_TLS_MODE": "off"}):
                        start_server()  # Should not raise — agent is deferred

    def test_a2a_server_error_handling_server_creation_failure(self) -> None:
        """Test server startup handles A2A server creation failure gracefully."""
        mock_config_instance = Mock()
        mock_config_instance.agent_version = "1.0.0"
        mock_config_instance.agent_port = None

        with patch("uvicorn.run"):  # Add: patch uvicorn.run
            with patch(
                "strands_base_agent.server._BearerCardA2AServer", side_effect=RuntimeError("A2A server creation failed")
            ):  # Fix: correct path
                with patch("strands_base_agent.server.create_application_container") as mock_container:
                    mock_container_instance = Mock()
                    mock_container.return_value = mock_container_instance
                    mock_container_instance.resolve.return_value = mock_config_instance
                    with patch("asyncio.run", return_value=Mock()):
                        with patch.dict(os.environ, {"HOST": "127.0.0.1", "PORT": "8000"}):
                            with pytest.raises(RuntimeError, match="A2A server creation failed"):
                                start_server()


def _capture_factory_and_lifespan(agent_factory_mock=None):
    """Call start_server() with mocks, return the A2A agent_factory and the lifespan."""
    mock_config = Mock()
    mock_config.agent_name = "test-agent"
    mock_config.agent_description = "Test description"
    mock_config.agent_version = "1.0.0"
    mock_config.agent_port = 8000

    captured: dict = {}

    @asynccontextmanager
    async def fake_original_lifespan(app):  # noqa: ARG001
        yield {}

    class FakeRouter:
        lifespan_context = staticmethod(fake_original_lifespan)

    def capture_a2a_server(**kwargs):
        captured.update(kwargs)
        mock_server = Mock()
        mock_fastapi_app = Mock()
        mock_fastapi_app.include_router = Mock()
        mock_fastapi_app.router = FakeRouter()
        mock_server.to_fastapi_app.return_value = mock_fastapi_app
        return mock_server

    def capture_uvicorn_run(app, **_kwargs):
        captured["lifespan"] = app.router.lifespan_context

    with (
        patch("strands_base_agent.server.create_application_container") as mock_container,
        patch("strands_base_agent.server._BearerCardA2AServer", side_effect=capture_a2a_server),
        patch("uvicorn.run", side_effect=capture_uvicorn_run),
        patch.dict(os.environ, {"STRANDS_TLS_MODE": "off", "STRANDS_API_KEY": "test-key"}, clear=True),
    ):
        agent_factory = agent_factory_mock or Mock()
        mock_container_instance = Mock()
        mock_container.return_value = mock_container_instance
        mock_container_instance.resolve.side_effect = lambda protocol: (
            mock_config if protocol is AgentConfig else agent_factory
        )
        start_server()

    return captured["agent_factory"], captured["lifespan"]


def _factory_with_builder():
    """An AgentFactory mock whose create_agent_builder() returns a builder mock."""
    builder = Mock()
    builder.build.side_effect = lambda session_id=None: Mock(name=f"agent-{session_id}")
    factory = Mock()
    factory.create_agent_builder = AsyncMock(return_value=builder)
    return factory, builder


def _single_agent_deprecation_message() -> str:
    """The exact DeprecationWarning text the SDK emits for the old A2AServer(agent=...) path."""
    import warnings

    from strands.multiagent.a2a.executor import StrandsA2AExecutor

    agent = Mock()
    agent.session_manager = None
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        StrandsA2AExecutor(agent)
    return next(str(w.message) for w in caught if issubclass(w.category, DeprecationWarning))


class TestA2AAgentFactory:
    """The per-context agent_factory passed to A2AServer."""

    def test_card_context_returns_config_metadata_without_builder(self):
        agent_factory, _ = _capture_factory_and_lifespan()
        card = agent_factory("__agent_card__")
        assert card.name == "test-agent"
        assert card.description == "Test description"
        assert card.tool_registry.get_all_tools_config() == {}

    def test_card_context_id_matches_sdk(self):
        from strands.multiagent.a2a import server as sdk_server

        from strands_base_agent.server import _A2A_AGENT_CARD_CONTEXT_ID

        assert sdk_server._AGENT_CARD_CONTEXT_ID == _A2A_AGENT_CARD_CONTEXT_ID

    def test_real_context_before_lifespan_raises(self):
        agent_factory, _ = _capture_factory_and_lifespan()
        with pytest.raises(RuntimeError, match="before the agent builder was initialized"):
            agent_factory("ctx-one")

    @pytest.mark.asyncio
    async def test_each_context_gets_its_own_build(self):
        factory, builder = _factory_with_builder()
        agent_factory, lifespan = _capture_factory_and_lifespan(factory)

        with patch.dict(os.environ, {"STRANDS_API_KEY": "test-key"}):
            async with lifespan(Mock()):
                agent_one = agent_factory("ctx-one")
                agent_two = agent_factory("ctx-two")

        factory.create_agent_builder.assert_awaited_once_with()
        assert [c.kwargs for c in builder.build.call_args_list] == [
            {},
            {"session_id": "a2a.ctx-one"},
            {"session_id": "a2a.ctx-two"},
        ]
        assert agent_one is not agent_two

    @pytest.mark.asyncio
    async def test_context_agent_takes_name_and_description_from_card_config(self):
        """Per-context agents use the same name and description as the agent card."""
        factory, builder = _factory_with_builder()
        builder.build.side_effect = lambda **_kwargs: Mock(name="from-config-yaml")
        agent_factory, lifespan = _capture_factory_and_lifespan(factory)

        with patch.dict(os.environ, {"STRANDS_API_KEY": "test-key"}):
            async with lifespan(Mock()):
                agent = agent_factory("ctx-one")

        assert agent.name == "test-agent"
        assert agent.description == "Test description"

    @pytest.mark.asyncio
    async def test_card_context_id_after_lifespan_builds_a_real_agent(self):
        """A request with contextId "__agent_card__" gets a built agent, not the card stub."""
        factory, builder = _factory_with_builder()
        agent_factory, lifespan = _capture_factory_and_lifespan(factory)

        with patch.dict(os.environ, {"STRANDS_API_KEY": "test-key"}):
            async with lifespan(Mock()):
                agent = agent_factory("__agent_card__")

        assert builder.build.call_args.kwargs == {"session_id": "a2a.__agent_card__"}
        assert type(agent).__name__ != "_AgentCardMetadata"

    @pytest.mark.asyncio
    @pytest.mark.parametrize(("length", "accepted"), [(124, True), (125, False)])
    async def test_context_id_length_limit_includes_session_prefix(self, length, accepted):
        """build() caps session_id at 128 characters, so a contextId gets 124 after "a2a."."""
        from a2a.types import InvalidParamsError
        from a2a.utils.errors import ServerError

        from foundry_strands_agent.factory import AgentBuilder

        builder = AgentBuilder(Mock(), Mock(), {"session_type": "file"}, [], Mock())
        factory = Mock()
        factory.create_agent_builder = AsyncMock(return_value=builder)
        agent_factory, lifespan = _capture_factory_and_lifespan(factory)

        with patch.object(AgentBuilder, "_build") as inner_build:
            with patch.dict(os.environ, {"STRANDS_API_KEY": "test-key"}):
                async with lifespan(Mock()):
                    if accepted:
                        agent_factory("x" * length)
                    else:
                        with pytest.raises(ServerError) as excinfo:
                            agent_factory("x" * length)
                        assert isinstance(excinfo.value.error, InvalidParamsError)
        context_builds = [c.args for c in inner_build.call_args_list if c.args[0] is not None]
        assert context_builds == ([("a2a." + "x" * length, "file")] if accepted else [])

    @pytest.mark.asyncio
    @pytest.mark.parametrize("context_id", ["../x", "a/b", "a\\b", "a\x00b", "x" * 129, "ends-in-dot."])
    async def test_unsafe_context_id_is_rejected_before_session_storage(self, context_id):
        """A caller-controlled context_id never reaches file or S3 session storage unvalidated."""
        from a2a.types import InvalidParamsError
        from a2a.utils.errors import ServerError

        from foundry_strands_agent.factory import AgentBuilder

        builder = AgentBuilder(Mock(), Mock(), {"session_type": "file"}, [], Mock())
        factory = Mock()
        factory.create_agent_builder = AsyncMock(return_value=builder)
        agent_factory, lifespan = _capture_factory_and_lifespan(factory)

        with patch.object(AgentBuilder, "_build") as inner_build:
            with patch.dict(os.environ, {"STRANDS_API_KEY": "test-key"}):
                async with lifespan(Mock()):
                    with pytest.raises(ServerError) as excinfo:
                        agent_factory(context_id)
        error = excinfo.value.error
        assert isinstance(error, InvalidParamsError)
        assert error.message.startswith("Invalid contextId")
        assert context_id not in error.message
        assert [c.args for c in inner_build.call_args_list] == [(None, "file")]

    @pytest.mark.asyncio
    async def test_other_build_failures_are_not_reported_as_invalid_context_id(self):
        """Only build()'s session_id check becomes an invalid-params error; MCP or model errors pass through."""
        from foundry_agent_core import AgentCreationError

        factory, builder = _factory_with_builder()
        agent_factory, lifespan = _capture_factory_and_lifespan(factory)

        with patch.dict(os.environ, {"STRANDS_API_KEY": "test-key"}):
            async with lifespan(Mock()):
                builder.build.side_effect = AgentCreationError("Failed to start MCP client")
                with pytest.raises(AgentCreationError, match="Failed to start MCP client"):
                    agent_factory("ctx-one")

    @pytest.mark.asyncio
    async def test_lifespan_startup_and_shutdown_complete(self):
        factory, builder = _factory_with_builder()
        _, lifespan = _capture_factory_and_lifespan(factory)
        app = Mock()
        with patch.dict(os.environ, {"STRANDS_API_KEY": "test-key"}):
            async with lifespan(app):
                startup_agent = app.state.a2a_startup_agent
        factory.create_agent_builder.assert_awaited_once_with()
        builder.build.assert_called_once_with()
        # Held on app.state while the server runs, so MCP stays connected; released at shutdown.
        assert startup_agent is not None
        assert app.state.a2a_startup_agent is None

    @pytest.mark.asyncio
    async def test_startup_fails_when_the_first_build_fails(self, caplog):
        """A bad MCP config surfaces from build(), so startup fails and still logs shutdown."""
        from foundry_agent_core import AgentCreationError

        factory, builder = _factory_with_builder()
        builder.build.side_effect = AgentCreationError("Failed to start MCP client")
        _, lifespan = _capture_factory_and_lifespan(factory)

        with caplog.at_level("INFO", logger="strands_base_agent.server"):
            with patch.dict(os.environ, {"STRANDS_API_KEY": "test-key"}):
                with pytest.raises(AgentCreationError, match="Failed to start MCP client"):
                    async with lifespan(Mock()):
                        pass

        messages = [r.getMessage() for r in caplog.records]
        assert "A2A server started" not in messages
        assert "A2A server shutting down" in messages

    def test_factory_without_builder_support_fails_fast(self):
        class _NoBuilderFactory:
            pass

        with pytest.raises(RuntimeError, match="create_agent_builder"):
            _capture_factory_and_lifespan(_NoBuilderFactory())

    def test_real_a2a_server_card_and_no_deprecation_warning(self, recwarn):
        """Build the real SDK A2AServer with the factory: card unchanged, factory mode."""
        from strands.multiagent.a2a.server import A2AServer

        agent_factory, _ = _capture_factory_and_lifespan()
        server = A2AServer(agent_factory=agent_factory, host="127.0.0.1", port=8000, http_url="http://test-agent:8000")

        card = server.public_agent_card
        assert card.name == "test-agent"
        assert card.description == "Test description"
        assert card.skills == []
        assert card.url == "http://test-agent:8000/"
        assert _single_agent_deprecation_message() not in [str(w.message) for w in recwarn]

    def test_served_card_advertises_bearer_auth(self):
        """The served card declares the bearer scheme the auth middleware enforces, and requires it."""
        from fastapi.testclient import TestClient

        from strands_base_agent.server import _BearerCardA2AServer

        agent_factory, _ = _capture_factory_and_lifespan()
        server = _BearerCardA2AServer(
            agent_factory=agent_factory, host="127.0.0.1", port=8000, http_url="http://test-agent:8000"
        )

        card = TestClient(server.to_fastapi_app()).get("/.well-known/agent-card.json").json()
        assert card["securitySchemes"]["bearer"]["type"] == "http"
        assert card["securitySchemes"]["bearer"]["scheme"] == "bearer"
        assert "STRANDS_API_KEY" in card["securitySchemes"]["bearer"]["description"]
        assert card["security"] == [{"bearer": []}]
        assert card["name"] == "test-agent"
        assert card["url"] == "http://test-agent:8000/"

    def test_single_agent_deprecation_message_is_captured(self):
        """Guard the check above: the old agent= path must still emit the warning it looks for."""
        assert "agent_factory" in _single_agent_deprecation_message()


class TestA2AMaxContexts:
    """STRANDS_A2A_MAX_CONTEXTS sets A2AServer(max_contexts=...)."""

    def test_unset_uses_sdk_default(self):
        from strands_base_agent.server import _a2a_max_contexts

        with patch.dict(os.environ, {}, clear=True):
            assert _a2a_max_contexts() == StrandsA2AExecutor.DEFAULT_MAX_CONTEXTS

    def test_env_value_is_used(self):
        from strands_base_agent.server import _a2a_max_contexts

        with patch.dict(os.environ, {"STRANDS_A2A_MAX_CONTEXTS": "25"}, clear=True):
            assert _a2a_max_contexts() == 25

    def test_cap_is_accepted(self):
        from strands_base_agent.server import _A2A_MAX_CONTEXTS_CAP, _a2a_max_contexts

        with patch.dict(os.environ, {"STRANDS_A2A_MAX_CONTEXTS": str(_A2A_MAX_CONTEXTS_CAP)}, clear=True):
            assert _a2a_max_contexts() == _A2A_MAX_CONTEXTS_CAP

    @pytest.mark.parametrize("value", ["0", "-3", "many", "1_000", " 5 ", "+5", "1.5", "10001", "١", "9" * 5000])
    def test_invalid_value_raises(self, value):
        from strands_base_agent.server import _a2a_max_contexts

        with patch.dict(os.environ, {"STRANDS_A2A_MAX_CONTEXTS": value}, clear=True):
            with pytest.raises(RuntimeError, match="integer from 1 to 10000"):
                _a2a_max_contexts()
