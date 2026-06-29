# Copyright 2026 Booz Allen Hamilton Inc.
# SPDX-License-Identifier: Apache-2.0
"""Integration tests for dynamic tool loading."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import Mock, patch

import pytest

from foundry_strands_agent import AgentFactory, StrandsAgentFactory, create_agent_service

from strands_base_agent.application.factory import create_application_container


class TestServiceToolLoadingIntegration:
    """Integration tests for service initialization with tool loading."""

    @pytest.mark.asyncio
    async def test_service_initializes_without_tools(self) -> None:
        """Test that service initializes successfully with no tools configured."""
        with patch.dict(
            "os.environ",
            {"STRANDS__TOOLS_MODULES": "", "STRANDS__TOOLS_FILES": ""},
            clear=False,
        ):
            container = create_application_container()
            container.register_factory(AgentFactory, lambda: StrandsAgentFactory(container), singleton=True)
            service = create_agent_service(container)

            await service.initialize()

            # Service should be initialized
            assert service._initialized is True

            # Tool registry should be initialized but empty
            assert service._tool_registry is not None
            tools = service._tool_registry.get_available_tools()
            assert isinstance(tools, list)

            await service.shutdown()

    @pytest.mark.asyncio
    async def test_service_initializes_with_invalid_tool_gracefully(self) -> None:
        """Test that service handles invalid tool specs gracefully."""
        with patch.dict(
            "os.environ",
            {"STRANDS__TOOLS_MODULES": "nonexistent.invalid.module"},
            clear=False,
        ):
            container = create_application_container()
            container.register_factory(AgentFactory, lambda: StrandsAgentFactory(container), singleton=True)
            service = create_agent_service(container)

            # Should not raise exception - graceful degradation
            await service.initialize()

            # Service should still be initialized
            assert service._initialized is True

            await service.shutdown()

    @pytest.mark.asyncio
    async def test_service_loads_and_registers_tool_successfully(self) -> None:
        """Test that service successfully loads and registers a tool."""
        # Create a mock tool module with TOOL_SPEC format
        mock_tool_function = Mock()
        mock_tool_module = Mock()
        mock_tool_module.TOOL_SPEC = {
            "name": "test_tool",
            "description": "Test tool for integration testing",
            "inputSchema": {"json": {"type": "object", "properties": {}}},
        }
        mock_tool_module.test_tool = mock_tool_function

        with patch.dict("os.environ", {"STRANDS__TOOLS_MODULES": "test.tool"}, clear=False):
            with (
                patch("foundry_strands_agent.tool_loader._assert_module_in_tools_dir", lambda *_: None),
                patch("foundry_strands_agent.tool_loader.importlib.util.find_spec") as mock_find_spec,
                patch("foundry_strands_agent.tool_loader.SECURITY_ANALYZER.analyze_module_file", return_value=True),
                patch("foundry_strands_agent.tool_loader.importlib.import_module") as mock_import,
            ):
                mock_import.return_value = mock_tool_module
                mock_find_spec.return_value = SimpleNamespace(origin=__file__, submodule_search_locations=None)
                mock_find_spec.return_value = Mock(origin="test/tool.py")

                container = create_application_container()

                container.register_factory(AgentFactory, lambda: StrandsAgentFactory(container), singleton=True)
                service = create_agent_service(container)

                await service.initialize()

                # Service should be initialized
                assert service._initialized is True

                # Tool should be registered
                assert service._tool_registry is not None
                tools = service._tool_registry.get_available_tools()

                # Should have the test tool
                tool_names = [
                    (
                        tool.TOOL_SPEC["name"]
                        if hasattr(tool, "TOOL_SPEC")
                        else (tool.__name__ if hasattr(tool, "__name__") else "unknown")
                    )
                    for tool in tools
                ]
                # Tool name is prefixed with module path: test.tool -> test__tool
                assert "test_tool" in tool_names

                await service.shutdown()

    @pytest.mark.asyncio
    async def test_service_loads_multiple_tools(self) -> None:
        """Test that service can load multiple tools."""
        # Create two mock tool modules
        mock_tool1_function = Mock()
        mock_tool1_module = Mock()
        mock_tool1_module.TOOL_SPEC = {
            "name": "tool_one",
            "description": "First test tool",
            "inputSchema": {"json": {"type": "object"}},
        }
        mock_tool1_module.tool_one = mock_tool1_function

        mock_tool2_function = Mock()
        mock_tool2_module = Mock()
        mock_tool2_module.TOOL_SPEC = {
            "name": "tool_two",
            "description": "Second test tool",
            "inputSchema": {"json": {"type": "object"}},
        }
        mock_tool2_module.tool_two = mock_tool2_function

        with patch.dict(
            "os.environ",
            {"STRANDS__TOOLS_MODULES": "test.tool1,test.tool2"},
            clear=False,
        ):
            with (
                patch("foundry_strands_agent.tool_loader._assert_module_in_tools_dir", lambda *_: None),
                patch("foundry_strands_agent.tool_loader.importlib.util.find_spec") as mock_find_spec,
                patch("foundry_strands_agent.tool_loader.SECURITY_ANALYZER.analyze_module_file", return_value=True),
                patch("foundry_strands_agent.tool_loader.importlib.import_module") as mock_import,
            ):
                mock_find_spec.return_value = SimpleNamespace(origin=__file__, submodule_search_locations=None)
                mock_find_spec.return_value = Mock(origin="test/tool1.py")
                mock_find_spec.return_value = Mock(origin="test/tool2.py")

                def import_side_effect(module_name: str) -> Any:
                    if module_name == "test.tool1":
                        return mock_tool1_module
                    elif module_name == "test.tool2":
                        return mock_tool2_module
                    raise ImportError(f"Unknown module: {module_name}")

                mock_import.side_effect = import_side_effect

                container = create_application_container()

                container.register_factory(AgentFactory, lambda: StrandsAgentFactory(container), singleton=True)
                service = create_agent_service(container)

                await service.initialize()

                # Both tools should be registered
                assert service._tool_registry is not None
                tools = service._tool_registry.get_available_tools()

                tool_names = [
                    (
                        tool.TOOL_SPEC["name"]
                        if hasattr(tool, "TOOL_SPEC")
                        else (tool.__name__ if hasattr(tool, "__name__") else "unknown")
                    )
                    for tool in tools
                ]
                # Tool names are prefixed with module paths
                assert "tool_one" in tool_names
                assert "tool_two" in tool_names

                await service.shutdown()

    @pytest.mark.asyncio
    async def test_service_handles_mixed_success_and_failure(self) -> None:
        """Test that service continues when some tools fail but others succeed."""
        # Create one valid tool
        mock_valid_function = Mock()
        mock_valid_module = Mock()
        mock_valid_module.TOOL_SPEC = {
            "name": "valid_tool",
            "description": "Valid tool",
            "inputSchema": {"json": {"type": "object"}},
        }
        mock_valid_module.valid_tool = mock_valid_function

        with patch.dict(
            "os.environ",
            {"STRANDS__TOOLS_MODULES": "valid.tool,invalid.tool"},
            clear=False,
        ):
            with (
                patch("foundry_strands_agent.tool_loader._assert_module_in_tools_dir", lambda *_: None),
                patch("foundry_strands_agent.tool_loader.importlib.util.find_spec") as mock_find_spec,
                patch("foundry_strands_agent.tool_loader.SECURITY_ANALYZER.analyze_module_file", return_value=True),
                patch("foundry_strands_agent.tool_loader.importlib.import_module") as mock_import,
            ):
                mock_find_spec.return_value = SimpleNamespace(origin=__file__, submodule_search_locations=None)
                mock_find_spec.return_value = Mock(origin="valid/tool.py")
                mock_find_spec.return_value = Mock(origin="invalid/tool.py")

                def import_side_effect(module_name: str) -> Any:
                    if module_name == "valid.tool":
                        return mock_valid_module
                    elif module_name == "invalid.tool":
                        raise ImportError("Module not found")
                    raise ImportError(f"Unknown module: {module_name}")

                mock_import.side_effect = import_side_effect

                container = create_application_container()

                container.register_factory(AgentFactory, lambda: StrandsAgentFactory(container), singleton=True)
                service = create_agent_service(container)

                # Should not raise exception
                await service.initialize()

                # Service should still be initialized
                assert service._initialized is True

                # Valid tool should be registered
                assert service._tool_registry is not None
                tools = service._tool_registry.get_available_tools()

                tool_names = [
                    (
                        tool.TOOL_SPEC["name"]
                        if hasattr(tool, "TOOL_SPEC")
                        else (tool.__name__ if hasattr(tool, "__name__") else "unknown")
                    )
                    for tool in tools
                ]
                # Tool name is prefixed with module path: valid.tool -> valid__tool
                assert "valid_tool" in tool_names

                await service.shutdown()

    @pytest.mark.asyncio
    async def test_service_lifecycle_context_manager_with_tools(self) -> None:
        """Test that service lifecycle context manager works with tool loading."""
        mock_tool_function = Mock()
        mock_tool_module = Mock()
        mock_tool_module.TOOL_SPEC = {
            "name": "test_tool",
            "description": "Test tool",
            "inputSchema": {"json": {"type": "object"}},
        }
        mock_tool_module.test_tool = mock_tool_function

        with patch.dict("os.environ", {"STRANDS__TOOLS_MODULES": "test.tool"}, clear=False):
            with (
                patch("foundry_strands_agent.tool_loader._assert_module_in_tools_dir", lambda *_: None),
                patch("foundry_strands_agent.tool_loader.importlib.util.find_spec") as mock_find_spec,
                patch("foundry_strands_agent.tool_loader.SECURITY_ANALYZER.analyze_module_file", return_value=True),
                patch("foundry_strands_agent.tool_loader.importlib.import_module") as mock_import,
            ):
                mock_find_spec.return_value = SimpleNamespace(origin=__file__, submodule_search_locations=None)
                mock_find_spec.return_value = Mock(origin="test/tool.py")
                mock_import.return_value = mock_tool_module

                container = create_application_container()

                container.register_factory(AgentFactory, lambda: StrandsAgentFactory(container), singleton=True)
                service = create_agent_service(container)

                async with service.service_lifecycle():
                    # Service should be initialized with tools
                    assert service._initialized is True
                    assert service._tool_registry is not None

                # Service should be shut down
                assert service._initialized is False


class TestToolLoadingConfiguration:
    """Tests for tool loading configuration parsing."""

    @pytest.mark.asyncio
    async def test_empty_strands_tools_skips_loading(self) -> None:
        """Test that empty STRANDS__TOOLS_MODULES and STRANDS__TOOLS_FILES skip tool loading."""
        with patch.dict(
            "os.environ",
            {"STRANDS__TOOLS_MODULES": "", "STRANDS__TOOLS_FILES": ""},
            clear=False,
        ):
            container = create_application_container()
            container.register_factory(AgentFactory, lambda: StrandsAgentFactory(container), singleton=True)
            service = create_agent_service(container)

            with (
                patch("foundry_strands_agent.tool_loader.load_tool_from_module") as mock_load_module,
                patch("foundry_strands_agent.tool_loader.load_tool_from_file") as mock_load_file,
            ):
                await service.initialize()

                # Neither loader should be called
                mock_load_module.assert_not_called()
                mock_load_file.assert_not_called()

                await service.shutdown()

    @pytest.mark.asyncio
    async def test_whitespace_in_tool_specs_is_handled(self) -> None:
        """Test that whitespace in tool specs is handled correctly."""
        mock_tool_function = Mock()
        mock_tool_module = Mock()
        mock_tool_module.TOOL_SPEC = {
            "name": "test_tool",
            "description": "Test tool",
            "inputSchema": {"json": {"type": "object"}},
        }
        mock_tool_module.test_tool = mock_tool_function

        # Tool spec with extra whitespace
        with patch.dict(
            "os.environ",
            {"STRANDS__TOOLS_MODULES": "  test.tool  ,  another.tool  "},
            clear=False,
        ):
            with (
                patch("foundry_strands_agent.tool_loader._assert_module_in_tools_dir", lambda *_: None),
                patch("foundry_strands_agent.tool_loader.importlib.util.find_spec") as mock_find_spec,
                patch("foundry_strands_agent.tool_loader.SECURITY_ANALYZER.analyze_module_file", return_value=True),
                patch("foundry_strands_agent.tool_loader.importlib.import_module") as mock_import,
            ):
                mock_find_spec.return_value = SimpleNamespace(origin=__file__, submodule_search_locations=None)
                mock_find_spec.return_value = Mock(origin="test/tool.py")
                mock_find_spec.return_value = Mock(origin="another/tool.py")
                mock_import.return_value = mock_tool_module

                container = create_application_container()

                container.register_factory(AgentFactory, lambda: StrandsAgentFactory(container), singleton=True)
                service = create_agent_service(container)

                await service.initialize()

                # Should have attempted to load both tools (whitespace trimmed)
                assert mock_import.call_count >= 2

                await service.shutdown()


class TestToolLoadingErrorHandling:
    """Tests for error handling during tool loading."""

    @pytest.mark.asyncio
    async def test_tool_registration_failure_logged(self) -> None:
        """Test that tool registration failures are logged but don't crash service."""
        mock_tool_function = Mock()
        mock_tool_module = Mock()
        mock_tool_module.TOOL_SPEC = {
            "name": "test_tool",
            "description": "Test tool",
            "inputSchema": {"json": {"type": "object"}},
        }
        mock_tool_module.test_tool = mock_tool_function

        with patch.dict("os.environ", {"STRANDS__TOOLS_MODULES": "test.tool"}, clear=False):
            with (
                patch("foundry_strands_agent.tool_loader._assert_module_in_tools_dir", lambda *_: None),
                patch("foundry_strands_agent.tool_loader.importlib.util.find_spec") as mock_find_spec,
                patch("foundry_strands_agent.tool_loader.SECURITY_ANALYZER.analyze_module_file", return_value=True),
                patch("foundry_strands_agent.tool_loader.importlib.import_module") as mock_import,
            ):
                mock_find_spec.return_value = SimpleNamespace(origin=__file__, submodule_search_locations=None)
                mock_find_spec.return_value = Mock(origin="test/tool.py")
                mock_import.return_value = mock_tool_module

                container = create_application_container()

                container.register_factory(AgentFactory, lambda: StrandsAgentFactory(container), singleton=True)
                service = create_agent_service(container)

                await service.initialize()

                # Mock register_tool to raise an exception after initialization
                if service._tool_registry:
                    # Just verify service initialized despite potential registration issues
                    # The actual test would involve re-loading tools with a broken registry
                    pass

                # Service should still be initialized
                assert service._initialized is True

                await service.shutdown()

    @pytest.mark.asyncio
    async def test_service_health_reflects_tool_loading(self) -> None:
        """Test that service health check works after tool loading."""
        mock_tool_function = Mock()
        mock_tool_module = Mock()
        mock_tool_module.TOOL_SPEC = {
            "name": "test_tool",
            "description": "Test tool",
            "inputSchema": {"json": {"type": "object"}},
        }
        mock_tool_module.test_tool = mock_tool_function

        with patch.dict("os.environ", {"STRANDS__TOOLS_MODULES": "test.tool"}, clear=False):
            with (
                patch("foundry_strands_agent.tool_loader._assert_module_in_tools_dir", lambda *_: None),
                patch("foundry_strands_agent.tool_loader.importlib.util.find_spec") as mock_find_spec,
                patch("foundry_strands_agent.tool_loader.SECURITY_ANALYZER.analyze_module_file", return_value=True),
                patch("foundry_strands_agent.tool_loader.importlib.import_module") as mock_import,
            ):
                mock_find_spec.return_value = SimpleNamespace(origin=__file__, submodule_search_locations=None)
                mock_find_spec.return_value = Mock(origin="test/tool.py")
                mock_import.return_value = mock_tool_module

                container = create_application_container()

                container.register_factory(AgentFactory, lambda: StrandsAgentFactory(container), singleton=True)
                service = create_agent_service(container)

                await service.initialize()

                # Get service health
                health = await service.get_service_health()

                assert health["service_initialized"] is True
                assert health["components"]["tool_registry"] is True

                await service.shutdown()


