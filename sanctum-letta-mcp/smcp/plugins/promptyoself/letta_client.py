import os
import httpx
from typing import Dict, Any

# --- Letta Agent Communication ---

LETTA_API_KEY = os.environ.get("LETTA_API_KEY")
LETTA_API_BASE_URL = os.environ.get("LETTA_API_BASE_URL", "https://api.letta.ai/v1")

def send_prompt_to_agent(agent_id: str, prompt_text: str) -> Dict[str, Any]:
    """
    Sends a prompt to a specified Letta agent.
    
    Args:
        agent_id: The ID of the target agent.
        prompt_text: The content of the prompt to send.
        
    Returns:
        The JSON response from the Letta API.
        
    Raises:
        Exception: If the API key is not configured or if the request fails.
    """
    if not LETTA_API_KEY:
        raise Exception("LETTA_API_KEY environment variable not set.")
        
    headers = {
        "Authorization": f"Bearer {LETTA_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "prompt": prompt_text
    }
    
    url = f"{LETTA_API_BASE_URL}/agents/{agent_id}/prompt"
    
    with httpx.Client() as client:
        response = client.post(url, headers=headers, json=payload)
        response.raise_for_status()  # Will raise an exception for 4xx/5xx responses
        return response.json()

if __name__ == '__main__':
    # Example usage (for testing purposes)
    agent_id_to_test = os.environ.get("TEST_AGENT_ID", "agent-123")
    prompt_to_test = "This is a test prompt from the Letta client."
    
    print(f"Sending test prompt to agent: {agent_id_to_test}")
    
    try:
        api_response = send_prompt_to_agent(agent_id_to_test, prompt_to_test)
        print("API Response:")
        print(api_response)
    except Exception as e:
        print(f"An error occurred: {e}")