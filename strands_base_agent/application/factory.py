# Copyright 2026 Booz Allen Hamilton Inc.
# SPDX-License-Identifier: Apache-2.0
"""Application factory coordinating infrastructure service creation.

Implements application factory function that creates and configures dependency
container with all required infrastructure services for production use.

Registered Protocols
--------------------
This factory registers infrastructure protocols. Agent-layer protocols
(AgentFactory, AgentBackend) are registered in server.py — the composition root.

Core Configuration:
    - AgentConfig: Agent configuration from environment

Infrastructure Services (framework-agnostic):
    - ErrorTranslator: Error classification and translation
    - ResponseProcessor: Agent response transformation

Agent Layer (Strands-coupled):
    - AgentToolRegistry: Tool registration and management
    - ChatHistoryManager: Session and message history
    - QueryProcessor: Query orchestration and processing
"""

import logging
from pathlib import Path

from foundry_agent_core import (
    DependencyContainer,
    ErrorTranslator,
    QueryProcessor,
    ResponseProcessor,
    create_dependency_container,
)
from foundry_agent_core.errors.translator import create_error_translator
from foundry_strands_agent import (
    AgentConfig,
    AgentFactory,
    AgentToolRegistry,
    AgentToolRegistryManager,
    ChatHistorian,
    ChatHistoryManager,
    DefaultResponseProcessor,
    QueryOrchestrator,
)

logger = logging.getLogger(__name__)


def create_application_container() -> DependencyContainer:
    """Create production application dependency container.

    Creates and configures a dependency container with infrastructure services.
    AgentFactory and AgentBackend are registered in server.py (composition root).

    Returns:
        DependencyContainer configured with protocol implementations

    Raises:
        InvalidConfigurationError: If environment configuration is invalid
    """
    yaml_path = Path("config.yaml")
    if yaml_path.exists():
        config = AgentConfig.from_yaml(yaml_path, "STRANDS")
    else:
        config = AgentConfig.from_env()

    container = create_dependency_container()

    container.register_factory(AgentConfig, lambda: config, singleton=True)

    # Register infrastructure services
    container.register_factory(
        ErrorTranslator,
        lambda: create_error_translator(),
        singleton=True,
    )

    container.register_factory(
        ResponseProcessor,
        lambda: DefaultResponseProcessor(),
        singleton=True,
    )

    # ==========================================================================
    # Agent Layer (Strands-coupled)
    # ==========================================================================
    # NOTE: AgentFactory is registered by the entry point (server.py, main.py)
    # as it is the composition root extension point for adopters.

    container.register_factory(
        AgentToolRegistry,
        lambda: AgentToolRegistryManager(container),
        singleton=True,
    )

    # ==========================================================================
    # Services with Dependencies
    # ==========================================================================
    container.register_factory_with_dependencies(
        ChatHistoryManager,
        lambda factory: ChatHistorian(factory),
        dependencies=[AgentFactory],
        singleton=True,
    )

    container.register_factory_with_dependencies(
        QueryProcessor,
        lambda factory, registry, processor: QueryOrchestrator(container, factory, registry, processor),
        dependencies=[AgentFactory, AgentToolRegistry, ResponseProcessor],
        singleton=True,
    )

    logger.info(
        "Application container created",
        extra={"registered_types": len(container.get_registered_types())},
    )

    return container
