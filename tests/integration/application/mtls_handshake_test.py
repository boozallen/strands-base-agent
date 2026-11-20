# Copyright 2026 Booz Allen Hamilton Inc.
# SPDX-License-Identifier: Apache-2.0
"""Integration tests for mTLS handshake behavior."""

import asyncio
import ssl
import threading
from collections.abc import Generator

import pytest
import trustme
import uvicorn
from fastapi import FastAPI


@pytest.fixture
def ca() -> trustme.CA:
    return trustme.CA()


@pytest.fixture
def server_ssl_ctx(ca: trustme.CA) -> ssl.SSLContext:
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    server_cert = ca.issue_cert("localhost", "127.0.0.1")
    server_cert.configure_cert(ctx)
    ca.configure_trust(ctx)
    ctx.verify_mode = ssl.CERT_REQUIRED
    return ctx


@pytest.fixture
def client_ssl_ctx(ca: trustme.CA) -> ssl.SSLContext:
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ca.configure_trust(ctx)
    client_cert = ca.issue_cert("client")
    client_cert.configure_cert(ctx)
    return ctx


@pytest.fixture
def untrusted_client_ssl_ctx() -> ssl.SSLContext:
    other_ca = trustme.CA()
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    other_ca.configure_trust(ctx)
    client_cert = other_ca.issue_cert("rogue-client")
    client_cert.configure_cert(ctx)
    return ctx


@pytest.fixture
def mtls_server(ca: trustme.CA) -> Generator[int]:
    """Start a uvicorn server with mTLS enabled using trustme certs."""
    import tempfile
    from pathlib import Path

    tmp = Path(tempfile.mkdtemp())

    server_cert = ca.issue_cert("localhost", "127.0.0.1")
    key_file = tmp / "server.key"
    cert_file = tmp / "server.pem"
    ca_file = tmp / "ca.pem"

    server_cert.private_key_pem.write_to_path(str(key_file))
    with open(cert_file, "wb") as f:
        for blob in server_cert.cert_chain_pems:
            f.write(blob.bytes())
    ca.cert_pem.write_to_path(str(ca_file))

    app = FastAPI()

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    config = uvicorn.Config(
        app,
        host="127.0.0.1",
        port=0,
        ssl_keyfile=str(key_file),
        ssl_certfile=str(cert_file),
        ssl_ca_certs=str(ca_file),
        ssl_cert_reqs=ssl.CERT_REQUIRED,
        log_level="error",
    )
    server = uvicorn.Server(config)

    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    # Wait for server to start
    for _ in range(50):
        if server.started:
            break
        import time

        time.sleep(0.1)

    # Get the actual port
    sockets = server.servers[0].sockets if server.servers else []
    port = sockets[0].getsockname()[1] if sockets else 0

    yield port

    server.should_exit = True
    thread.join(timeout=5)


class TestMtlsHandshake:
    def test_rejects_client_without_certificate(self, mtls_server: int, ca: trustme.CA) -> None:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ca.configure_trust(ctx)

        with pytest.raises((ssl.SSLError, ConnectionResetError, OSError)):
            asyncio.run(self._connect(mtls_server, ctx))

    def test_accepts_client_with_valid_certificate(self, mtls_server: int, client_ssl_ctx: ssl.SSLContext) -> None:
        result = asyncio.run(self._connect(mtls_server, client_ssl_ctx))
        assert result == 200

    def test_rejects_client_with_untrusted_certificate(
        self, mtls_server: int, untrusted_client_ssl_ctx: ssl.SSLContext
    ) -> None:
        with pytest.raises((ssl.SSLError, ConnectionResetError, OSError)):
            asyncio.run(self._connect(mtls_server, untrusted_client_ssl_ctx))

    async def _connect(self, port: int, ssl_ctx: ssl.SSLContext) -> int:
        reader, writer = await asyncio.open_connection("127.0.0.1", port, ssl=ssl_ctx)
        writer.write(b"GET /health HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n")
        await writer.drain()
        response = await reader.read(4096)
        writer.close()
        try:
            await writer.wait_closed()
        except ssl.SSLError:
            pass
        if not response:
            raise ConnectionResetError("Empty response — connection rejected")
        status_line = response.split(b"\r\n")[0]
        return int(status_line.split(b" ")[1])
