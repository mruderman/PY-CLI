#!/usr/bin/env python3
"""
Promptyoself CLI Plugin

Self-hosted prompt scheduler for Letta agents.
Provides commands to register, list, cancel, and execute scheduled prompts.
"""

import argparse
import json
import sys
import logging
from typing import Dict, Any
from datetime import datetime
from dateutil import parser as date_parser

logging.basicConfig(level=logging.DEBUG, stream=sys.stderr, format='%(asctime)s - %(levelname)s - %(message)s')
from croniter import croniter

from smcp.plugins.promptyoself.db import add_schedule, list_schedules, cancel_schedule
from smcp.plugins.promptyoself.scheduler import calculate_next_run, execute_due_prompts


def register_prompt(args: Dict[str, Any]) -> Dict[str, Any]:
    """Register a new scheduled prompt."""
    agent_id = args.get("agent_id") or args.get("agent-id")
    prompt = args.get("prompt")
    time_str = args.get("time")
    cron_expr = args.get("cron")
    
    if not agent_id or not prompt:
        return {"error": "Missing required arguments: agent-id and prompt"}
    
    if not time_str and not cron_expr:
        return {"error": "Must specify either --time or --cron"}
    
    if time_str and cron_expr:
        return {"error": "Cannot specify both --time and --cron"}
    
    try:
        if time_str:
            # One-time schedule
            next_run = date_parser.parse(time_str)
            if next_run <= datetime.utcnow():
                return {"error": "Scheduled time must be in the future"}
            
            schedule_type = "once"
            schedule_value = time_str
            
        else:
            # Recurring schedule
            if not croniter.is_valid(cron_expr):
                return {"error": f"Invalid cron expression: {cron_expr}"}
            
            schedule_type = "cron"
            schedule_value = cron_expr
            next_run = calculate_next_run(cron_expr)
        
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


def list_prompts(args: Dict[str, Any]) -> Dict[str, Any]:
    """List scheduled prompts."""
    logging.debug(f"list_prompts called with args: {args}")
    agent_id = args.get("agent_id") or args.get("agent-id")
    show_all = args.get("all", False)
    
    try:
        logging.debug(f"Calling list_schedules with agent_id={agent_id}, active_only={not show_all}")
        schedules = list_schedules(
            agent_id=agent_id,
            active_only=not show_all
        )
        logging.debug(f"list_schedules returned {len(schedules)} schedules.")
        
        return {
            "status": "success",
            "schedules": schedules,
            "count": len(schedules)
        }
        
    except Exception as e:
        logging.error("Exception in list_prompts", exc_info=True)
        return {"error": f"Failed to list prompts: {str(e)}"}


def cancel_prompt(args: Dict[str, Any]) -> Dict[str, Any]:
    """Cancel a scheduled prompt."""
    schedule_id = args.get("id")
    
    if not schedule_id:
        return {"error": "Missing required argument: id"}
    
    try:
        schedule_id = int(schedule_id)
        success = cancel_schedule(schedule_id)
        
        if success:
            return {
                "status": "success",
                "cancelled_id": schedule_id,
                "message": f"Schedule {schedule_id} cancelled"
            }
        else:
            return {"error": f"Schedule {schedule_id} not found or already cancelled"}
            
    except ValueError:
        return {"error": "Schedule ID must be a number"}
    except Exception as e:
        return {"error": f"Failed to cancel prompt: {str(e)}"}


def execute_prompts(args: Dict[str, Any]) -> Dict[str, Any]:
    """Execute due prompts."""
    loop_mode = args.get("loop", False)
    
    try:
        if loop_mode:
            # This will be implemented in Phase 4
            return {"error": "Loop mode not yet implemented"}
        else:
            results = execute_due_prompts()
            return {
                "status": "success",
                "executed": results,
                "message": f"{len(results)} prompts executed"
            }
            
    except Exception as e:
        return {"error": f"Failed to execute prompts: {str(e)}"}


def main():
    logging.debug("CLI main() started.")
    parser = argparse.ArgumentParser(
        description="Promptyoself CLI – Schedule and manage prompts for Letta agents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Available commands:
  register    Register a new scheduled prompt
  list        List scheduled prompts
  cancel      Cancel a scheduled prompt
  execute     Execute due prompts

Examples:
  python cli.py register --agent-id agent-123 --prompt "Check status" --time "2024-01-01 14:30:00"
  python cli.py register --agent-id agent-123 --prompt "Daily report" --cron "0 9 * * *"
  python cli.py list --agent-id agent-123
  python cli.py cancel --id 5
  python cli.py execute
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", required=True, help="Available commands")
    
    # Register command
    register_parser = subparsers.add_parser("register", help="Register a new scheduled prompt")
    register_parser.add_argument("--agent-id", required=True, help="Target agent ID")
    register_parser.add_argument("--prompt", required=True, help="Prompt content to schedule")
    register_parser.add_argument("--time", help="One-time execution time (ISO format)")
    register_parser.add_argument("--cron", help="Cron expression for recurring execution")
    
    # List command
    list_parser = subparsers.add_parser("list", help="List scheduled prompts")
    list_parser.add_argument("--agent-id", help="Filter by agent ID")
    list_parser.add_argument("--all", action="store_true", help="Include cancelled schedules")
    
    # Cancel command
    cancel_parser = subparsers.add_parser("cancel", help="Cancel a scheduled prompt")
    cancel_parser.add_argument("--id", required=True, help="Schedule ID to cancel")
    
    # Execute command
    execute_parser = subparsers.add_parser("execute", help="Execute due prompts")
    execute_parser.add_argument("--loop", action="store_true", help="Run continuously")
    
    args = parser.parse_args()
    logging.debug(f"Parsed args: {args}")
    
    # Convert args to dict for easier handling
    args_dict = vars(args)
    command = args_dict.pop("command")
    logging.debug(f"Dispatching command: '{command}'")
    
    # Dispatch to appropriate function
    if command == "register":
        result = register_prompt(args_dict)
    elif command == "list":
        result = list_prompts(args_dict)
    elif command == "cancel":
        result = cancel_prompt(args_dict)
    elif command == "execute":
        result = execute_prompts(args_dict)
    else:
        result = {"error": f"Unknown command: {command}"}
    
    # Output JSON result
    logging.debug(f"Final result: {result}")
    print(json.dumps(result, indent=2))
    
    # Exit with appropriate code
    sys.exit(0 if result.get("status") == "success" or "error" not in result else 1)


if __name__ == "__main__":
    main()