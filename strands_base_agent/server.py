# Copyright 2026 Booz Allen Hamilton Inc.
# SPDX-License-Identifier: Apache-2.0
"""A2A server entry point.

Provides the entry point for starting application and A2A protocol servers.
"""

import logging
import os
import re
from contextlib import asynccontextmanager
from typing import Protocol, cast

import uvicorn
from a2a import types as a2a_types
from a2a.types import InvalidParamsError
from a2a.utils.errors import ServerError
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from strands import Agent
from strands.multiagent.a2a.executor import StrandsA2AExecutor
from strands.multiagent.a2a.server import A2AServer

from foundry_agent_core import AgentBackend, AgentCreationError
from foundry_strands_agent import AgentConfig, AgentFactory, StrandsAgentBackend, StrandsAgentFactory
from foundry_strands_agent.factory import AgentBuilder

from strands_base_agent.application.factory import create_application_container
from strands_base_agent.application.lifecycle import boot_system
from strands_base_agent.application.runtime_container import set_runtime_container

logger = logging.getLogger(__name__)


_AUTH_EXEMPT_PATHS = frozenset(
    {
        "/api/v1/health",
        "/.well-known/agent.json",
        "/.well-known/agent-card.json",
    }
)


class _SupportsAgentBuilder(Protocol):
    """An AgentFactory that can prepare a builder for per-context A2A agents."""

    async def create_agent_builder(self) -> AgentBuilder: ...


# The context id A2AServer passes to agent_factory when it builds the agent card
# at construction (strands.multiagent.a2a.server._AGENT_CARD_CONTEXT_ID).
_A2A_AGENT_CARD_CONTEXT_ID = "__agent_card__"

# A2A sessions share session_storage_dir / session_s3_prefix with REST sessions.
# REST session_ids allow only letters, digits, "_" and "-", so the "." keeps the
# two apart in both directions.
_A2A_SESSION_ID_PREFIX = "a2a."

_INVALID_CONTEXT_ID_MESSAGE = "Invalid contextId: use at most 124 letters, digits, '.', '_', or '-', not ending in '.'"


# Each retained context holds a full Agent with its message history, so the
# limit is a memory knob. The cap keeps a typo from exhausting memory.
_A2A_MAX_CONTEXTS_CAP = 10_000


def _a2a_max_contexts() -> int:
    """Per-context agents A2AServer keeps (STRANDS_A2A_MAX_CONTEXTS), SDK default when unset."""
    value = os.getenv("STRANDS_A2A_MAX_CONTEXTS")
    if not value:
        return StrandsA2AExecutor.DEFAULT_MAX_CONTEXTS
    # 1 to 5 ASCII digits: int() accepts "1_000" and " 5 ", and fails past 4300 digits.
    if not re.fullmatch(r"[0-9]{1,5}", value) or not 1 <= int(value) <= _A2A_MAX_CONTEXTS_CAP:
        raise RuntimeError(
            f"STRANDS_A2A_MAX_CONTEXTS must be an integer from 1 to {_A2A_MAX_CONTEXTS_CAP}, got {value!r}"
        )
    return int(value)


def is_auth_exempt(method: str, path: str) -> bool:
    """True when the request may bypass bearer auth (OPTIONS or an exempt path)."""
    path = path.rstrip("/") or "/"
    return method == "OPTIONS" or path in _AUTH_EXEMPT_PATHS


_BEARER_SCHEME_NAME = "bearer"


class _BearerCardA2AServer(A2AServer):
    """A2AServer whose agent card says every A2A call needs the bearer API key."""

    @property
    def public_agent_card(self) -> a2a_types.AgentCard:
        """The SDK's card plus the bearer scheme that _require_bearer_auth enforces."""
        scheme = a2a_types.HTTPAuthSecurityScheme(
            scheme="bearer", description="The API key the server is configured with (STRANDS_API_KEY)."
        )
        return super().public_agent_card.model_copy(
            update={
                "security_schemes": {_BEARER_SCHEME_NAME: a2a_types.SecurityScheme(root=scheme)},
                "security": [{_BEARER_SCHEME_NAME: []}],
            }
        )


