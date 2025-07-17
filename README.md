# Promptyoself-Command-Line-Edition

> **Self‑hosted prompt scheduler for Letta agents, delivered as a Sanctum MCP CLI plugin**

---

## ✨ Features

| Capability                      | Description                                                                                                                                                                       |
| ------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **CLI‑first design**            | `promptyoself` ships as an [argparse](https://docs.python.org/3/library/argparse.html)‑based CLI. Sanctum MCP auto‑discovers it and exposes each sub‑command as a tool to agents. |
| **One‑off & recurring prompts** | Schedule prompts at a specific ISO datetime or by cron expression (`"0 9 * * *"` → daily 09:00).                                                                                  |
| **SQLite persistence**          | All schedules are stored in a lightweight SQLite DB (volume‑mounted for durability).                                                                                              |
| **Internal scheduler loop**     | A companion process wakes every 60 s and delivers due prompts via the Letta Python SDK. No external cron daemon required.                                                         |
| **Docker Compose ready**        | One command spins up Sanctum MCP, the plugin, the scheduler, and (optionally) a local Letta server.                                                                               |
| **Pythonic & tested**           | Typed codebase, `pytest` + `coverage`, `pre‑commit` hooks (Black, Flake8, isort, mypy).                                                                                           |

---

## 🏗 Architecture Overview

```
┌────────────────────┐  CLI cmds  ┌──────────────────────────┐
│  Sanctum MCP       │──────────▶│  promptyoself CLI        │
│  (stdio server)    │           │  (argparse sub‑commands) │
└────────────────────┘           └──────────┬───────────────┘
                                           │DB (SQLite)
                                           ▼
                                 ┌────────────────────┐
                                 │ Scheduler Loop     │
                                 │ (exec every 60 s)  │
                                 └──────────┬─────────┘
                                            │HTTP (Letta SDK)
                                            ▼
                                     ┌──────────────┐
                                     │ Letta Server │
                                     └──────────────┘
```

---

## 🧰 Tech Stack

| Layer         | Choice                          | Why                                                     |
| ------------- | ------------------------------- | ------------------------------------------------------- |
| Language      | **Python 3.11**                 | Native SDK for Letta; Sanctum plugins are Python CLIs   |
| CLI framework | **argparse**                    | Guaranteed compatibility with Sanctum's `--help` parser |
| Persistence   | **SQLite + SQLAlchemy**         | Zero‑config DB; ORM for maintainability                 |
| Scheduler     | **Internal loop (APScheduler)** | Cron parsing & interval triggers without external deps  |
| Containers    | **Docker Compose**              | Simple local orchestration; one‑command spin‑up         |
| CI            | **GitHub Actions**              | Lint, test, build image, push to registry               |

---

## 🚀 Quick Start

```bash
# 1. Clone repo
$ git clone https://github.com/your-org/promptyoself && cd promptyoself

# 2. Copy environment template & edit
$ cp .env.example .env       # set LETTA_API_KEY / LETTA_BASE_URL etc.

# 3. Launch stack (MCP + scheduler)
$ docker compose up -d       # first build takes ~1‑2 min

# 4. Verify plugin discovery
$ docker compose exec mcp python smcp/mcp_cli.py tools list | grep promptyoself
```

You should see `promptyoself.register`, `promptyoself.list`, `promptyoself.cancel`, and `promptyoself.execute` in the tool list.

---

## ⚙️ Configuration

| Variable                | Default                 | Purpose                                                         |
| ----------------------- | ----------------------- | --------------------------------------------------------------- |
| `LETTA_API_KEY`         | *empty*                 | API key for Letta Cloud or self‑hosted server (if auth enabled) |
| `LETTA_BASE_URL`        | `http://localhost:8283` | Base URL of Letta server (omit for cloud)                       |
| `PROMPTYOSELF_DB_PATH`  | `/data/promptyoself.db` | SQLite file path (mounted volume)                               |
| `PROMPTYOSELF_INTERVAL` | `60`                    | Seconds between scheduler executions                            |

All variables are loaded on startup; edit `.env` or override in Compose.

---

## 🎛 CLI Usage

```bash
# Register a one‑off prompt
promptyoself register \
  --agent-id AGENT_123 \
  --prompt "Remember to review sprint goals" \
  --time "2025-07-20T10:00:00"

# Register a daily prompt at 09:00
promptyoself register \
  --agent-id AGENT_123 \
  --prompt "Daily stand‑up" \
  --cron "0 9 * * *"

# List active schedules
promptyoself list

# Cancel a schedule
promptyoself cancel --id 7
```

Every command prints **JSON** to stdout and exits 0 on success.

---

## 🕰 Scheduling Details

* **Cron expressions** use standard 5‑field syntax (`min hour dom month dow`).
* The internal scheduler wakes every `PROMPTYOSELF_INTERVAL` seconds and executes due prompts.
* Recurring prompts update `next_run` after each delivery; one‑off prompts are deactivated.
* Typical worst‑case delay ≤ `PROMPTYOSELF_INTERVAL` seconds.

---

## 🧑‍💻 Development

```bash
# Create virtualenv & install deps
$ python -m venv .venv && source .venv/bin/activate
$ pip install -r requirements.dev.txt

# Run tests + coverage
$ pytest -q --cov=smcp/plugins/promptyoself

# Lint & format
$ pre-commit run --all-files
```

### Project Scripts

| Script                 | Action                            |
| ---------------------- | --------------------------------- |
| `scripts/create_db.py` | Initialise SQLite schema locally  |
| `scripts/seed_demo.py` | Seed sample schedules for testing |

---

## 🐳 Docker & Compose

The repo ships with:

```text
Dockerfile            # builds promptyoself image
compose.yaml          # MCP + scheduler services
.env.example          # copy → .env and customise
```

```bash
# Build & run
$ docker compose up --build

# Tail scheduler logs
$ docker compose logs -f promptyoself_scheduler
```

---

## ✅ Testing Matrix

| Test Layer             | Tooling                                    |
| ---------------------- | ------------------------------------------ |
| Unit                   | `pytest`, `pytest-mock`                    |
| CLI                    | `pytest` + `capfd`, golden JSON outputs    |
| DB                     | SQLite in‑memory fixtures                  |
| Integration (optional) | Local Letta server in CI service container |

---

## 🤝 Contributing

1. Fork repo ➜ feature branch ➜ PR.
2. Ensure `pre-commit` passes locally.
3. Write tests for new features.
4. Follow conventional commits for commit messages.

---

## 📜 License

Distributed under the **MIT License**. See `LICENSE` for details.

---

Made with ❤️ for the Letta & Sanctum ecosystem.
