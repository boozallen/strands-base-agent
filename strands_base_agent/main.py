# Copyright 2026 Booz Allen Hamilton Inc.
# SPDX-License-Identifier: Apache-2.0
"""Interface-agnostic query processing function for Strands Base Agent.

Provides reusable `process_query()` function that can be embedded in any interface
(CLI, HTTP, scripts, Lambda functions) using existing service lifecycle patterns.
"""

from foundry_agent_core import AgentRequest, AgentResponse
from foundry_strands_agent import AgentFactory, StrandsAgentFactory, create_agent_service

from strands_base_agent.application.factory import create_application_container


async def process_query(query_text: str) -> AgentResponse:
    """Process a single query using the Strands Base Agent.

    Interface-agnostic function that can be embedded in CLI, HTTP, Lambda, etc.

    Args:
        query_text: The query text to process

    Returns:
        AgentResponse containing the agent's response

    Raises:
        Various exceptions from agent processing pipeline
    """
    container = create_application_container()
    container.register_factory(AgentFactory, lambda: StrandsAgentFactory(container), singleton=True)
    service = create_agent_service(container)
    agent_request = AgentRequest(query=query_text)

    async with service.service_lifecycle() as active_service:
        return await active_service.process_query(agent_request)
