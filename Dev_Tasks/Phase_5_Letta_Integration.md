# Phase 5: Letta Integration

## Overview
Complete the Letta client integration to actually send prompts to agents on the self-hosted Letta ADE server.

## Prerequisites
- Phase 4 completed
- Letta client dependency installed from Phase 1
- Self-hosted Letta server accessible at https://cyansociety.a.pinggy.link/

## Tasks

### 5.1 Complete Letta Client Module
**File**: `smcp/plugins/promptyoself/letta_client.py`

```python
"""
Letta client integration for promptyoself plugin.
Handles sending prompts to Letta agents via API.
"""

import os
import logging
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Global client instance
_letta_client = None

def get_letta_client():
    """Get configured Letta client."""
    global _letta_client
    
    if _letta_client is None:
        try:
            from letta_client import Letta
            
            base_url = os.getenv("LETTA_BASE_URL")
            api_key = os.getenv("LETTA_API_KEY")
            
            if not base_url:
                raise ValueError("LETTA_BASE_URL environment variable not set")
            
            logger.info(f"Connecting to Letta server at {base_url}")
            
            # Create client with authentication
            _letta_client = Letta(
                token=api_key,
                base_url=base_url
            )
            
            logger.info("Successfully connected to Letta server")
            
        except Exception as e:
            logger.error(f"Failed to create Letta client: {e}")
            raise
    
    return _letta_client

def send_prompt_to_agent(agent_id: str, prompt_text: str) -> bool:
    """
    Send a prompt to a Letta agent.
    
    Args:
        agent_id: The Letta agent ID
        prompt_text: The prompt content to send
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        client = get_letta_client()
        
        logger.info(f"Sending prompt to agent {agent_id}")
        logger.debug(f"Prompt content: {prompt_text}")
        
        # Send message to agent
        response = client.agents.messages.create(
            agent_id=agent_id,
            messages=[{"role": "user", "content": prompt_text}]
        )
        
        if response:
            logger.info(f"Successfully sent prompt to agent {agent_id}")
            logger.debug(f"Agent response: {response}")
            return True
        else:
            logger.warning(f"Empty response from agent {agent_id}")
            return False
            
    except Exception as e:
        logger.error(f"Failed to send prompt to agent {agent_id}: {e}")
        return False

def test_letta_connection() -> Dict[str, Any]:
    """Test connection to Letta server and return status info."""
    try:
        client = get_letta_client()
        
        # Try to list agents to test connection
        agents = client.agents.all()
        
        return {
            "success": True,
            "agent_count": len(agents),
            "agents": [{"id": agent.id, "name": agent.name} for agent in agents[:5]],  # First 5 only
            "server_url": os.getenv("LETTA_BASE_URL")
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "server_url": os.getenv("LETTA_BASE_URL")
        }

def list_available_agents() -> List[Dict[str, Any]]:
    """List all available agents."""
    try:
        client = get_letta_client()
        agents = client.agents.all()
        
        return [
            {
                "id": agent.id,
                "name": agent.name,
                "created_at": agent.created_at.isoformat() if hasattr(agent, 'created_at') else None,
                "last_updated": agent.last_updated_at.isoformat() if hasattr(agent, 'last_updated_at') else None
            }
            for agent in agents
        ]
        
    except Exception as e:
        logger.error(f"Failed to list agents: {e}")
        return []

def validate_agent_exists(agent_id: str) -> bool:
    """Check if an agent exists."""
    try:
        client = get_letta_client()
        agent = client.agents.retrieve(agent_id)
        return agent is not None
        
    except Exception as e:
        logger.debug(f"Agent {agent_id} validation failed: {e}")
        return False
```

### 5.2 Add Connection Testing Command
**File**: Update `smcp/plugins/promptyoself/cli.py` with new commands:

Add new test and agents commands to the CLI:

