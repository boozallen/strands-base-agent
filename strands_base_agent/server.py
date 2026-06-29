# Copyright 2026 Booz Allen Hamilton Inc.
# SPDX-License-Identifier: Apache-2.0
"""A2A server entry point.

Provides the entry point for starting application and A2A protocol servers.
"""

import asyncio
import logging
import os
import threading
from contextlib import asynccontextmanager
from typing import Any, Self, cast

import uvicorn
from a2a.utils.errors import ServerError
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from strands.multiagent.a2a.server import A2AServer

from foundry_agent_core import AgentBackend
from foundry_strands_agent import AgentConfig, AgentFactory, StrandsAgentBackend, StrandsAgentFactory

from strands_base_agent.application.factory import create_application_container
from strands_base_agent.application.lifecycle import boot_system
from strands_base_agent.application.runtime_container import set_runtime_container

logger = logging.getLogger(__name__)


class MCPReconnectExhaustedError(RuntimeError):
    """Raised when MCP reconnect + retry still fails."""


class ReconnectingAgentProxy:
    """A proxy for an agent that reconnects to an MCP server if it fails."""

    def __init__(self, agent, agent_factory, max_retries: int = 1):
        self._agent_factory = agent_factory
        self._max_retries = max_retries
        self._lock = threading.RLock()
        self._agent = agent
        self._needs_rebuild = False

    @classmethod
    async def create(cls, agent_factory, max_retries: int = 1) -> Self:
        agent = await agent_factory.create_agent()
        return cls(agent, agent_factory, max_retries=max_retries)

    async def _recreate_agent_async(self) -> None:
        logger.info("Recreating agent due to MCP error...")

        old = None
        new_agent = await self._agent_factory.create_agent()

        with self._lock:
            old = self._agent
            self._agent = new_agent

        close_fn = getattr(old, "close", None)
        if callable(close_fn):
            try:
                maybe_coro = close_fn()
                if asyncio.iscoroutine(maybe_coro):
                    await maybe_coro
            except Exception:
                pass

        logger.info("Agent recreated successfully")

    def _is_mcp_error(self, err: Exception) -> bool:
        text = str(err).lower()
        markers = (
            "mcp",
            "mcpconnectionerror",
            "mcpclientinitializationerror",
            "client session is not running",
            "connection to the mcp server was closed",
            "streamablehttp",
        )
        return any(m in text for m in markers)

    def _event_has_mcp_failure(self, event: object) -> bool:
        text = f"{event!r} {event}".lower()
        markers = (
            "mcpclientinitializationerror",
            "client session is not running",
            "connection to the mcp server was closed",
            "tool execution failed",
            "failed to process tool",
            "Connection to the MCP server was closed",
        )
        return any(m in text for m in markers)

    def mark_stale(self) -> None:
        with self._lock:
            self._needs_rebuild = True

    async def _ensure_fresh_agent(self) -> None:
        with self._lock:
            needs_rebuild = self._needs_rebuild
            if needs_rebuild:
                self._needs_rebuild = False

        if not needs_rebuild:
            return

        await self._recreate_agent_async()

    async def _stream_once(self, *args, **kwargs):
        with self._lock:
            agent = self._agent
        async for event in agent.stream_async(*args, **kwargs):
            yield event

    def stream_async(self, *args, **kwargs):
        async def _gen():
            for attempt in range(self._max_retries + 1):
                await self._ensure_fresh_agent()
                saw_mcp_failure = False
                try:
                    async for event in self._stream_once(*args, **kwargs):
                        if self._event_has_mcp_failure(event):
                            saw_mcp_failure = True
                            self.mark_stale()
                            break
                        yield event
                except Exception as e:
                    if self._is_mcp_error(e):
                        saw_mcp_failure = True
                        self.mark_stale()
                    else:
                        raise

                if not saw_mcp_failure:
                    return

                if attempt < self._max_retries:
                    await self._ensure_fresh_agent()
                    continue

                # exhausted: emit explicit stream error event instead of silent end
                yield {
                    "type": "error",
                    "error": "mcp_reconnect_failed",
                    "message": f"MCP unavailable after {self._max_retries + 1} attempt(s)",
                    "retryable": True,
                }
                return

        return _gen()

    async def invoke_async(self, *args, **kwargs):
        await self._ensure_fresh_agent()
        with self._lock:
            agent = self._agent
        try:
            return await agent.invoke_async(*args, **kwargs)
        except Exception as e:
            if self._is_mcp_error(e):
                self.mark_stale()
                await self._recreate_agent_async()
                with self._lock:
                    agent = self._agent
                return await agent.invoke_async(*args, **kwargs)  # one retry
            raise

    def __getattr__(self, item: str):
        with self._lock:
            return getattr(self._agent, item)

    async def aclose(self) -> None:
        with self._lock:
            agent = self._agent

        close_fn = getattr(agent, "close", None)
        if callable(close_fn):
            result = close_fn()
            if asyncio.iscoroutine(result):
                await result


