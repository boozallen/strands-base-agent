# Copyright 2026 Booz Allen Hamilton Inc.
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for agent card URL warning at startup."""

import logging
import os
from unittest.mock import Mock, patch

from foundry_strands_agent import AgentConfig

from strands_base_agent.server import start_server


class TestAgentCardUrlWarning:
    @patch("uvicorn.run")
    @patch("strands_base_agent.server._BearerCardA2AServer")
    @patch("strands_base_agent.server.create_application_container")
    @patch("asyncio.run")
    def test_warns_when_public_url_unset(
        self,
        mock_asyncio,
        mock_container,
        mock_a2a_server,
        mock_uvicorn_run,
        caplog,
    ):
        mock_config_instance = Mock()
        mock_config_instance.agent_name = "strands-base-agent"
        mock_config_instance.agent_version = "1.0"
        mock_config_instance.agent_port = None

        mock_container_instance = Mock()
        mock_container.return_value = mock_container_instance
        mock_container_instance.resolve.side_effect = lambda protocol: (
            mock_config_instance if protocol is AgentConfig else Mock()
        )
        mock_asyncio.return_value = Mock()

        mock_fastapi_app = Mock()
        mock_a2a_server.return_value.to_fastapi_app.return_value = mock_fastapi_app

        with patch.dict(
            os.environ,
            {"STRANDS_TLS_MODE": "off"},
            clear=True,
        ):
            with caplog.at_level(logging.WARNING):
                start_server()

        assert any("STRANDS_AGENT_PUBLIC_URL is not set" in record.message for record in caplog.records)

    @patch("uvicorn.run")
    @patch("strands_base_agent.server._BearerCardA2AServer")
    @patch("strands_base_agent.server.create_application_container")
    @patch("asyncio.run")
    def test_no_warning_when_public_url_set(
        self,
        mock_asyncio,
        mock_container,
        mock_a2a_server,
        mock_uvicorn_run,
        caplog,
    ):
        mock_config_instance = Mock()
        mock_config_instance.agent_name = "strands-base-agent"
        mock_config_instance.agent_version = "1.0"
        mock_config_instance.agent_port = None

        mock_container_instance = Mock()
        mock_container.return_value = mock_container_instance
        mock_container_instance.resolve.side_effect = lambda protocol: (
            mock_config_instance if protocol is AgentConfig else Mock()
        )
        mock_asyncio.return_value = Mock()

        mock_fastapi_app = Mock()
        mock_a2a_server.return_value.to_fastapi_app.return_value = mock_fastapi_app

        with patch.dict(
            os.environ,
            {
                "STRANDS_TLS_MODE": "off",
                "STRANDS_AGENT_PUBLIC_URL": "https://my-agent.example.com",
            },
            clear=True,
        ):
            with caplog.at_level(logging.WARNING):
                start_server()

        assert not any("STRANDS_AGENT_PUBLIC_URL is not set" in record.message for record in caplog.records)


class TestConfigYamlIsHonored:
    """start_server() must take agent_name and agent_port from config.yaml, not only from env vars."""

    @patch("uvicorn.run")
    @patch("strands_base_agent.server._BearerCardA2AServer")
    @patch("asyncio.run")
    def test_yaml_agent_name_and_port_reach_the_card_and_the_bind(
        self, mock_asyncio, mock_a2a_server, mock_uvicorn_run, tmp_path, monkeypatch
    ):
        (tmp_path / "config.yaml").write_text("agent_name: yaml-agent\nagent_port: 9123\n")
        monkeypatch.chdir(tmp_path)
        mock_asyncio.return_value = Mock()
        mock_a2a_server.return_value.to_fastapi_app.return_value = Mock()

        # The old single-underscore variables must not override the YAML-aware config.
        with patch.dict(
            os.environ,
            {"STRANDS_TLS_MODE": "off", "STRANDS_AGENT_NAME": "env-agent", "STRANDS_AGENT_PORT": "7777"},
            clear=True,
        ):
            start_server()

        assert mock_a2a_server.call_args.kwargs["http_url"] == "http://yaml-agent:9123"
        assert mock_uvicorn_run.call_args.kwargs["port"] == 9123

    @patch("uvicorn.run")
    @patch("strands_base_agent.server._BearerCardA2AServer")
    @patch("asyncio.run")
    def test_double_underscore_env_overrides_yaml_port(
        self, mock_asyncio, mock_a2a_server, mock_uvicorn_run, tmp_path, monkeypatch
    ):
        (tmp_path / "config.yaml").write_text("agent_name: yaml-agent\nagent_port: 9123\n")
        monkeypatch.chdir(tmp_path)
        mock_asyncio.return_value = Mock()
        mock_a2a_server.return_value.to_fastapi_app.return_value = Mock()

        with patch.dict(os.environ, {"STRANDS_TLS_MODE": "off", "STRANDS__AGENT_PORT": "8000"}, clear=True):
            start_server()

        assert mock_uvicorn_run.call_args.kwargs["port"] == 8000