```python
def test_connection(args: Dict[str, Any]) -> Dict[str, Any]:
    """Test connection to Letta server."""
    from .letta_client import test_letta_connection
    
    try:
        result = test_letta_connection()
        if result["success"]:
            return {
                "status": "success",
                "connection": result,
                "message": f"Connected to {result['server_url']}, found {result['agent_count']} agents"
            }
        else:
            return {
                "error": f"Connection failed: {result['error']}"
            }
    except Exception as e:
        return {"error": f"Test failed: {str(e)}"}

def list_agents(args: Dict[str, Any]) -> Dict[str, Any]:
    """List available Letta agents."""
    from .letta_client import list_available_agents
    
    try:
        agents = list_available_agents()
        return {
            "status": "success",
            "agents": agents,
            "count": len(agents)
        }
    except Exception as e:
        return {"error": f"Failed to list agents: {str(e)}"}
```

Update the main() function to add the new commands:

```python
def main():
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
  agents      List available Letta agents

Examples:
  python cli.py test
  python cli.py agents
  python cli.py register --agent-id agent-123 --prompt "Check status" --time "2024-01-01 14:30:00"
  python cli.py register --agent-id agent-123 --prompt "Daily report" --cron "0 9 * * *"
  python cli.py register --agent-id agent-123 --prompt "Every 5 minutes" --every "5m"
  python cli.py list --agent-id agent-123
  python cli.py cancel --id 5
  python cli.py execute
  python cli.py execute --loop --interval 30
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", required=True, help="Available commands")
    
    # Test command
    test_parser = subparsers.add_parser("test", help="Test connection to Letta server")
    
    # Agents command
    agents_parser = subparsers.add_parser("agents", help="List available Letta agents")
    
    # ... existing commands remain the same ...
    
    # Add to dispatch logic
    if command == "test":
        result = test_connection(args_dict)
    elif command == "agents":
        result = list_agents(args_dict)
    # ... existing elif statements ...
```

### 5.3 Add Agent Validation to Register Command
**File**: Update `smcp/plugins/promptyoself/cli.py` register_prompt function:

```python
def register_prompt(args: Dict[str, Any]) -> Dict[str, Any]:
    """Register a new scheduled prompt."""
    agent_id = args.get("agent-id")
    prompt = args.get("prompt")
    time_str = args.get("time")
    cron_expr = args.get("cron")
    every_str = args.get("every")
    skip_validation = args.get("skip-validation", False)
    
    if not agent_id or not prompt:
        return {"error": "Missing required arguments: agent-id and prompt"}
    
    # Validate agent exists (unless skipped)
    if not skip_validation:
        from .letta_client import validate_agent_exists
        if not validate_agent_exists(agent_id):
            return {"error": f"Agent {agent_id} not found. Use --skip-validation to bypass this check."}
    
    # ... rest of the function remains the same ...
```

Update the register parser:

```python
register_parser.add_argument("--skip-validation", action="store_true", help="Skip agent validation")
```

### 5.4 Improve Error Handling in Scheduler
**File**: Update `smcp/plugins/promptyoself/scheduler.py`:

```python
def execute_due_prompts() -> List[Dict[str, Any]]:
    """Execute all due prompts and update their schedules."""
    from .letta_client import send_prompt_to_agent, validate_agent_exists
    
    due_schedules = get_due_schedules()
    executed = []
    
    logger.info(f"Found {len(due_schedules)} due schedules")
    
    for schedule in due_schedules:
        try:
            logger.info(f"Executing schedule {schedule.id} for agent {schedule.agent_id}")
            
            # Validate agent exists before attempting to send
            if not validate_agent_exists(schedule.agent_id):
                logger.warning(f"Agent {schedule.agent_id} not found, skipping schedule {schedule.id}")
                executed.append({
                    "id": schedule.id,
                    "agent_id": schedule.agent_id,
                    "delivered": False,
                    "error": "Agent not found",
                    "next_run": schedule.next_run.isoformat()
                })
                continue
            
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
```

