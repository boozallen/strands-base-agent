# Copyright 2026 Booz Allen Hamilton Inc.
# SPDX-License-Identifier: Apache-2.0
"""FastAPI dependency injection integration with application container.

Bridges FastAPI's dependency injection with the process-wide
`DependencyContainer` from `application.runtime_container` (initialized at
application startup), so route handlers share one container graph instead of
building a new one per request.
"""

from typing import Annotated

from fastapi import Depends, Request

from foundry_agent_core import AgentBackend, DependencyContainer
from foundry_strands_agent import AgentService, ChatHistoryManager, create_agent_service

from strands_base_agent.application.runtime_container import get_dependency_container


def get_container() -> DependencyContainer:
    return get_dependency_container()


def get_agent_backend(container: Annotated[DependencyContainer, Depends(get_container)]) -> AgentBackend:
    return container.resolve(AgentBackend)


def get_agent_service(container: Annotated[DependencyContainer, Depends(get_container)]) -> AgentService:
    return create_agent_service(container)


def get_chat_history_manager(
    container: Annotated[DependencyContainer, Depends(get_container)],
) -> ChatHistoryManager:
    return container.resolve(ChatHistoryManager)


def get_correlation_id(request: Request) -> str:
    try:
        return getattr(request.state, "correlation_id", "")
    except AttributeError:
        return ""


ContainerDep = Annotated[DependencyContainer, Depends(get_container)]
AgentBackendDep = Annotated[AgentBackend, Depends(get_agent_backend)]
AgentServiceDep = Annotated[AgentService, Depends(get_agent_service)]
ChatHistoryManagerDep = Annotated[ChatHistoryManager, Depends(get_chat_history_manager)]
CorrelationIdDep = Annotated[str, Depends(get_correlation_id)]
