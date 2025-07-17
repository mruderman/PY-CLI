# Phase 4: Scheduler Implementation

## Overview
Implement the background scheduler using APScheduler and complete the execute_due_prompts functionality with proper cron calculation and scheduling loop.

## Prerequisites
- Phase 3 completed
- APScheduler dependency installed from Phase 1

## Tasks

### 4.1 Complete Scheduler Module
**File**: `smcp/plugins/promptyoself/scheduler.py`

```python
"""
Scheduler logic for promptyoself plugin.
Handles cron calculations, prompt execution, and background scheduling.
"""

import time
import logging
from datetime import datetime, timedelta
from croniter import croniter
from typing import List, Dict, Any
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from .db import get_due_schedules, update_schedule
from .letta_client import send_prompt_to_agent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def calculate_next_run(cron_expr: str, base_time: datetime = None) -> datetime:
    """Calculate next run time from cron expression."""
    if base_time is None:
        base_time = datetime.utcnow()
    
    cron = croniter(cron_expr, base_time)
    return cron.get_next(datetime)

def calculate_next_run_for_schedule(schedule) -> datetime:
    """Calculate next run time for a schedule based on its type."""
    if schedule.schedule_type == "once":
        # One-time schedules don't have a next run
        return None
    elif schedule.schedule_type == "cron":
        return calculate_next_run(schedule.schedule_value)
    elif schedule.schedule_type == "interval":
        # Parse interval (e.g., "60s", "5m", "1h")
        interval_str = schedule.schedule_value
        if interval_str.endswith('s'):
            seconds = int(interval_str[:-1])
        elif interval_str.endswith('m'):
            seconds = int(interval_str[:-1]) * 60
        elif interval_str.endswith('h'):
            seconds = int(interval_str[:-1]) * 3600
        else:
            seconds = int(interval_str)  # Default to seconds
        
        return datetime.utcnow() + timedelta(seconds=seconds)
    else:
        raise ValueError(f"Unknown schedule type: {schedule.schedule_type}")

def execute_due_prompts() -> List[Dict[str, Any]]:
    """Execute all due prompts and update their schedules."""
    due_schedules = get_due_schedules()
    executed = []
    
    logger.info(f"Found {len(due_schedules)} due schedules")
    
    for schedule in due_schedules:
        try:
            logger.info(f"Executing schedule {schedule.id} for agent {schedule.agent_id}")
            
            # Send prompt to agent
            success = send_prompt_to_agent(schedule.agent_id, schedule.prompt_text)
            
            # Update schedule
            update_data = {
                "last_run": datetime.utcnow()
            }
            
            if success:
                # Calculate next run time
                next_run = calculate_next_run_for_schedule(schedule)
                if next_run:
                    update_data["next_run"] = next_run
                else:
                    # One-time schedule, deactivate it
                    update_data["active"] = False
                
                executed.append({
                    "id": schedule.id,
                    "agent_id": schedule.agent_id,
                    "delivered": True,
                    "next_run": next_run.isoformat() if next_run else None
                })
            else:
                # Failed to deliver, keep the same next_run time for retry
                executed.append({
                    "id": schedule.id,
                    "agent_id": schedule.agent_id,
                    "delivered": False,
                    "error": "Failed to deliver prompt",
                    "next_run": schedule.next_run.isoformat()
                })
            
            update_schedule(schedule.id, **update_data)
            
        except Exception as e:
            logger.error(f"Error executing schedule {schedule.id}: {e}")
            executed.append({
                "id": schedule.id,
                "agent_id": schedule.agent_id,
                "delivered": False,
                "error": str(e),
                "next_run": schedule.next_run.isoformat()
            })
    
    return executed

class PromptScheduler:
    """Background scheduler for executing prompts."""
    
    def __init__(self, interval_seconds: int = 60):
        self.interval_seconds = interval_seconds
        self.scheduler = None
        self.running = False
    
    def start(self):
        """Start the background scheduler."""
        if self.running:
            logger.warning("Scheduler is already running")
            return
        
        logger.info(f"Starting prompt scheduler with {self.interval_seconds}s interval")
        
        self.scheduler = BackgroundScheduler()
        self.scheduler.add_job(
            func=self._execute_job,
            trigger=IntervalTrigger(seconds=self.interval_seconds),
            id='execute_prompts',
            name='Execute Due Prompts',
            replace_existing=True
        )
        
        self.scheduler.start()
        self.running = True
        logger.info("Prompt scheduler started")
    
    def stop(self):
        """Stop the background scheduler."""
        if not self.running:
            return
        
        logger.info("Stopping prompt scheduler")
        if self.scheduler:
            self.scheduler.shutdown()
        self.running = False
        logger.info("Prompt scheduler stopped")
    
    def _execute_job(self):
        """Internal job execution method."""
        try:
            results = execute_due_prompts()
            if results:
                logger.info(f"Executed {len(results)} prompts")
        except Exception as e:
            logger.error(f"Error in scheduled job: {e}")
    
    def run_loop(self):
        """Run the scheduler in a blocking loop."""
        self.start()
        try:
            logger.info("Scheduler running in loop mode. Press Ctrl+C to stop.")
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        finally:
            self.stop()

def run_scheduler_loop(interval_seconds: int = 60):
    """Run the scheduler in a blocking loop."""
    scheduler = PromptScheduler(interval_seconds)
    scheduler.run_loop()
```

### 4.2 Create Letta Client Module (Stub)
**File**: `smcp/plugins/promptyoself/letta_client.py`

