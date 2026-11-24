English | [한국어](SETUP.KR.md)

# Setup and Execution

## Requirements

- Python 3.10 or later
- Ollama 0.12.7 or later
- A local model that supports tool calling
- A desktop environment for opening a browser or Excel files

## Installation

```bash
git clone https://github.com/101beee/ai-agent-grand-battle-2026.git
cd ai-agent-grand-battle-2026
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
ollama pull qwen3-vl:2b-instruct
```

On Windows PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe agents/tool_agent/main.py --tools
```

## Model Configuration

| Environment variable | Default | Purpose |
|---|---|---|
| `LOCAL_LLM_MODEL` | `qwen3-vl:2b-instruct` | Model name |
| `LOCAL_LLM_URL` | `http://127.0.0.1:11434` | Ollama-compatible server URL |
| `LOCAL_LLM_API_KEY` | Empty | Bearer authentication key for the tool agent |

On macOS or Linux with bash, copy `.env.example` and load the configuration:

```bash
cp .env.example .env
# Edit .env, then export its variables.
set -a
source .env
set +a
```

`.env` is not loaded automatically. In PowerShell, set variables with syntax such as `$env:LOCAL_LLM_MODEL = 'qwen3-vl:2b-instruct'`. Do not commit authentication keys.

## Tool Agent

```bash
python agents/tool_agent/main.py --tools
python agents/tool_agent/main.py "Find Seoul National University on Wikipedia and describe it in two sentences."
python agents/tool_agent/main.py "Create and open an Excel project schedule from Monday to Friday."
```

`--tools` lists connected MCP tools without calling the model. When given a question, the model selects tools, checks their results, and returns an answer.

Generated Excel files are saved to `agents/tool_agent/outputs/`. MCP server logs are written to `agents/tool_agent/mcp_servers.log`.

## Team Agent

The planner, budget agent, and reviewer work together on a constrained selection problem.

```bash
python agents/team_agent/runner.py --check
python agents/team_agent/runner.py --step inspect
python agents/team_agent/runner.py --step models
python agents/team_agent/runner.py --step run
python agents/team_agent/runner.py --step cases
python agents/team_agent/runner.py --step report
```

Set `USE_TOOLS` in `config.py` to control tool use. Set `AGENT_BASES` to choose each role's base model. Execution records are saved to `agents/team_agent/runs/`.

Use `--mode replay` to inspect the execution flow without a model. This mode replays fixed responses.

## Server Protocol

Both agents use the Ollama API. For a local server with a different protocol, adapt the model client and message conversion to that server's specification.

## Adding Tools

Add a function decorated with `@mcp.tool()` to `agents/tool_agent/tools.py`. Provide input types and a description, then check registration with `--tools`. To connect another MCP server, add its process configuration to `SERVERS` in `agents/tool_agent/main.py`.

Implement and connect any additional tools your team needs, including email scheduling and sending, image processing, or reading existing Excel files.

## Checks

```bash
python -m unittest discover -s tests -v
python scripts/update_leaderboard.py --check
python scripts/check_repository.py
```
