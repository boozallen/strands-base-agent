---
sidebar_position: 2
---

# Adding Tools

Tools give your agent domain-specific capabilities. Strands supports two ways to define them: the `@tool` decorator (most common) and the `TOOL_SPEC` module pattern.

## Using `@tool` (Recommended)

1. Create a Python file inside [`strands_base_agent/tools/`](../../../strands_base_agent/tools/).

2. Configure the tool path in [`config.yaml`](../../../config.yaml):

   ```yaml
   tools_dir: strands_base_agent/tools
   tools_files:
     - strands_base_agent/tools/local_tools.py
   ```

   Or via environment variable:

   ```bash
   export STRANDS__TOOLS_DIR=strands_base_agent/tools
   export STRANDS__TOOLS_FILES=strands_base_agent/tools/local_tools.py
   ```

   Tools load only from inside `tools_dir`. Its default is the container path
   `/app/strands_base_agent/tools`, so without `tools_dir`, local runs (`just run`,
   `just demo`) reject every tool. The relative path works both locally and
   in the container.

   For multiple files, use a YAML list or a comma-separated string.

   Or name the file by its module path in `tools_modules` instead:

   ```yaml
   tools_dir: strands_base_agent/tools
   tools_modules:
     - strands_base_agent.tools.local_tools
   ```

   Or via environment variable:

   ```bash
   export STRANDS__TOOLS_DIR=strands_base_agent/tools
   export STRANDS__TOOLS_MODULES=strands_base_agent.tools.local_tools
   ```

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

1. Create a Python file inside `strands_base_agent/tools/`. A `TOOL_SPEC` file holds one tool, and the file name must match the tool name.

2. Configure the file path in `config.yaml`:

   ```yaml
   tools_dir: strands_base_agent/tools
   tools_files:
     - strands_base_agent/tools/send_report.py
   ```

   Or via environment variable:

   ```bash
   export STRANDS__TOOLS_DIR=strands_base_agent/tools
   export STRANDS__TOOLS_FILES=strands_base_agent/tools/send_report.py
   ```

   List a `TOOL_SPEC` file in `tools_files`, not by module name in `tools_modules`:
   [`foundry-strands-agent`](https://github.com/boozallen/foundry-agent-packages/blob/HEAD/docs/foundry/packages/foundry-strands-agent/index.md) 3.2.1 and earlier drop a `TOOL_SPEC` module listed in
   `tools_modules` without an error, so the agent never gets the tool.

3. Define `TOOL_SPEC` and the implementation function in the file:

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

For the full `TOOL_SPEC` reference, see [Module Based Tools](https://strandsagents.com/docs/user-guide/sdk/tools/custom-tools/#module-based-tools) in the Strands documentation.

## Verifying Tools Loaded

Run the agent and check the startup logs — registered tools are logged when the agent factory builds the tool registry. Then ask the agent something that should trigger your tool:

```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your-key>" \
  -d '{"query": "Flip a coin for me"}'
```
## Note on CLI Functionality

Please note that local tools are not supported when running the agent in the CLI. They will fail to load. MCP tools may still be used, however.
