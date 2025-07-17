"""
Letta client integration for promptyoself plugin.
Provides helper functions that wrap the official letta-client SDK.
"""

import os
import logging
from typing import Dict, Any, List

from letta_client import Letta

logger = logging.getLogger(__name__)

_letta_client: Letta | None = None


def _get_letta_client() -> Letta:
    """Return a singleton instance of the Letta SDK client."""
    global _letta_client

    if _letta_client is None:
        token = os.getenv("LETTA_API_KEY")
        base_url = os.getenv("LETTA_BASE_URL")

        if not token:
            raise RuntimeError("LETTA_API_KEY environment variable not set")

        logger.debug("Initialising Letta client (base_url=%s)", base_url or "cloud default")
        _letta_client = Letta(token=token, base_url=base_url)

    return _letta_client


def send_prompt_to_agent(agent_id: str, prompt_text: str) -> bool:
    """
    Send a prompt message to a Letta agent.

    Args:
        agent_id: The Letta agent ID.
        prompt_text: Text content of the prompt.

    Returns:
        Boolean indicating success or failure.
    """
    try:
        client = _get_letta_client()

        logger.info("Sending prompt to agent %s", agent_id)
        response = client.agents.messages.create(
            agent_id=agent_id,
            messages=[{"role": "user", "content": prompt_text}],
        )
        logger.info("Successfully sent prompt to agent %s", agent_id)
        return True
    except Exception as e:
        logger.error("Failed to send prompt to agent %s: %s", agent_id, str(e))
        return False


def test_letta_connection() -> Dict[str, Any]:
    """
    Test connection to Letta server.
    
    Returns:
        Status dict with connection test results.
    """
    try:
        client = _get_letta_client()
        # Try to list agents as a simple connectivity test
        agents = client.agents.list()
        return {
            "status": "success",
            "message": "Connection to Letta server successful",
            "agent_count": len(agents)
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to connect to Letta server: {str(e)}"
        }


def list_available_agents() -> Dict[str, Any]:
    """
    List all available agents from Letta server.
    
    Returns:
        Dict with agent list or error message.
    """
    try:
        client = _get_letta_client()
        agents = client.agents.list()
        
        agent_list = []
        for agent in agents:
            agent_list.append({
                "id": agent.id,
                "name": getattr(agent, 'name', 'Unknown'),
                "created_at": getattr(agent, 'created_at', None),
                "last_updated": getattr(agent, 'last_updated', None)
            })
        
        return {
            "status": "success",
            "agents": agent_list,
            "count": len(agent_list)
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to list agents: {str(e)}"
        }


def validate_agent_exists(agent_id: str) -> Dict[str, Any]:
    """
    Validate that an agent exists on the Letta server.
    
    Args:
        agent_id: The agent ID to validate.
        
    Returns:
        Dict with validation results.
    """
    try:
        client = _get_letta_client()
        agent = client.agents.get(agent_id)
        
        if agent:
            return {
                "status": "success",
                "exists": True,
                "agent_id": agent_id,
                "agent_name": getattr(agent, 'name', 'Unknown')
            }
        else:
            return {
                "status": "error",
                "exists": False,
                "message": f"Agent {agent_id} not found"
            }
    except Exception as e:
        return {
            "status": "error",
            "exists": False,
            "message": f"Failed to validate agent {agent_id}: {str(e)}"
        }


if __name__ == "__main__":
    # Manual smoke test
    import json
    import sys

    test_agent_id = os.getenv("TEST_AGENT_ID")
    if not test_agent_id:
        sys.exit("Set TEST_AGENT_ID env var to run this test")

    # Test connection
    print("Testing connection...")
    conn_result = test_letta_connection()
    print(json.dumps(conn_result, indent=2))
    
    # Test sending prompt
    print("\nTesting prompt sending...")
    success = send_prompt_to_agent(test_agent_id, "Hello from promptyoself!")
    print(f"Prompt sent successfully: {success}")
    
    # Test listing agents
    print("\nTesting agent listing...")
    agents_result = list_available_agents()
    print(json.dumps(agents_result, indent=2))