```python
"""
Letta client integration for promptyoself plugin.
Handles sending prompts to Letta agents via API.
"""

import os
import logging
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

def get_letta_client():
    """Get configured Letta client. (Stub - will be implemented in Phase 5)"""
    # This will be fully implemented in Phase 5
    pass

def send_prompt_to_agent(agent_id: str, prompt_text: str) -> bool:
    """
    Send a prompt to a Letta agent.
    
    Args:
        agent_id: The Letta agent ID
        prompt_text: The prompt content to send
    
    Returns:
        bool: True if successful, False otherwise
    """
    # Stub implementation - will be completed in Phase 5
    logger.info(f"[STUB] Would send prompt to agent {agent_id}: {prompt_text[:50]}...")
    return True  # Assume success for now

def test_letta_connection() -> bool:
    """Test connection to Letta server."""
    # Stub implementation - will be completed in Phase 5
    logger.info("[STUB] Testing Letta connection...")
    return True
```

### 4.3 Update CLI Execute Command
**File**: Update `smcp/plugins/promptyoself/cli.py` execute_prompts function:

```python
def execute_prompts(args: Dict[str, Any]) -> Dict[str, Any]:
    """Execute due prompts."""
    loop_mode = args.get("loop", False)
    interval = int(args.get("interval", 60))
    
    try:
        if loop_mode:
            from .scheduler import run_scheduler_loop
            # This will run indefinitely
            run_scheduler_loop(interval)
            return {"status": "success", "message": "Scheduler stopped"}
        else:
            results = execute_due_prompts()
            return {
                "status": "success",
                "executed": results,
                "message": f"{len(results)} prompts executed"
            }
            
    except Exception as e:
        return {"error": f"Failed to execute prompts: {str(e)}"}
```

Also update the execute parser in main():

```python
# Execute command
execute_parser = subparsers.add_parser("execute", help="Execute due prompts")
execute_parser.add_argument("--loop", action="store_true", help="Run continuously")
execute_parser.add_argument("--interval", type=int, default=60, help="Loop interval in seconds")
```

### 4.4 Add Support for Interval Schedules
**File**: Update `smcp/plugins/promptyoself/cli.py` register_prompt function:

Add support for `--every` parameter:

```python
def register_prompt(args: Dict[str, Any]) -> Dict[str, Any]:
    """Register a new scheduled prompt."""
    agent_id = args.get("agent-id")
    prompt = args.get("prompt")
    time_str = args.get("time")
    cron_expr = args.get("cron")
    every_str = args.get("every")
    
    if not agent_id or not prompt:
        return {"error": "Missing required arguments: agent-id and prompt"}
    
    schedule_options = [time_str, cron_expr, every_str]
    if sum(bool(x) for x in schedule_options) != 1:
        return {"error": "Must specify exactly one of --time, --cron, or --every"}
    
    try:
        if time_str:
            # One-time schedule
            next_run = date_parser.parse(time_str)
            if next_run <= datetime.utcnow():
                return {"error": "Scheduled time must be in the future"}
            
            schedule_type = "once"
            schedule_value = time_str
            
        elif cron_expr:
            # Recurring schedule with cron
            if not croniter.is_valid(cron_expr):
                return {"error": f"Invalid cron expression: {cron_expr}"}
            
            schedule_type = "cron"
            schedule_value = cron_expr
            next_run = calculate_next_run(cron_expr)
            
        else:
            # Interval schedule
            if not every_str.endswith(('s', 'm', 'h')):
                return {"error": "Interval must end with 's' (seconds), 'm' (minutes), or 'h' (hours)"}
            
            schedule_type = "interval"
            schedule_value = every_str
            
            # Calculate first run time (immediate + interval)
            if every_str.endswith('s'):
                seconds = int(every_str[:-1])
            elif every_str.endswith('m'):
                seconds = int(every_str[:-1]) * 60
            elif every_str.endswith('h'):
                seconds = int(every_str[:-1]) * 3600
            
            next_run = datetime.utcnow() + timedelta(seconds=seconds)
        
        schedule_id = add_schedule(
            agent_id=agent_id,
            prompt_text=prompt,
            schedule_type=schedule_type,
            schedule_value=schedule_value,
            next_run=next_run
        )
        
        return {
            "status": "success",
            "id": schedule_id,
            "next_run": next_run.isoformat(),
            "message": f"Prompt scheduled with ID {schedule_id}"
        }
        
    except Exception as e:
        return {"error": f"Failed to register prompt: {str(e)}"}
```

Update the register parser:

```python
register_parser.add_argument("--every", help="Interval for recurring execution (e.g., '30s', '5m', '1h')")
```

### 4.5 Test Scheduler Functionality
Create test script:

```bash
# Test interval scheduling
python cli.py register --agent-id test-agent --prompt "Every minute test" --every "1m"

# Test loop mode (run in background terminal)
python cli.py execute --loop --interval 30

# Test single execution
python cli.py execute
```

### 4.6 Git Commit
```bash
git add .
git commit -m "Phase 4: Implement scheduler with APScheduler

- Complete scheduler module with background execution
- Add support for cron, interval, and one-time schedules
- Implement loop mode for continuous execution
- Add proper logging and error handling
- Create stub for Letta client integration (Phase 5)

🤖 Generated with Claude Code"
git push origin main
```

## Success Criteria
- [ ] APScheduler background execution implemented
- [ ] Support for all schedule types (once, cron, interval)
- [ ] Loop mode functionality working
- [ ] Proper error handling and logging
- [ ] Schedule next-run calculations working correctly
- [ ] Changes committed and pushed to GitHub

## Next Phase
Proceed to Phase 5: Letta Integration