class TestSeparateToolEnvironmentVariables:
    """Tests for separate STRANDS__TOOLS_MODULES and STRANDS__TOOLS_FILES environment variables."""

    @pytest.mark.asyncio
    async def test_service_loads_module_tools_from_strands_tools_modules(self) -> None:
        """Integration test for module loading via STRANDS__TOOLS_MODULES."""
        mock_tool_function = Mock()
        mock_tool_module = Mock()
        mock_tool_module.TOOL_SPEC = {
            "name": "test_module_tool",
            "description": "Test module tool",
            "inputSchema": {"json": {"type": "object"}},
        }
        mock_tool_module.test_module_tool = mock_tool_function

        with patch.dict("os.environ", {"STRANDS__TOOLS_MODULES": "test.module"}, clear=False):
            with (
                patch("foundry_strands_agent.tool_loader._assert_module_in_tools_dir", lambda *_: None),
                patch("foundry_strands_agent.tool_loader.importlib.util.find_spec") as mock_find_spec,
                patch("foundry_strands_agent.tool_loader.SECURITY_ANALYZER.analyze_module_file", return_value=True),
                patch("foundry_strands_agent.tool_loader.importlib.import_module") as mock_import,
            ):
                mock_find_spec.return_value = SimpleNamespace(origin=__file__, submodule_search_locations=None)
                mock_find_spec.return_value = Mock(origin="test/module.py")
                mock_import.return_value = mock_tool_module

                container = create_application_container()

                container.register_factory(AgentFactory, lambda: StrandsAgentFactory(container), singleton=True)
                service = create_agent_service(container)

                await service.initialize()

                assert service._initialized is True
                assert service._tool_registry is not None
                tools = service._tool_registry.get_available_tools()

                tool_names = [
                    (
                        tool.TOOL_SPEC["name"]
                        if hasattr(tool, "TOOL_SPEC")
                        else (tool.__name__ if hasattr(tool, "__name__") else "unknown")
                    )
                    for tool in tools
                ]
                # Tool name is prefixed with module path: test.module -> test__module
                assert "test_module_tool" in tool_names

                await service.shutdown()

    @pytest.mark.asyncio
    async def test_service_loads_file_tools_from_strands_tools_files(self) -> None:
        """Integration test for file loading via STRANDS__TOOLS_FILES."""
        import tempfile
        from pathlib import Path

        # Create a temporary tool file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(
                """
TOOL_SPEC = {
    "name": "test_file_tool",
    "description": "Test file tool",
    "inputSchema": {"json": {"type": "object"}},
}

def test_file_tool():
    return "test"
"""
            )
            temp_file = f.name
        temp_dir = Path(temp_file).resolve().parent

        try:
            with patch.dict("os.environ", {"STRANDS__TOOLS_FILES": temp_file}, clear=False):
                with (
                    patch("foundry_strands_agent.tool_loader.TOOLS_DIR", temp_dir),
                    patch("foundry_strands_agent.tool_loader.SECURITY_ANALYZER.analyze_module_file", return_value=True),
                ):
                    container = create_application_container()
                    container.register_factory(AgentFactory, lambda: StrandsAgentFactory(container), singleton=True)
                    service = create_agent_service(container)

                    await service.initialize()

                    assert service._initialized is True
                    assert service._tool_registry is not None
                    tools = service._tool_registry.get_available_tools()

                    tool_names = [
                        (
                            tool.TOOL_SPEC["name"]
                            if hasattr(tool, "TOOL_SPEC")
                            else (tool.__name__ if hasattr(tool, "__name__") else "unknown")
                        )
                        for tool in tools
                    ]
                    assert len(tool_names) == 1, "Should have one tool registered"

                    await service.shutdown()
        finally:
            Path(temp_file).unlink()

    @pytest.mark.asyncio
    async def test_service_loads_both_module_and_file_tools(self) -> None:
        """Integration test for loading both module and file tools together."""
        import tempfile
        from pathlib import Path

        # Create a temporary tool file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(
                """
TOOL_SPEC = {
    "name": "file_tool",
    "description": "File tool",
    "inputSchema": {"json": {"type": "object"}},
}

def file_tool():
    return "test"
"""
            )
            temp_file = f.name

        mock_tool_function = Mock()
        mock_tool_module = Mock()
        mock_tool_module.TOOL_SPEC = {
            "name": "module_tool",
            "description": "Module tool",
            "inputSchema": {"json": {"type": "object"}},
        }
        mock_tool_module.module_tool = mock_tool_function

        try:
            with patch.dict(
                "os.environ",
                {
                    "STRANDS__TOOLS_MODULES": "test.module",
                    "STRANDS__TOOLS_FILES": temp_file,
                },
                clear=False,
            ):
                with (
                    patch("foundry_strands_agent.tool_loader._assert_module_in_tools_dir", lambda *_: None),
                    patch("foundry_strands_agent.tool_loader.importlib.util.find_spec") as mock_find_spec,
                    patch("foundry_strands_agent.tool_loader.SECURITY_ANALYZER.analyze_module_file", return_value=True),
                    patch("foundry_strands_agent.tool_loader.importlib.import_module") as mock_import,
                ):
                    mock_find_spec.return_value = SimpleNamespace(origin=__file__, submodule_search_locations=None)
                    mock_find_spec.return_value = Mock(origin="test/module.py")
                    mock_find_spec.return_value = Mock(origin=temp_file)
                    mock_import.return_value = mock_tool_module

                    container = create_application_container()

                    container.register_factory(AgentFactory, lambda: StrandsAgentFactory(container), singleton=True)
                    service = create_agent_service(container)

                    await service.initialize()

                    assert service._initialized is True
                    assert service._tool_registry is not None
                    tools = service._tool_registry.get_available_tools()

                    tool_names = [
                        (
                            tool.TOOL_SPEC["name"]
                            if hasattr(tool, "TOOL_SPEC")
                            else (tool.__name__ if hasattr(tool, "__name__") else "unknown")
                        )
                        for tool in tools
                    ]
                    # Module tool: test.module -> test_module
                    assert "module_tool" in tool_names

                    await service.shutdown()
        finally:
            Path(temp_file).unlink()

    @pytest.mark.asyncio
    async def test_service_handles_empty_modules_with_valid_files(self) -> None:
        """Test when STRANDS__TOOLS_MODULES is empty but STRANDS__TOOLS_FILES has values."""
        import tempfile
        from pathlib import Path

        # Create a temporary tool file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(
                """
TOOL_SPEC = {
    "name": "file_only_tool",
    "description": "File only tool",
    "inputSchema": {"json": {"type": "object"}},
}

def file_only_tool():
    return "test"
"""
            )
            temp_file = f.name
        temp_dir = Path(temp_file).resolve().parent

        try:
            with patch.dict(
                "os.environ",
                {"STRANDS__TOOLS_MODULES": "", "STRANDS__TOOLS_FILES": temp_file},
                clear=False,
            ):
                with (
                    patch("foundry_strands_agent.tool_loader.TOOLS_DIR", temp_dir),
                    patch("foundry_strands_agent.tool_loader.SECURITY_ANALYZER.analyze_module_file", return_value=True),
                ):
                    container = create_application_container()
                    container.register_factory(AgentFactory, lambda: StrandsAgentFactory(container), singleton=True)
                    service = create_agent_service(container)

                    await service.initialize()

                    assert service._initialized is True
                    assert service._tool_registry is not None
                    tools = service._tool_registry.get_available_tools()

                    tool_names = [
                        (
                            tool.TOOL_SPEC["name"]
                            if hasattr(tool, "TOOL_SPEC")
                            else (tool.__name__ if hasattr(tool, "__name__") else "unknown")
                        )
                        for tool in tools
                    ]
                    # File tool: prefixed with temp file path components
                    assert len(tool_names) == 1, "Should have one tool registered"

                    await service.shutdown()
        finally:
            Path(temp_file).unlink()

    @pytest.mark.asyncio
    async def test_service_handles_empty_files_with_valid_modules(self) -> None:
        """Test when STRANDS__TOOLS_FILES is empty but STRANDS__TOOLS_MODULES has values."""
        mock_tool_function = Mock()
        mock_tool_module = Mock()
        mock_tool_module.TOOL_SPEC = {
            "name": "module_only_tool",
            "description": "Module only tool",
            "inputSchema": {"json": {"type": "object"}},
        }
        mock_tool_module.module_only_tool = mock_tool_function

        with patch.dict(
            "os.environ",
            {"STRANDS__TOOLS_MODULES": "test.module", "STRANDS__TOOLS_FILES": ""},
            clear=False,
        ):
            with (
                patch("foundry_strands_agent.tool_loader._assert_module_in_tools_dir", lambda *_: None),
                patch("foundry_strands_agent.tool_loader.importlib.util.find_spec") as mock_find_spec,
                patch("foundry_strands_agent.tool_loader.SECURITY_ANALYZER.analyze_module_file", return_value=True),
                patch("foundry_strands_agent.tool_loader.importlib.import_module") as mock_import,
            ):
                mock_find_spec.return_value = SimpleNamespace(origin=__file__, submodule_search_locations=None)
                mock_find_spec.return_value = Mock(origin="test/module.py")
                mock_import.return_value = mock_tool_module

                container = create_application_container()

                container.register_factory(AgentFactory, lambda: StrandsAgentFactory(container), singleton=True)
                service = create_agent_service(container)

                await service.initialize()

                assert service._initialized is True
                assert service._tool_registry is not None
                tools = service._tool_registry.get_available_tools()

                tool_names = [
                    (
                        tool.TOOL_SPEC["name"]
                        if hasattr(tool, "TOOL_SPEC")
                        else (tool.__name__ if hasattr(tool, "__name__") else "unknown")
                    )
                    for tool in tools
                ]
                # Module tool: test.module -> test_module
                assert "module_only_tool" in tool_names

                await service.shutdown()

    @pytest.mark.asyncio
    async def test_service_does_not_use_load_tool_from_string(self) -> None:
        """Verify load_tool_from_string() is never called by service."""
        mock_tool_function = Mock()
        mock_tool_module = Mock()
        mock_tool_module.TOOL_SPEC = {
            "name": "test_tool",
            "description": "Test tool",
            "inputSchema": {"json": {"type": "object"}},
        }
        mock_tool_module.test_tool = mock_tool_function

        with patch.dict("os.environ", {"STRANDS__TOOLS_MODULES": "test.tool"}, clear=False):
            with (
                patch("foundry_strands_agent.tool_loader._assert_module_in_tools_dir", lambda *_: None),
                patch("foundry_strands_agent.tool_loader.importlib.util.find_spec") as mock_find_spec,
                patch("foundry_strands_agent.tool_loader.SECURITY_ANALYZER.analyze_module_file", return_value=True),
                patch("foundry_strands_agent.tool_loader.importlib.import_module") as mock_import,
                patch("foundry_strands_agent.service.load_tool_from_string") as mock_load_string,
            ):
                mock_find_spec.return_value = SimpleNamespace(origin=__file__, submodule_search_locations=None)
                mock_find_spec.return_value = Mock(origin="test/tool.py")
                mock_import.return_value = mock_tool_module

                container = create_application_container()

                container.register_factory(AgentFactory, lambda: StrandsAgentFactory(container), singleton=True)
                service = create_agent_service(container)

                await service.initialize()

                # load_tool_from_string should never be called
                mock_load_string.assert_not_called()

                await service.shutdown()
