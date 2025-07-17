# Implementation Plan for promptyoself System

---

## Phase 1: Project Setup and Tech Stack Selection

* **Programming Language & Version:**
  Use Python 3.12+ for compatibility and latest features.
  Required because Sanctum MCP plugins are CLI-based Python scripts and Letta provides a Python SDK.

* **Repository Structure:**
  Organize as a Sanctum MCP plugin:
  `smcp/plugins/promptyoself/` directory in Sanctum MCP codebase (or separate repo if standalone).
  Contains plugin code including entrypoint `cli.py` for plugin discovery.

* **Key Dependencies:**

  * **Letta SDK:** Install `letta-client` Python package for interacting with agents via API.
  * **Database:** Use SQLite for schedule persistence. Use either Python’s built-in `sqlite3`, or an ORM like SQLAlchemy (robust) or Peewee (lightweight).
  * **CLI Framework:** Prefer built-in `argparse` to align with Sanctum plugin conventions (Sanctum MCP auto-discovers plugins by running `python plugins/<name>/cli.py --help`). Optionally, Typer or Click can be used if they produce standard `--help` output.
  * **Scheduling Library:**

    * Option 1: Use system `cron` (or Docker cron container) to invoke plugin’s execute command periodically.
    * Option 2: Use Python scheduler like APScheduler to handle recurring jobs in-process, supporting cron expressions and SQLite job store. Recommended for ease of setup in Docker environments.
  * **Utilities:** Use `python-dotenv` to load environment variables from `.env` file. Use standard libs like `os` for environment config.

* **Environment Configuration:**

  * `PROMPTYOSELF_DB_PATH` — SQLite DB file path (default: mounted volume or `./promptyoself.db`)
  * `LETTA_API_KEY` — Letta API token (for Letta Cloud or self-hosted with auth)
  * `LETTA_BASE_URL` — Letta server URL (optional, defaults to cloud/local default; e.g. `http://localhost:8283` for local)
  * Other options like scheduling interval, e.g., `PROMPTYOSELF_INTERVAL` (in seconds, default \~60)

* **Docker Base Image:**
  Use lightweight Python base image (e.g. `python:3.12.8-slim`) and list dependencies in `requirements.txt` for installation.

---

## Phase 2: CLI Structure and Sanctum Plugin Integration

* **CLI Entrypoint (`cli.py`):**
  Located at `smcp/plugins/promptyoself/cli.py`, executable (`chmod +x`).
  Use `argparse` to define subcommands and arguments.

* **Example CLI Structure:**

  ```python
  import argparse, json, sys

  def main():
      parser = argparse.ArgumentParser(description="promptyoself CLI – Schedule and manage prompts")
      subparsers = parser.add_subparsers(dest="command", required=True, help="Subcommands")

      reg_parser = subparsers.add_parser("register", help="Register a new scheduled prompt")
      reg_parser.add_argument("--agent-id", required=True, help="Target agent ID for the prompt")
      reg_parser.add_argument("--prompt", required=True, help="Prompt content (text) to schedule")
      reg_parser.add_argument("--time", help="Specific time for one-time prompt (ISO datetime)")
      reg_parser.add_argument("--cron", help="Cron expression for recurring prompt")

      # Similarly define 'list', 'cancel', 'execute' subcommands...

      args = parser.parse_args()
      # Dispatch to appropriate function based on args.command ...
  ```

* **Subcommands:**

  * `register` — Register a new scheduled prompt with arguments:
    `--agent-id`, `--prompt`, and scheduling options `--time <datetime>` or `--cron "<cron_expr>"`.
    Optionally support `--every <interval>` for common recurrences.
  * `list` — List all scheduled prompts with details (ID, agent, next run, recurrence, summary). Optional filtering by agent or status.
  * `cancel` — Cancel scheduled prompt by `--id <schedule_id>`.
  * `execute` — Trigger due prompts; send them to agents and update schedules.

* **Output Format:**
  All CLI commands must output JSON to stdout. Sanctum MCP then embeds this payload inside the `result` field of a **JSON-RPC 2.0** response when returning the tool call to Letta agents. Examples:

  ```json
  // register success
  {"status": "success", "id": 5, "next_run": "...", "message": "Prompt scheduled."}

  // list
  {"status": "success", "schedules": [ ... ]}

  // cancel success
  {"status": "success", "cancelled_id": 5}

  // execute
  {
    "status": "success",
    "executed": [
      {"id": 5, "agent_id": "agent-123", "delivered": true, "next_run": "..."},
      {"id": 8, "agent_id": "agent-456", "delivered": true, "next_run": "..."}
    ],
    "message": "2 prompts executed"
  }
  ```

* **Error Handling:** Output JSON with `"status": "error"` and a meaningful `"message"` on failure.