def start_server() -> None:
    """Start the A2A server.

    This function handles starting an A2A protocol server.

    This function is blocking and will not return until the server is shut down.

    Raises:
        ImportError: If A2A dependencies are not installed
        RuntimeError: If server initialization fails or if called in client mode
    """
    # Load configuration
    config = AgentConfig.from_env()

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

    # Create agent using the factory pattern (register for FastAPI deps — see runtime_container)
    container = create_application_container()

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

    # Agent instance created async in lifespan; placeholder for closure reference
    agent_instance: ReconnectingAgentProxy | None = None

    # Create A2A server — agent_instance is set before requests arrive via lifespan.
    # A2AServer.__init__ eagerly accesses .name, .description on the agent (for the
    # agent card) and passes it to StrandsA2AExecutor which checks ._session_manager
    # and calls .take_snapshot(). We satisfy those during construction with safe
    # defaults; all runtime access defers to the real agent once lifespan initializes it.
    class _NoOpToolRegistry:
        """Stub registry for agent card construction before real agent exists."""

        def get_all_tools_config(self):
            return {}

    class _LazyAgentProxy:
        """Provides card metadata for A2AServer construction; defers runtime access."""

        name = config.agent_name
        description = config.agent_description
        _session_manager = None
        tool_registry = _NoOpToolRegistry()

        def take_snapshot(self, **kwargs):
            return None

        def __getattr__(self, item: str):
            if agent_instance is None:
                raise RuntimeError("Agent not yet initialized")
            return getattr(agent_instance, item)

    a2a_server = A2AServer(
        agent=cast(Any, _LazyAgentProxy()),
        host=host,
        port=port,
        http_url=agent_public_url,
        version=version,
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

    from strands_base_agent.api.routes import chat_history_router, query_router

    fastapi_app.include_router(health_router)
    fastapi_app.include_router(query_router)
    fastapi_app.include_router(chat_history_router)

    original_lifespan = fastapi_app.router.lifespan_context

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        nonlocal agent_instance
        async with original_lifespan(app):
            try:
                agent_instance = await ReconnectingAgentProxy.create(agent_factory, max_retries=1)
                agent_instance._agent.name = config.agent_name
                agent_instance._agent.description = config.agent_description
                yield
            finally:
                try:
                    if agent_instance is not None:
                        await agent_instance.aclose()
                except Exception as e:
                    logger.warning("Agent shutdown cleanup warning: %s", e)

    fastapi_app.router.lifespan_context = lifespan

    def _is_mcp_chain(exc: Exception) -> bool:
        markers = (
            "mcpclientinitializationerror",
            "client session is not running",
            "connection to the mcp server was closed",
            "mcp",
        )
        seen = set()
        cur: BaseException | None = exc
        while cur and id(cur) not in seen:
            seen.add(id(cur))
            msg = str(cur).lower()
            if any(m in msg for m in markers):
                return True
            cur = cur.__cause__ or cur.__context__
        return False

    @fastapi_app.exception_handler(ServerError)
    async def handle_a2a_server_error(_: Request, exc: ServerError):  # pyright: ignore[reportUnusedFunction]
        if _is_mcp_chain(exc) and agent_instance is not None:
            agent_instance.mark_stale()
            return JSONResponse(
                status_code=400,
                content={
                    "error": "mcp_session_stale",
                    "message": "MCP session became stale; retry the request.",
                    "retryable": True,
                },
            )

        return JSONResponse(
            status_code=500,
            content={"error": "internal_error", "message": "A2A server error"},
        )

    @fastapi_app.exception_handler(MCPReconnectExhaustedError)
    async def handle_mcp_reconnect_exhausted(_: Request, exc: MCPReconnectExhaustedError):  # pyright: ignore[reportUnusedFunction]
        return JSONResponse(
            status_code=400,
            content={
                "error": "mcp_reconnect_failed",
                "message": str(exc),
                "retryable": True,
            },
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
