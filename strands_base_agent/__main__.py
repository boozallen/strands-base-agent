# Copyright 2026 Booz Allen Hamilton Inc.
# SPDX-License-Identifier: Apache-2.0
"""CLI entry point for Strands Base Agent.

Provides command-line interface enabling `python -m strands_base_agent` execution.
Uses the interface-agnostic `process_query()` function from main.py.
"""

import asyncio
import sys


async def cli_main() -> None:
    """CLI-specific entry point."""
    from strands_base_agent.application.lifecycle import boot_system
    from strands_base_agent.main import process_query

    if len(sys.argv) < 2:
        print("Usage: python -m strands_base_agent 'your query here'")  # noqa: T201
        sys.exit(1)

    query = sys.argv[1]
    try:
        boot_system()
        response = await process_query(query)
        print(f"Response: {response.content}")  # noqa: T201
    except Exception as e:
        print(f"Error: {e}")  # noqa: T201
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(cli_main())