### 5.5 Test Letta Integration
Create comprehensive test script:

**File**: `sanctum-letta-mcp/test_letta_integration.py` (temporary)

```python
#!/usr/bin/env python3
"""Test script for Letta integration."""

import subprocess
import json
import sys

def run_cli_command(cmd):
    """Run CLI command and return parsed JSON result."""
    try:
        result = subprocess.run(
            ["python", "smcp/plugins/promptyoself/cli.py"] + cmd,
            capture_output=True,
            text=True,
            cwd="."
        )
        
        if result.stdout:
            return json.loads(result.stdout)
        else:
            return {"error": result.stderr}
            
    except Exception as e:
        return {"error": str(e)}

def main():
    print("Testing Letta Integration...")
    print("=" * 50)
    
    # Test connection
    print("1. Testing connection...")
    result = run_cli_command(["test"])
    if result.get("status") == "success":
        print("✅ Connection successful")
        print(f"   Server: {result['connection']['server_url']}")
        print(f"   Agents found: {result['connection']['agent_count']}")
    else:
        print("❌ Connection failed")
        print(f"   Error: {result.get('error')}")
        return
    
    # List agents
    print("\n2. Listing agents...")
    result = run_cli_command(["agents"])
    if result.get("status") == "success":
        print(f"✅ Found {result['count']} agents")
        for agent in result['agents'][:3]:  # Show first 3
            print(f"   - {agent['id']}: {agent['name']}")
        
        if result['agents']:
            test_agent_id = result['agents'][0]['id']
            print(f"\n3. Testing with agent: {test_agent_id}")
            
            # Register a test prompt
            print("   Registering test prompt...")
            register_result = run_cli_command([
                "register",
                "--agent-id", test_agent_id,
                "--prompt", "This is a test prompt from promptyoself",
                "--every", "2m"
            ])
            
            if register_result.get("status") == "success":
                schedule_id = register_result["id"]
                print(f"   ✅ Registered schedule {schedule_id}")
                
                # Execute immediately
                print("   Executing prompt...")
                execute_result = run_cli_command(["execute"])
                if execute_result.get("status") == "success":
                    if execute_result["executed"]:
                        print("   ✅ Prompt executed successfully")
                        for exec_info in execute_result["executed"]:
                            if exec_info["delivered"]:
                                print(f"      Delivered to {exec_info['agent_id']}")
                            else:
                                print(f"      Failed: {exec_info.get('error')}")
                    else:
                        print("   ℹ️  No prompts were due")
                
                # Clean up - cancel the test schedule
                print("   Cleaning up...")
                cancel_result = run_cli_command(["cancel", "--id", str(schedule_id)])
                if cancel_result.get("status") == "success":
                    print("   ✅ Test schedule cancelled")
            else:
                print(f"   ❌ Failed to register: {register_result.get('error')}")
    else:
        print("❌ Failed to list agents")
        print(f"   Error: {result.get('error')}")

if __name__ == "__main__":
    main()
```

Run the test:

```bash
cd sanctum-letta-mcp
python test_letta_integration.py
```

### 5.6 Git Commit
```bash
git add .
git commit -m "Phase 5: Complete Letta integration

- Implement full Letta client with self-hosted server support
- Add connection testing and agent listing commands
- Implement agent validation in registration
- Add comprehensive error handling for agent operations
- Create integration test script for validation
- Support actual prompt delivery to Letta agents

🤖 Generated with Claude Code"
git push origin main
```

## Success Criteria
- [ ] Letta client successfully connects to self-hosted server
- [ ] Prompts can be sent to real agents
- [ ] Agent validation working properly
- [ ] Connection testing command functional
- [ ] Error handling for network/agent issues
- [ ] Integration test script passes
- [ ] Changes committed and pushed to GitHub

## Next Phase
Proceed to Phase 6: Testing Integration