---
sidebar_position: 2
---

# Adding Tools

Tools give your agent domain-specific capabilities. Strands supports two ways to define them: the `@tool` decorator (most common) and the `TOOL_SPEC` module pattern.

## Using `@tool` (Recommended)

1. Create a Python file inside `strands_base_agent/tools/`.

2. Configure the tool path in `config.yaml`:

   ```yaml
   tools_files:
     - strands_base_agent/tools/local_tools.py
   ```

   Or via environment variable:

   ```bash
   export STRANDS__TOOLS_FILES=strands_base_agent/tools/local_tools.py
   ```

   For multiple files, use a YAML list or a comma-separated string.

3. Decorate each function with `@tool`, include type hints and a docstring:

   ```python
   from strands import tool


   @tool
   def flip_coin() -> bool:
       """
       Flips a coin.

       Returns:
           Returns True for heads and False for tails.
       """
       import random
       return random.random() >= 0.5


   @tool
   def check_app_approval_status(app_name: str) -> bool:
       """
       Checks if a given app is approved for use.

       Args:
           app_name: the name of the app

       Returns:
           Returns True if the app is approved.
       """
       return "ai" not in app_name
   ```

The docstring is what the model sees — write it clearly. Describe what the tool does, when to use it, what arguments mean, and what it returns.

## Using `TOOL_SPEC`

For tools that need explicit JSON Schema input definitions:

1. Create a Python file inside `strands_base_agent/tools/`. With `TOOL_SPEC` module loading, you may only have one tool per file, and the file name must match the tool name.

2. Configure the module path in `config.yaml`:

   ```yaml
   tools_modules:
     - strands_base_agent.tools.send_report
   ```

   Or via environment variable:

   ```bash
   export STRANDS__TOOLS_MODULES=strands_base_agent.tools.send_report
   ```

3. Define `TOOL_SPEC` and the implementation function in the module:

   ```python
   TOOL_SPEC = {
       "name": "send_report",
       "description": "Submit a report to a manager.",
       "inputSchema": {
           "json": {
               "type": "object",
               "properties": {
                   "content": {
                       "type": "string",
                       "description": "The items in the report",
                   },
               },
               "required": ["content"],
           }
       },
   }


   def send_report(tool, **kwargs):
       tool_use_id = tool["toolUseId"]
       tool_input = tool["input"]
       content = tool_input.get("content")

       result = "Report submitted successfully."

       return {
           "toolUseId": tool_use_id,
           "status": "success",
           "content": [{"text": result}],
       }
   ```

For the full `TOOL_SPEC` reference, see the [Strands documentation](https://strandsagents.com/latest/documentation/docs/user-guide/concepts/tools/custom-tools/#module-based-tools-python-only).

## Verifying Tools Loaded

Run the agent and check the startup logs — registered tools are logged when the agent factory builds the tool registry. Then ask the agent something that should trigger your tool:

```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Flip a coin for me"}'
```
## Note on CLI Functionality

Please note that local tools are not supported when running the agent in the CLI. They will fail to load. MCP tools may still be used, however.
