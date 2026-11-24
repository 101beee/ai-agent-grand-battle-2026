English | [한국어](ARCHITECTURE.KR.md)

# Agent Architecture

The model selects the next action and its inputs. The harness validates the request, executes the tool, and returns the result to the model. The model then chooses another action or produces a final answer.

## Tool Agent

| File or function | Responsibility |
|---|---|
| `agents/tool_agent/main.py` | Host that manages model calls and MCP connections |
| `make_client()` | Create a local model client from environment variables |
| `connect()` | Initialize MCP servers and collect their tools |
| `schema()` | Convert MCP tool definitions to model function schemas |
| `call_tool()` | Return tool results and errors |
| `ask()` | Repeat model decisions and tool execution |
| `agents/tool_agent/tools.py` | MCP tool implementations |

MCP connections follow `initialize`, `tools/list`, and `tools/call`. Tool names include a server prefix to prevent collisions. Set the model call limit with `MAX_TURNS`.

| Tool | Function |
|---|---|
| `tools__open_webpage` | Open a webpage in the default browser |
| `tools__search_wikipedia` | Search Korean Wikipedia and retrieve a summary |
| `tools__create_excel` | Save a CSV table as an Excel file and open it |
| `fetch__fetch` | Retrieve webpage content |

## Team Agent

The planner proposes a choice, the budget agent calculates its cost, and the reviewer checks the constraints. Results pass between roles through a shared board.

| File or component | Responsibility |
|---|---|
| `agents/team_agent/config.py` | Tool-use and model settings |
| `agents/team_agent/runner.py` | Commands to create models, run agents, and inspect results |
| `agents/team_agent/harness.py` | Roles, tools, model client, and execution loop |
| `agents/team_agent/modelfiles/` | Role-specific model parameters and system prompts |
| `ROLES` | Role objectives and tool permissions |
| `ToolRegistry.execute()` | Validate tool permissions and inputs |
| `run_agent()` | Manage planning, execution, observations, and termination |
| `run_case()` | Run each role and pass results through the shared board |

The included selection example chooses a snack set under group-size, budget, and vegan constraints. Each role maintains its own conversation history and receives previous results through `shared_board`. Teams can replace the roles and tools for their competition strategy.

## Logs

| Tag | Meaning |
|---|---|
| `[MODEL]` | Model call |
| `[PLAN]` | Task plan |
| `[TOOL CALL]` | Requested tool |
| `[TOOL RESULT]` | Tool execution result |
| `[HANDOFF]` | Transfer to the next role |
| `[FINAL]` | Final answer |
| `[VERIFY]` | Constraint validation result |
