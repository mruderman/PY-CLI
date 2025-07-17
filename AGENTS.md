# AGENTS.md – Developer Quick‑Start for Letta Agents

This guide explains how **Letta agents** can interact with the `promptyoself` plugin (exposed via Sanctum MCP) to schedule, list, and cancel their own prompts. Use it in Codex or any IDE for rapid reference during development.

---

## 1 · Prerequisites

| Requirement                | Notes                                                                                             |
| -------------------------- | ------------------------------------------------------------------------------------------------- |
| ➡️ **Agent runs on Letta** | Works with self‑hosted Letta server **or** Letta Cloud.                                           |
| ➡️ **Sanctum MCP server**  | Ensure the MCP that hosts `promptyoself` is registered in ADE ("Add MCP server → STDIO").         |
| ➡️ **Permissions**         | The agent should know its own `agent_id` (available in ADE metadata or via environment variable). |

---

## 2 · Tool Discovery

Once the MCP server is connected:

```text
/help                # List all tools
/help promptyoself    # Detailed help for each sub‑command
```

Output shows available sub‑commands:

```text
promptyoself register   Register a new scheduled prompt
promptyoself list       List scheduled prompts
promptyoself cancel     Cancel a scheduled prompt
```

---

## 3 · Usage Examples

### 3.1 Schedule a One‑Off Prompt

```bash
/run plugin=promptyoself \
     command=register \
     args='{ "agent-id": "<your_agent_id>",
             "prompt": "Reflect on yesterday's decisions.",
             "time": "2025-07-20T09:00:00" }'
```

### 3.2 Schedule a Daily Prompt at 09:00 AM

```bash
/run plugin=promptyoself \
     command=register \
     args='{ "agent-id": "<your_agent_id>",
             "prompt": "Daily stand‑up: what are your goals?",
             "cron": "0 9 * * *" }'
```

### 3.3 List Active Prompts

```bash
/run plugin=promptyoself command=list
```

### 3.4 Cancel by ID

```bash
/run plugin=promptyoself \
     command=cancel \
     args='{ "id": 3 }'
```

---

## 4 · JSON Response Schema

Every invocation returns structured JSON:

```json
{
  "status": "success" | "error",
  "message": "Human‑readable description",
  ...command‑specific fields...
}
```

Check `status` before using returned data.

---

## 5 · Best Practices

1. **Self‑prompt carefully** – avoid prompt storms; stagger schedules.
2. **Use ISO 8601 times** – always include timezone (`Z` or `+00:00`).
3. **Cron precision** – minute‑level granularity; sub‑minute not supported.
4. **Cancel unused prompts** – keep schedule DB lean.
5. **No history needed** – Letta agents are **stateful**; send only new queries in each message.

---

## 6 · Troubleshooting

| Symptom                           | Possible Cause                  | Fix                                        |
| --------------------------------- | ------------------------------- | ------------------------------------------ |
| `status = error` – "Invalid time" | Time string not ISO8601         | Use `YYYY-MM-DDTHH:MM:SS±HH:MM`.           |
| Prompt delivered late             | Scheduler interval default 60 s | Adjust `PROMPTYOSELF_INTERVAL`.            |
| No plugin in `/help`              | MCP not reloaded                | Restart MCP or ensure `cli.py` executable. |

---

## 7 · Further Reading

* **promptyoself README** for deployment & environment variables.
* **Letta Quick‑start** docs for agent creation patterns.
* **Crontab Guru** for cron expression syntax.

Feel free to extend this guide in Codex as the plugin evolves.
