# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Core Purpose

This is the Promptyoself-Command-Line-Edition project - a self-hosted prompt scheduler for Letta agents delivered as a Sanctum MCP CLI plugin. The system allows Letta agents to schedule one-off and recurring prompts via a CLI interface that's auto-discovered by Sanctum MCP.

## Server Details

- Url for self-hosted remote letta server is https://cyansociety.a.pinggy.link/
- Letta password for self-hosted Letta ADE server is TWIJftq/ufbbxo8w51m/BQ1wBNrZb/JT

## Essential Commands

### Testing
```bash
# Run all tests with coverage
python run_tests.py

# Run specific test types
python run_tests.py --type unit
python run_tests.py --type integration 
python run_tests.py --type e2e
python run_tests.py --type coverage  # generates HTML and XML reports

# Run tests with verbose output
python run_tests.py --verbose

# Run without coverage
python run_tests.py --no-cov
```

### Development Server
```bash
# Start the MCP server (main entry point)
cd sanctum-letta-mcp
source venv/bin/activate
python smcp/mcp_server.py

# Or use the startup script
./start.sh

# Custom configurations
python smcp/mcp_server.py --port 9000
python smcp/mcp_server.py --allow-external
python smcp/mcp_server.py --host 127.0.0.1
```

### Plugin Testing
```bash
# Test individual plugins directly
cd sanctum-letta-mcp/smcp/plugins/botfather
python cli.py --help
python cli.py send-message --message "/newbot"

cd sanctum-letta-mcp/smcp/plugins/devops
python cli.py --help
python cli.py deploy --app-name "myapp" --environment "staging"
```

## Architecture Overview

### High-Level Structure
```
┌────────────────────┐  CLI cmds  ┌──────────────────────────┐
│  Sanctum MCP       │──────────▶│  promptyoself CLI        │
│  (stdio server)    │           │  (argparse sub‑commands) │
└────────────────────┘           └──────────┬───────────────┘
                                           │DB (SQLite)
                                           ▼
                                 ┌────────────────────┐
                                 │ Scheduler Loop     │
                                 │ (exec every 60 s)  │
                                 └──────────┬─────────┘
                                            │HTTP (Letta SDK)
                                            ▼
                                     ┌──────────────┐
                                     │ Letta Server │
                                     └──────────────┘
```

### Key Components

**MCP Server** (`smcp/mcp_server.py:251-364`)
- FastMCP-based server with SSE transport
- Auto-discovers plugins in `smcp/plugins/` directory
- Registers plugin CLI commands as MCP tools
- Health check endpoint and plugin registry

**Plugin System** (`smcp/plugins/`)
- Each plugin is a directory with `cli.py`
- Uses argparse with subcommands for tool discovery
- JSON output for MCP tool integration
- Current plugins: `botfather` (Telegram automation), `devops` (deployment operations)

**Plugin Auto-Discovery** (`smcp/mcp_server.py:36-81`)
- Scans plugins directory for `cli.py` files
- Extracts commands by parsing `--help` output
- Dynamically creates MCP tools with proper schemas

**Tool Execution** (`smcp/mcp_server.py:83-135`)
- Subprocess execution of plugin commands
- Argument marshaling (boolean flags, key-value pairs)
- Async execution with proper error handling

## Development Patterns

### Plugin Development
- Plugins must use argparse with subcommands
- Include help text with "Available commands:" section
- Return JSON with `{"result": "..."}` or `{"error": "..."}`
- Place in `smcp/plugins/{plugin_name}/cli.py`

### Testing Structure
- Unit tests: `tests/unit/` - test individual components
- Integration tests: `tests/integration/` - test MCP protocol compliance  
- E2E tests: `tests/e2e/` - test full workflow scenarios
- Coverage requirement: 100% (enforced by pytest.ini)

### Server Configuration
- Default binding: `0.0.0.0:8000` (localhost + Docker containers)
- Environment variables: `MCP_PORT`, `MCP_PLUGINS_DIR`
- Security modes: localhost-only (`--host 127.0.0.1`) vs external (`--allow-external`)

## Important File Locations

- Main server: `sanctum-letta-mcp/smcp/mcp_server.py`
- Test runner: `sanctum-letta-mcp/run_tests.py`
- Plugin directory: `sanctum-letta-mcp/smcp/plugins/`
- Test configuration: `sanctum-letta-mcp/pytest.ini`
- Dependencies: `sanctum-letta-mcp/requirements.txt`

## Key Implementation Details

- Plugins communicate via CLI interface, not Python imports
- MCP tool names use format: `{plugin_name}.{command}`
- Tool schemas are hardcoded in `create_tool_from_plugin()` for known commands
- Server uses FastMCP with SSE transport for real-time communication
- All plugin executions are async subprocess calls with timeout handling

## Development Workflow

### Implementation Planning
- Detailed implementation phases are stored in `Dev_Tasks/` directory
- Each phase has its own markdown file with comprehensive task breakdown
- Use `LOCAL_IMPLEMENTATION_PROGRESS.md` to track overall progress
- Follow phases sequentially: Environment Setup → Plugin Structure → CLI Commands → Scheduler → Letta Integration → Testing → Deployment

### Git Workflow
- Make periodic commits after completing each major task
- Stage changes with `git add .`
- Use descriptive commit messages ending with `🤖 Generated with Claude Code`
- Push to remote main branch: `git push origin main`
- Commit after each phase completion for proper version control

### Promptyoself Plugin Commands
```bash
# Test Letta connection
cd sanctum-letta-mcp
python smcp/plugins/promptyoself/cli.py test

# List available agents
python smcp/plugins/promptyoself/cli.py agents

# Register prompts
python smcp/plugins/promptyoself/cli.py register --agent-id "agent-123" --prompt "Daily check" --cron "0 9 * * *"
python smcp/plugins/promptyoself/cli.py register --agent-id "agent-456" --prompt "Every 5 minutes" --every "5m"

# List scheduled prompts
python smcp/plugins/promptyoself/cli.py list
python smcp/plugins/promptyoself/cli.py list --agent-id "agent-123"

# Execute due prompts
python smcp/plugins/promptyoself/cli.py execute

# Start scheduler daemon
./start_promptyoself.sh start
./start_promptyoself.sh status
./start_promptyoself.sh stop
```

### Promptyoself Operations
```bash
# Start scheduler daemon
./start_promptyoself.sh start

# Monitor health
python monitor_promptyoself.py

# Database backup
./maintenance/backup_database.sh

# Log cleanup
./maintenance/cleanup_logs.sh
```