def start_server() -> None:
    """Start the A2A server.

    This function handles starting an A2A protocol server.

    This function is blocking and will not return until the server is shut down.

    Raises:
        ImportError: If A2A dependencies are not installed
        RuntimeError: If server initialization fails or if called in client mode
    """
    # Build the DI container first so the one YAML-aware AgentConfig can be resolved from it
    # below, rather than constructing a second, potentially divergent instance via
    # AgentConfig.from_env(). The container is also registered for FastAPI deps (see runtime_container).
    container = create_application_container()
    config = container.resolve(AgentConfig)

    # Get deployment configuration
    host = os.getenv("HOST", "0.0.0.0")
    # Use agent-specific port if configured, otherwise fall back to general PORT
    port = config.agent_port if config.agent_port is not None else int(os.getenv("PORT", "8000"))

    # Get public URL for agent card (use service name in Docker, or AGENT_PUBLIC_URL if set)
    agent_public_url = os.getenv("STRANDS_AGENT_PUBLIC_URL", f"http://{config.agent_name}:{port}")
    if not os.getenv("STRANDS_AGENT_PUBLIC_URL"):
        logger.warning(
            "STRANDS_AGENT_PUBLIC_URL is not set. The agent card will advertise "
            "the default internal URL (%s) which may not be reachable externally. "
            "Set STRANDS_AGENT_PUBLIC_URL to the public ingress URL for production deployments.",
            agent_public_url,
        )

    # Get agent version for A2A identity
    version = config.agent_version

    logger.info("Starting A2A server on %s:%s (version: %s)", host, port, version)
    logger.info("Agent discovery endpoint %s", agent_public_url)

    # Register AgentFactory in the composition root — adopters customize here.
    # Pass session_manager_factories / model_provider_factories dicts to extend.
    container.register_factory(
        AgentFactory,
        lambda: StrandsAgentFactory(container),
        singleton=True,
    )

    container.register_factory(
        AgentBackend,
        lambda: StrandsAgentBackend(container),
        singleton=True,
    )

    set_runtime_container(container)
    agent_factory = container.resolve(AgentFactory)

    # Per-context A2A agents. The one-time setup runs in the
    # lifespan; A2AServer then builds a fresh agent per context_id, so no two
    # conversations share message history, state or session.
    if not callable(getattr(agent_factory, "create_agent_builder", None)):
        raise RuntimeError(
            "The registered AgentFactory does not provide create_agent_builder(), which the A2A "
            "server needs to build a fresh agent per conversation. StrandsAgentFactory provides it."
        )
    strands_agent_factory = cast(_SupportsAgentBuilder, agent_factory)
    agent_builder: AgentBuilder | None = None

    class _NoOpToolRegistry:
        """Empty tool registry, so the agent card lists no skills."""

        def get_all_tools_config(self):
            return {}

    class _AgentCardMetadata:
        """What A2AServer reads to build the agent card: name, description, tools.

        A2AServer calls agent_factory once at construction with the card context
        id, before the lifespan has created the builder. This object answers that
        call from config alone and forwards nothing to a runtime agent.
        """

        name = config.agent_name
        description = config.agent_description
        tool_registry = _NoOpToolRegistry()

    def build_context_agent(context_id: str) -> Agent:
        if agent_builder is None:
            # Only A2AServer's construction-time card build runs before the lifespan.
            if context_id == _A2A_AGENT_CARD_CONTEXT_ID:
                return cast(Agent, _AgentCardMetadata())
            raise RuntimeError("A2A request received before the agent builder was initialized")
        try:
            agent = agent_builder.build(session_id=f"{_A2A_SESSION_ID_PREFIX}{context_id}")
        except AgentCreationError as e:
            # Only build()'s session_id check carries session_id_length; let other failures through.
            if "session_id_length" not in e.context:
                raise
            # A ServerError reaches the client as a JSON-RPC "invalid params" error, not a failed task.
            raise ServerError(error=InvalidParamsError(message=_INVALID_CONTEXT_ID_MESSAGE)) from e
        # The builder names agents from config.yaml; match the card, which uses this config.
        agent.name = config.agent_name
        agent.description = config.agent_description
        return agent

    a2a_server = _BearerCardA2AServer(
        agent_factory=build_context_agent,
        max_contexts=_a2a_max_contexts(),
        host=host,
        port=port,
        http_url=agent_public_url,
        version=version,
        # Stream chunks into one artifact, not one history message per chunk.
        enable_a2a_compliant_streaming=True,
    )

    # Access the underlying FastAPI app
    fastapi_app = a2a_server.to_fastapi_app()

    from foundry_agent_fastapi import (
        add_cors_middleware,
        add_error_handling_middleware,
        add_request_logging_middleware,
        health_router,
    )

    add_cors_middleware(fastapi_app)
    add_request_logging_middleware(fastapi_app)
    add_error_handling_middleware(fastapi_app)

    from strands_base_agent.api.dependencies import is_valid_api_key
    from strands_base_agent.api.routes import chat_history_router, query_router

    @fastapi_app.middleware("http")
    async def _require_bearer_auth(request: Request, call_next):  # pyright: ignore[reportUnusedFunction]
        if is_auth_exempt(request.method, request.url.path):
            return await call_next(request)
        scheme, _, token = request.headers.get("authorization", "").partition(" ")
        if scheme.lower() != "bearer" or not is_valid_api_key(token):
            return JSONResponse(
                status_code=401,
                content={"error": "unauthorized", "message": "Invalid or missing API key"},
                headers={"WWW-Authenticate": "Bearer"},
            )
        return await call_next(request)

    fastapi_app.include_router(health_router)
    fastapi_app.include_router(query_router)
    fastapi_app.include_router(chat_history_router)

    original_lifespan = fastapi_app.router.lifespan_context

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        nonlocal agent_builder
        if not os.environ.get("STRANDS_API_KEY"):
            raise RuntimeError(
                "STRANDS_API_KEY is required and must be non-empty. Set it in the environment (see env.template)."
            )
        async with original_lifespan(app):
            try:
                agent_builder = await strands_agent_factory.create_agent_builder()
                # MCP clients connect when the first agent is built and stop when the
                # last agent holding them is released. Building one here fails startup
                # on a bad MCP config, and holding it keeps the connections open for
                # later contexts until shutdown.
                app.state.a2a_startup_agent = agent_builder.build()
                logger.info("A2A server started")
                yield
            finally:
                app.state.a2a_startup_agent = None
                logger.info("A2A server shutting down")

    fastapi_app.router.lifespan_context = lifespan

    @fastapi_app.exception_handler(ServerError)
    async def handle_a2a_server_error(request: Request, exc: ServerError):  # pyright: ignore[reportUnusedFunction]
        logger.error(
            "A2A server error: %s",
            exc,
            exc_info=exc,
            extra={"correlation_id": getattr(request.state, "correlation_id", None)},
        )
        return JSONResponse(
            status_code=500,
            content={"error": "internal_error", "message": "A2A server error"},
        )

    # Validate TLS posture before starting the server
    from strands_base_agent.application.tls_config import (
        TlsMode,
        load_tls_config,
        validate_tls_config,
    )

    tls_config = load_tls_config()
    validate_tls_config(tls_config)

    # Start server (blocking call)
    if tls_config.tls_mode == TlsMode.NATIVE:
        if tls_config.tls_ca_certfile:
            import ssl

            uvicorn.run(
                fastapi_app,
                host=host,
                port=port,
                ssl_keyfile=tls_config.tls_keyfile,
                ssl_certfile=tls_config.tls_certfile,
                ssl_ca_certs=tls_config.tls_ca_certfile,
                ssl_cert_reqs=ssl.CERT_REQUIRED,
            )
        else:
            uvicorn.run(
                fastapi_app,
                host=host,
                port=port,
                ssl_keyfile=tls_config.tls_keyfile,
                ssl_certfile=tls_config.tls_certfile,
            )
    else:
        uvicorn.run(fastapi_app, host=host, port=port)


if __name__ == "__main__":
    boot_system()
    start_server()