* **Internal Modules:**
  To keep `cli.py` minimal, implement logic in modules like:

  * `db.py` — DB interactions
  * `scheduler.py` — Scheduling logic
  * `letta_client.py` (or `utils.py`) — Letta API integration

* **Plugin Discovery:**

  * Add `__init__.py` in plugin directory.
  * Ensure `cli.py` executable and named correctly.
  * Test with `python plugins/promptyoself/cli.py --help` for correct output.

---

## Phase 3: Database Schema and Persistence (SQLite)

* **Database Setup:**
  Use SQLite file (`promptyoself.db`) configurable via `PROMPTYOSELF_DB_PATH`.

* **Schema (Table `schedules`):**

  | Column          | Type        | Description                                         |
  | --------------- | ----------- | --------------------------------------------------- |
  | id              | PRIMARY KEY | Unique schedule ID                                  |
  | agent\_id       | String      | Letta agent ID to receive prompt                    |
  | prompt\_text    | Text        | Content of the prompt                               |
  | schedule\_type  | String      | "once", "cron", or "interval"                       |
  | schedule\_value | String      | Timestamp or cron expression or interval descriptor |
  | next\_run       | DateTime    | Next execution time                                 |
  | created\_at     | DateTime    | Creation timestamp                                  |
  | active          | Boolean     | Active or canceled flag                             |
  | last\_run       | DateTime    | Timestamp of last execution (optional)              |

* **ORM Example (SQLAlchemy):**

  ```python
  class PromptSchedule(Base):
      __tablename__ = "schedules"
      id = Column(Integer, primary_key=True)
      agent_id = Column(String, index=True)
      prompt_text = Column(Text)
      schedule_type = Column(String)  # 'once', 'cron', etc.
      schedule_value = Column(String)  # datetime string or cron pattern
      next_run = Column(DateTime)
      active = Column(Boolean, default=True)
      created_at = Column(DateTime, default=datetime.utcnow)
      last_run = Column(DateTime, nullable=True)
  ```

* **DB Access Layer:** Implement functions such as:

  * `add_schedule()`
  * `list_schedules()`
  * `get_schedule()`
  * `update_schedule()`
  * `delete_schedule()` (optional)

* **Thread-safety:** Use connection per thread with locks on writes if concurrency expected.

---

## Phase 4: Implementing CLI Commands

* **register Command:**

  * Validate `--time` (one-time) as future datetime.
  * Validate `--cron` (recurring) format with libraries like `croniter` or APScheduler's `CronTrigger`.
  * Disallow both or neither of `--time` and `--cron`.
  * Compute `next_run` accordingly.
  * Insert schedule into DB, output success JSON or error JSON.

* **list Command:**

  * Retrieve schedules (active only by default).
  * Output JSON list of schedules with friendly fields.
  * Support optional filtering by agent or status.

* **cancel Command:**

  * Take `--id`, verify existence and active status.
  * Mark inactive (preferred) or delete.
  * Output success JSON or error JSON if not found.

* **execute Command:**

  * Query active schedules with `next_run <= now`.
  * For each due prompt:

    1. Send prompt to agent via Letta SDK.
    2. Update `last_run` and calculate next `next_run` (or deactivate if one-time).
  * Output JSON summarizing executed prompts or no prompts due.
  * Handle errors gracefully, log issues, consider retry logic for future enhancements.
  * Ensure idempotence and concurrency safety.

* **Help Text:** Comprehensive for all commands to support agent usage via `/help`.

---

## Phase 5: Scheduling Mechanism (Cron vs Internal Scheduler)

* **Option A: External Cron Job**

  * Use system cron to run `cli.py execute` periodically (e.g., every minute).
  * In Docker, install cron or use cron container.

* **Option B: In-App Scheduler Loop (Recommended)**

  * Use APScheduler `BackgroundScheduler` with an interval job (e.g., every 60s) that runs `execute_due_prompts`.

  * Example:

    ```python
    from apscheduler.schedulers.background import BackgroundScheduler

    sched = BackgroundScheduler()
    sched.add_job(execute_due_prompts, 'interval', seconds=60)
    sched.start()
    ```

  * Run scheduler in a separate process to avoid conflicts with MCP server thread.

* **Custom Loop Alternative:**

  ```python
  while True:
      execute_due_prompts()
      time.sleep(60)
  ```

* **Deployment Recommendation:**
  Use internal scheduler loop in Docker Compose via CLI flag `--loop`.

* **Docker Compose snippet:**

  ```yaml
  services:
    promptyoself:
      build: .
      command: ["python", "smcp/plugins/promptyoself/cli.py", "execute", "--loop"]
      volumes:
        - ./data/promptyoself.db:/app/smcp/plugins/promptyoself/promptyoself.db
      environment:
        - LETTA_API_KEY=${LETTA_API_KEY}
        - LETTA_BASE_URL=${LETTA_BASE_URL}
        - PROMPTYOSELF_DB_PATH=/app/smcp/plugins/promptyoself/promptyoself.db
  ```

