# Copyright 2026 Booz Allen Hamilton Inc.
# SPDX-License-Identifier: Apache-2.0
# ruff: noqa: T201
"""Generate docs/openapi.yml from the query router's OpenAPI schema.

Run with: uv run python scripts/generate_openapi.py
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from fastapi import FastAPI

from strands_base_agent.api.routes.query import router as query_router

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PATH = REPO_ROOT / "docs" / "openapi.yml"


def build_schema() -> dict[str, Any]:
    """Return the OpenAPI schema for the published query endpoints."""
    app = FastAPI(
        title="Strands Base Agent API",
        description="HTTP REST interface for query processing via the Strands agent.",
        version="1.0.0",
    )
    app.include_router(query_router)
    schema = app.openapi()
    # Bearer auth is enforced in middleware, which FastAPI cannot see.
    schema.setdefault("components", {})["securitySchemes"] = {"HTTPBearer": {"type": "http", "scheme": "bearer"}}
    for operations in schema["paths"].values():
        for operation in operations.values():
            operation["security"] = [{"HTTPBearer": []}]
            operation["responses"]["401"] = {
                "description": "Missing or invalid bearer token",
                "headers": {"WWW-Authenticate": {"schema": {"type": "string"}, "description": "Bearer"}},
                "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}},
            }
    return schema


def main() -> None:
    """Write the current query OpenAPI schema to docs/openapi.yml."""
    OUTPUT_PATH.write_text(yaml.safe_dump(build_schema(), sort_keys=False))
    print(f"Wrote OpenAPI schema to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
