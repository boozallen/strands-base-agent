# Public Chainguard Python dev image (currently Python 3.14).
# `latest-dev` is the floating tag offered in the free public catalog.
FROM cgr.dev/chainguard/python:latest-dev AS base

# switch to root user
USER root

###

FROM base AS builder

COPY --from=ghcr.io/astral-sh/uv:0.9 /uv /uvx /bin/

ENV SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt \
    UV_COMPILE_BYTECODE=true \
    UV_LINK_MODE=copy \
    UV_NO_INSTALLER_METADATA=true \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-dev --no-editable --no-install-project --no-install-workspace

# Copy source code and configuration
COPY --link strands_base_agent ./strands_base_agent
COPY --link config.yaml ./config.yaml

###

# NOTE: Production currently inherits from `base`, which uses the Chainguard
# `python:latest-dev` image (ships a shell, apk, and build toolchain). For a
# hardened production image we should switch this stage to the distroless
# variant (`cgr.dev/chainguard/python:latest`, no `-dev` suffix) — smaller
# surface, fewer CVEs, no shell. Doing so requires moving the `install -d
# /app/sessions` step into the builder stage (distroless has no shell to run
# RUN commands).
FROM base AS production

LABEL org.opencontainers.image.source="https://github.com/boozallen/TBD" \
      org.opencontainers.image.licenses="Apache-2.0" \
      org.opencontainers.image.description="Foundry Strands base agent"

COPY --link --from=builder --chown=65532:65532 /app /app

# Pre-create the FileSessionManager storage dir owned by the runtime user so
# fresh volumes mounted here (Docker named volume, k8s emptyDir, etc.) inherit
# the right ownership and the SDK can write session files at runtime.
RUN install -d -o 65532 -g 65532 /app/sessions

# Set default environment variables
ENV PATH="/app/.venv/bin:$PATH" \
    SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

USER 65532:65532
WORKDIR /app

EXPOSE 8000

# Base image may set ENTRYPOINT ["python"]; without clearing it, CMD would become
# `python python -m ...` and Python would try to run /app/python as a script.
ENTRYPOINT []
CMD ["python", "-m", "strands_base_agent.server"]
