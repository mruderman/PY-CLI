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
from datetime import datetime, timedelta
from dateutil import parser as date_parser

logging.basicConfig(level=logging.DEBUG, stream=sys.stderr, format='%(asctime)s - %(levelname)s - %(message)s')
from croniter import croniter

from smcp.plugins.promptyoself.db import add_schedule, list_schedules, cancel_schedule
from smcp.plugins.promptyoself.scheduler import calculate_next_run, execute_due_prompts, run_scheduler_loop
from smcp.plugins.promptyoself.letta_client import test_letta_connection, list_available_agents, validate_agent_exists


def register_prompt(args: Dict[str, Any]) -> Dict[str, Any]:
    """Register a new scheduled prompt."""
    agent_id = args.get("agent_id") or args.get("agent-id")
    prompt = args.get("prompt")
    time_str = args.get("time")
    cron_expr = args.get("cron")
    every_str = args.get("every")
    skip_validation = args.get("skip_validation", False)
    max_repetitions = args.get("max_repetitions") or args.get("max-repetitions")
    start_at = args.get("start_at") or args.get("start-at")
    
    if not agent_id or not prompt:
        return {"error": "Missing required arguments: agent-id and prompt"}
    
    # Count how many scheduling options are provided
    schedule_options = sum(bool(x) for x in [time_str, cron_expr, every_str])
    if schedule_options == 0:
        return {"error": "Must specify one of --time, --cron, or --every"}
    if schedule_options > 1:
        return {"error": "Cannot specify multiple scheduling options"}
    
    # Validate agent exists unless skipped
    if not skip_validation:
        validation_result = validate_agent_exists(agent_id)
        if validation_result["status"] == "error":
            return {"error": f"Agent validation failed: {validation_result['message']}"}
    
    try:
        if time_str:
            # One-time schedule
            next_run = date_parser.parse(time_str)
            if next_run <= datetime.utcnow():
                return {"error": "Scheduled time must be in the future"}
            
            schedule_type = "once"
            schedule_value = time_str
            
        elif cron_expr:
            # Recurring schedule
            if not croniter.is_valid(cron_expr):
                return {"error": f"Invalid cron expression: {cron_expr}"}
            
            schedule_type = "cron"
            schedule_value = cron_expr
            next_run = calculate_next_run(cron_expr)
            
        elif every_str:
            # Interval schedule
            schedule_type = "interval"
            schedule_value = every_str
            
            # Parse interval and calculate next run
            try:
                if every_str.endswith('s'):
                    seconds = int(every_str[:-1])
                elif every_str.endswith('m'):
                    seconds = int(every_str[:-1]) * 60
                elif every_str.endswith('h'):
                    seconds = int(every_str[:-1]) * 3600
                else:
                    seconds = int(every_str)  # Default to seconds
                
                # Handle start_at parameter for interval schedules
                if start_at:
                    next_run = date_parser.parse(start_at)
                    if next_run <= datetime.utcnow():
                        return {"error": "Start time must be in the future"}
                else:
                    next_run = datetime.utcnow() + timedelta(seconds=seconds)
            except ValueError:
                return {"error": f"Invalid interval format: {every_str}. Use formats like '30s', '5m', '1h'"}
        
        # Validate max_repetitions if provided
        if max_repetitions is not None:
            try:
                max_repetitions = int(max_repetitions)
                if max_repetitions <= 0:
                    return {"error": "max-repetitions must be a positive integer"}
            except ValueError:
                return {"error": "max-repetitions must be a valid integer"}
        
        schedule_id = add_schedule(
            agent_id=agent_id,
            prompt_text=prompt,
            schedule_type=schedule_type,
            schedule_value=schedule_value,
            next_run=next_run,
            max_repetitions=max_repetitions
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


def test_connection(args: Dict[str, Any]) -> Dict[str, Any]:
    """Test connection to Letta server."""
    try:
        result = test_letta_connection()
        return result
    except Exception as e:
        return {"error": f"Failed to test connection: {str(e)}"}


def list_agents(args: Dict[str, Any]) -> Dict[str, Any]:
    """List available agents from Letta server."""
    try:
        result = list_available_agents()
        return result
    except Exception as e:
        return {"error": f"Failed to list agents: {str(e)}"}


def execute_prompts(args: Dict[str, Any]) -> Dict[str, Any]:
    """Execute due prompts."""
    loop_mode = args.get("loop", False)
    interval = args.get("interval", 60)
    
    try:
        if loop_mode:
            # Run in loop mode using scheduler
            try:
                interval_seconds = int(interval)
            except ValueError:
                return {"error": "Interval must be a number (seconds)"}
            
            run_scheduler_loop(interval_seconds)
            return {
                "status": "success",
                "message": "Scheduler loop completed"
            }
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
  test        Test connection to Letta server
  agents      List available agents

Examples:
  python cli.py register --agent-id agent-123 --prompt "Check status" --time "2024-01-01 14:30:00"
  python cli.py register --agent-id agent-123 --prompt "Daily report" --cron "0 9 * * *"
  python cli.py register --agent-id agent-123 --prompt "Every 5 minutes" --every "5m"
  python cli.py register --agent-id agent-123 --prompt "Focus check" --every "6m" --max-repetitions 10 --start-at "2024-01-01 15:00:00"
  python cli.py list --agent-id agent-123
  python cli.py cancel --id 5
  python cli.py execute
  python cli.py execute --loop --interval 30
  python cli.py test
  python cli.py agents
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", required=True, help="Available commands")
    
    # Register command
    register_parser = subparsers.add_parser("register", help="Register a new scheduled prompt")
    register_parser.add_argument("--agent-id", required=True, help="Target agent ID")
    register_parser.add_argument("--prompt", required=True, help="Prompt content to schedule")
    register_parser.add_argument("--time", help="One-time execution time (ISO format)")
    register_parser.add_argument("--cron", help="Cron expression for recurring execution")
    register_parser.add_argument("--every", help="Interval for recurring execution (e.g., '5m', '1h', '30s')")
    register_parser.add_argument("--max-repetitions", type=int, help="Maximum number of repetitions (for --every schedules)")
    register_parser.add_argument("--start-at", help="Start time for interval schedules (ISO format)")
    register_parser.add_argument("--skip-validation", action="store_true", help="Skip agent validation")
    
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
    execute_parser.add_argument("--interval", type=int, default=60, help="Interval in seconds for loop mode (default: 60)")
    
    # Test command
    test_parser = subparsers.add_parser("test", help="Test connection to Letta server")
    
    # Agents command
    agents_parser = subparsers.add_parser("agents", help="List available agents")
    
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
    elif command == "test":
        result = test_connection(args_dict)
    elif command == "agents":
        result = list_agents(args_dict)
    else:
        result = {"error": f"Unknown command: {command}"}
    
    # Output JSON result
    logging.debug(f"Final result: {result}")
    print(json.dumps(result, indent=2))
    
    # Exit with appropriate code
    sys.exit(0 if result.get("status") == "success" or "error" not in result else 1)


if __name__ == "__main__":
    main()