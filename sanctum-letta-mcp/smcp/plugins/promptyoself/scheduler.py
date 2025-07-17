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
                # Increment repetition count
                new_repetition_count = schedule.repetition_count + 1
                update_data["repetition_count"] = new_repetition_count
                
                # Check if we've reached the maximum repetitions
                if schedule.max_repetitions is not None and new_repetition_count >= schedule.max_repetitions:
                    # Finite repetition limit reached, deactivate the schedule
                    update_data["active"] = False
                    next_run = None
                    logger.info(f"Schedule {schedule.id} completed {schedule.max_repetitions} repetitions, deactivating")
                else:
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
                    "next_run": next_run.isoformat() if next_run else None,
                    "repetition_count": new_repetition_count,
                    "max_repetitions": schedule.max_repetitions,
                    "completed": schedule.max_repetitions is not None and new_repetition_count >= schedule.max_repetitions
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