* **Synchronization:** Handle SQLite locks gracefully with retries if needed.

* **Time Accuracy:** \~1 minute precision acceptable, document accordingly.

* **Recurring Calculation:** Helper functions use `croniter` or APScheduler’s `CronTrigger` to compute next run times.

---

## Phase 6: Letta Integration for Prompt Delivery

* **Initialize Letta Client:**

  ```python
  from letta_client import Letta
  import os

  token = os.getenv("LETTA_API_KEY")
  base_url = os.getenv("LETTA_BASE_URL")
  client = Letta(token=token, base_url=base_url)
  ```

* **Send Prompt to Agent:**

  ```python
  response = client.agents.messages.create(
      agent_id=agent_id,
      messages=[{"role": "user", "content": prompt_text}]
  )
  ```

* **Error Handling:**
  Log API failures, mark delivery status in JSON output, handle network or agent-not-found errors gracefully.

* **Compatibility:** Delivered prompts appear as incoming messages to agents, fitting naturally into ADE workflow.

* **Testing:** Run local Letta server, create test agents, schedule prompts, verify delivery.

---

## Phase 7: Docker Compose Deployment (Self-Hosted)

* **Dockerfile:**

  * Use official Python base image.
  * Install dependencies from `requirements.txt` (`letta-client`, ORM, APScheduler, etc.)
  * Optionally install cron if using external cron.
  * Copy plugin code.
  * Configure environment variables via Compose or `.env` file.

* **Multi-Service Compose Example:**

  ```yaml
  version: '3.8'
  services:
    mcp:
      build: .
      command: python smcp/mcp_server.py
      environment:
        - MCP_PLUGINS_DIR=smcp/plugins
        - LETTA_API_KEY=${LETTA_API_KEY}
        - LETTA_BASE_URL=${LETTA_BASE_URL}
        - PROMPTYOSELF_DB_PATH=/data/promptyoself.db
      volumes:
        - promptyodata:/data
      ports:
        - "8000:8000"

    promptyoself_scheduler:
      image: ${DOCKER_IMAGE_NAME}
      command: python smcp/plugins/promptyoself/cli.py execute --loop
      depends_on:
        - mcp
      environment:
        - LETTA_API_KEY=${LETTA_API_KEY}
        - LETTA_BASE_URL=${LETTA_BASE_URL}
        - PROMPTYOSELF_DB_PATH=/data/promptyoself.db
      volumes:
        - promptyodata:/data

  volumes:
    promptyodata:
  ```

* **Ensure Both Services Access Same DB File and Config**

* **Letta Config:**

  * Cloud: Provide API key.
  * Self-hosted: Provide `LETTA_BASE_URL` and auth token if needed.

* **Security:** Avoid logging secrets; redact prompt content if sensitive.

---

## Phase 8: Testing and Quality Assurance

* **Unit Tests:**

  * DB module with in-memory SQLite
  * Scheduling logic tests with cron expressions
  * Mock Letta client for API interaction testing
  * CLI command argument and output tests

* **Integration Tests:**

  * Run with local Letta server, test end-to-end prompt scheduling and delivery.

* **Linting & Formatting:**

  * Use Black, Flake8/Pylint, isort, pre-commit hooks, and optionally mypy for type checking.

* **Continuous Integration (CI):**

  * Run tests, linting, Docker build.
  * Secure handling of secrets.

* **Manual CLI Testing:**

  * Register, list, cancel, execute commands.
  * Test invalid inputs and error messages.

* **Performance:**
  SQLite should handle expected load. Index `next_run` for efficient due queries.

---

## Phase 9: Documentation, Deployment & Monitoring

* **Documentation:**

  * README with installation, usage, env vars, examples.
  * Describe how prompts appear as user messages to agents.
  * Instructions for Docker Compose deployment.
  * Possible contribution to Sanctum plugin docs.

* **Ease of Setup:**

  * User sets Letta credentials in `.env`
  * Run `docker-compose up -d` to start MCP and scheduler.
  * Plugin ready to use in ADE.

* **Monitoring & Logging:**

  * Use Python `logging` module, write logs to file (e.g., `/data/promptyoself.log`).
  * Log prompt scheduling, executions, errors.
  * Use rotation handlers to manage log size.
  * Optionally expose plugin status via command or MCP API.
  * Leverage Docker logs for visibility.

* **Phased Deployment:**

  * Start in staging, test with dummy agent.
  * Roll out to production.

* **Future Enhancements:**

  * Event-based scheduling, webhook triggers
  * Web UI or ADE panel for management
  * Security: restrict agents to schedule prompts only for themselves.
