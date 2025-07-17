import os
from datetime import datetime
from typing import List, Dict, Any
from croniter import croniter
import logging

from smcp.plugins.promptyoself.db import get_due_schedules, update_schedule
from smcp.plugins.promptyoself.letta_client import send_prompt_to_agent

logging.basicConfig(level=logging.INFO)

def calculate_next_run(cron_expr: str) -> datetime:
    """Calculate the next run time for a cron expression."""
    base_time = datetime.utcnow()
    cron = croniter(cron_expr, base_time)
    return cron.get_next(datetime)

def execute_due_prompts() -> List[Dict[str, Any]]:
    """
    Execute all prompts that are due.
    
    Returns:
        A list of dictionaries, each containing the result of a prompt execution.
    """
    due_schedules = get_due_schedules()
    results = []
    
    for schedule in due_schedules:
        logging.info(f"Executing schedule {schedule.id} for agent {schedule.agent_id}")
        
        try:
            # Send prompt to Letta agent
            response = send_prompt_to_agent(schedule.agent_id, schedule.prompt_text)
            
            # Update schedule's last_run and next_run
            update_data = {"last_run": datetime.utcnow()}
            
            if schedule.schedule_type == "cron":
                update_data["next_run"] = calculate_next_run(schedule.schedule_value)
            else: # 'once'
                update_data["active"] = False

            update_schedule(schedule.id, **update_data)
            
            results.append({
                "schedule_id": schedule.id,
                "status": "success",
                "response": response
            })
            
        except Exception as e:
            logging.error(f"Failed to execute schedule {schedule.id}: {e}")
            results.append({
                "schedule_id": schedule.id,
                "status": "error",
                "error_message": str(e)
            })
            
    return results

if __name__ == "__main__":
    logging.info("Executing due prompts...")
    execution_results = execute_due_prompts()
    logging.info(f"Execution complete. Results: {execution_results}")