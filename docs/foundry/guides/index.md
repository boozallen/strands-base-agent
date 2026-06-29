---
sidebar_position: 5
---

# Guides

Practical guides for extending a Strands Base Agent fork.

- **[After You Fork](./after-you-fork.md)** — the path from a fresh clone to a customized agent
- **[Adding Tools](./adding-tools.md)** — give your agent domain-specific capabilities with `@tool` or `TOOL_SPEC`
- **[Adding API Endpoints](./adding-api-endpoints.md)** — expose new HTTP routes alongside `/api/v1/query`
- **[Customizing the Server](./customizing-server.md)** — wire custom session managers, model providers, or backends in `server.py`
- **[MCP Servers](./mcp-servers.md)** — connect external tool servers via Model Context Protocol
- **[Guardrails](./guardrails.md)** — set up AWS Bedrock Guardrails for safety filtering
- **[Embedding `process_query`](./embedding-process-query.md)** — use the agent from CLI, Lambda, or other interfaces
- **[Built-in HTTP API](./http-api.md)** — reference for the query, streaming, and chat history endpoints
- **[Built-in A2A Protocol](./a2a-protocol.md)** — reference for the agent card, JSON-RPC, and streaming routes
