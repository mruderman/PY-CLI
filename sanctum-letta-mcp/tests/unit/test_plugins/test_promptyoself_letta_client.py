"""
Unit tests for promptyoself letta_client module.
"""

import pytest
import os
from unittest.mock import patch, MagicMock, call

from smcp.plugins.promptyoself.letta_client import (
    _get_letta_client,
    send_prompt_to_agent,
    test_letta_connection,
    list_available_agents,
    validate_agent_exists
)


class TestLettaClientConnection:
    """Test class for Letta client connection functionality."""
    
    def setup_method(self):
        """Reset global client before each test."""
        # Reset the global client
        import smcp.plugins.promptyoself.letta_client
        smcp.plugins.promptyoself.letta_client._letta_client = None
    
    @patch.dict(os.environ, {"LETTA_API_KEY": "test-key", "LETTA_BASE_URL": "https://test.com"})
    @patch('smcp.plugins.promptyoself.letta_client.Letta')
    def test_get_letta_client_with_env_vars(self, mock_letta):
        """Test _get_letta_client with environment variables set."""
        mock_client = MagicMock()
        mock_letta.return_value = mock_client
        
        client = _get_letta_client()
        
        assert client == mock_client
        mock_letta.assert_called_once_with(token="test-key", base_url="https://test.com")
    
    @patch.dict(os.environ, {"LETTA_API_KEY": "test-key"})
    @patch('smcp.plugins.promptyoself.letta_client.Letta')
    def test_get_letta_client_without_base_url(self, mock_letta):
        """Test _get_letta_client without base URL (should use default)."""
        mock_client = MagicMock()
        mock_letta.return_value = mock_client
        
        client = _get_letta_client()
        
        assert client == mock_client
        mock_letta.assert_called_once_with(token="test-key", base_url=None)
    
    @patch.dict(os.environ, {}, clear=True)
    def test_get_letta_client_missing_api_key(self):
        """Test _get_letta_client without API key."""
        with pytest.raises(RuntimeError, match="LETTA_API_KEY environment variable not set"):
            _get_letta_client()
    
    @patch.dict(os.environ, {"LETTA_API_KEY": "test-key"})
    @patch('smcp.plugins.promptyoself.letta_client.Letta')
    def test_get_letta_client_singleton(self, mock_letta):
        """Test _get_letta_client returns same instance (singleton)."""
        mock_client = MagicMock()
        mock_letta.return_value = mock_client
        
        client1 = _get_letta_client()
        client2 = _get_letta_client()
        
        assert client1 == client2
        mock_letta.assert_called_once()  # Should only be called once


class TestSendPromptToAgent:
    """Test class for send_prompt_to_agent function."""
    
    def setup_method(self):
        """Reset global client before each test."""
        import smcp.plugins.promptyoself.letta_client
        smcp.plugins.promptyoself.letta_client._letta_client = None
    
    @patch('smcp.plugins.promptyoself.letta_client._get_letta_client')
    def test_send_prompt_to_agent_success(self, mock_get_client):
        """Test send_prompt_to_agent with successful message send."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        
        mock_response = {"id": "msg-123", "content": "Response"}
        mock_client.agents.messages.create.return_value = mock_response
        
        result = send_prompt_to_agent("agent-123", "Test prompt")
        
        assert result is True
        mock_client.agents.messages.create.assert_called_once_with(
            agent_id="agent-123",
            messages=[{"role": "user", "content": "Test prompt"}]
        )
    
    @patch('smcp.plugins.promptyoself.letta_client._get_letta_client')
    def test_send_prompt_to_agent_client_error(self, mock_get_client):
        """Test send_prompt_to_agent with client error."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        
        mock_client.agents.messages.create.side_effect = Exception("API Error")
        
        result = send_prompt_to_agent("agent-123", "Test prompt")
        
        assert result is False
    
    @patch('smcp.plugins.promptyoself.letta_client._get_letta_client')
    def test_send_prompt_to_agent_get_client_error(self, mock_get_client):
        """Test send_prompt_to_agent with client initialization error."""
        mock_get_client.side_effect = Exception("Client init error")
        
        result = send_prompt_to_agent("agent-123", "Test prompt")
        
        assert result is False


class TestTestLettaConnection:
    """Test class for test_letta_connection function."""
    
    def setup_method(self):
        """Reset global client before each test."""
        import smcp.plugins.promptyoself.letta_client
        smcp.plugins.promptyoself.letta_client._letta_client = None
    
    @patch('smcp.plugins.promptyoself.letta_client._get_letta_client')
    def test_test_letta_connection_success(self, mock_get_client):
        """Test test_letta_connection with successful connection."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        
        mock_agents = [
            MagicMock(id="agent-1"),
            MagicMock(id="agent-2")
        ]
        mock_client.agents.list.return_value = mock_agents
        
        result = test_letta_connection()
        
        assert result["status"] == "success"
        assert "Connection to Letta server successful" in result["message"]
        assert result["agent_count"] == 2
    
    @patch('smcp.plugins.promptyoself.letta_client._get_letta_client')
    def test_test_letta_connection_no_agents(self, mock_get_client):
        """Test test_letta_connection with no agents."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        
        mock_client.agents.list.return_value = []
        
        result = test_letta_connection()
        
        assert result["status"] == "success"
        assert result["agent_count"] == 0
    
    @patch('smcp.plugins.promptyoself.letta_client._get_letta_client')
    def test_test_letta_connection_client_error(self, mock_get_client):
        """Test test_letta_connection with client error."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        
        mock_client.agents.list.side_effect = Exception("Connection failed")
        
        result = test_letta_connection()
        
        assert result["status"] == "error"
        assert "Failed to connect to Letta server" in result["message"]
        assert "Connection failed" in result["message"]
    
    @patch('smcp.plugins.promptyoself.letta_client._get_letta_client')
    def test_test_letta_connection_get_client_error(self, mock_get_client):
        """Test test_letta_connection with client initialization error."""
        mock_get_client.side_effect = RuntimeError("LETTA_API_KEY environment variable not set")
        
        result = test_letta_connection()
        
        assert result["status"] == "error"
        assert "LETTA_API_KEY environment variable not set" in result["message"]


class TestListAvailableAgents:
    """Test class for list_available_agents function."""
    
    def setup_method(self):
        """Reset global client before each test."""
        import smcp.plugins.promptyoself.letta_client
        smcp.plugins.promptyoself.letta_client._letta_client = None
    
    @patch('smcp.plugins.promptyoself.letta_client._get_letta_client')
    def test_list_available_agents_success(self, mock_get_client):
        """Test list_available_agents with successful agent listing."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        
        mock_agent1 = MagicMock()
        mock_agent1.id = "agent-123"
        mock_agent1.name = "Test Agent 1"
        mock_agent1.created_at = "2024-01-01T12:00:00Z"
        mock_agent1.last_updated = "2024-01-01T12:30:00Z"
        
        mock_agent2 = MagicMock()
        mock_agent2.id = "agent-456"
        mock_agent2.name = "Test Agent 2"
        mock_agent2.created_at = "2024-01-01T13:00:00Z"
        mock_agent2.last_updated = "2024-01-01T13:30:00Z"
        
        mock_client.agents.list.return_value = [mock_agent1, mock_agent2]
        
        result = list_available_agents()
        
        assert result["status"] == "success"
        assert result["count"] == 2
        assert len(result["agents"]) == 2
        
        agent1 = result["agents"][0]
        assert agent1["id"] == "agent-123"
        assert agent1["name"] == "Test Agent 1"
        assert agent1["created_at"] == "2024-01-01T12:00:00Z"
        assert agent1["last_updated"] == "2024-01-01T12:30:00Z"
        
        agent2 = result["agents"][1]
        assert agent2["id"] == "agent-456"
        assert agent2["name"] == "Test Agent 2"
    
    @patch('smcp.plugins.promptyoself.letta_client._get_letta_client')
    def test_list_available_agents_no_agents(self, mock_get_client):
        """Test list_available_agents with no agents."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        
        mock_client.agents.list.return_value = []
        
        result = list_available_agents()
        
        assert result["status"] == "success"
        assert result["count"] == 0
        assert result["agents"] == []
    
    @patch('smcp.plugins.promptyoself.letta_client._get_letta_client')
    def test_list_available_agents_missing_attributes(self, mock_get_client):
        """Test list_available_agents with agents missing optional attributes."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        
        mock_agent = MagicMock()
        mock_agent.id = "agent-123"
        # Missing name, created_at, last_updated attributes
        del mock_agent.name
        del mock_agent.created_at
        del mock_agent.last_updated
        
        mock_client.agents.list.return_value = [mock_agent]
        
        result = list_available_agents()
        
        assert result["status"] == "success"
        assert result["count"] == 1
        
        agent = result["agents"][0]
        assert agent["id"] == "agent-123"
        assert agent["name"] == "Unknown"
        assert agent["created_at"] is None
        assert agent["last_updated"] is None
    
    @patch('smcp.plugins.promptyoself.letta_client._get_letta_client')
    def test_list_available_agents_client_error(self, mock_get_client):
        """Test list_available_agents with client error."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        
        mock_client.agents.list.side_effect = Exception("API Error")
        
        result = list_available_agents()
        
        assert result["status"] == "error"
        assert "Failed to list agents" in result["message"]
        assert "API Error" in result["message"]
    
    @patch('smcp.plugins.promptyoself.letta_client._get_letta_client')
    def test_list_available_agents_get_client_error(self, mock_get_client):
        """Test list_available_agents with client initialization error."""
        mock_get_client.side_effect = RuntimeError("LETTA_API_KEY environment variable not set")
        
        result = list_available_agents()
        
        assert result["status"] == "error"
        assert "LETTA_API_KEY environment variable not set" in result["message"]


class TestValidateAgentExists:
    """Test class for validate_agent_exists function."""
    
    def setup_method(self):
        """Reset global client before each test."""
        import smcp.plugins.promptyoself.letta_client
        smcp.plugins.promptyoself.letta_client._letta_client = None
    
    @patch('smcp.plugins.promptyoself.letta_client._get_letta_client')
    def test_validate_agent_exists_success(self, mock_get_client):
        """Test validate_agent_exists with existing agent."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        
        mock_agent = MagicMock()
        mock_agent.id = "agent-123"
        mock_agent.name = "Test Agent"
        
        mock_client.agents.get.return_value = mock_agent
        
        result = validate_agent_exists("agent-123")
        
        assert result["status"] == "success"
        assert result["exists"] is True
        assert result["agent_id"] == "agent-123"
        assert result["agent_name"] == "Test Agent"
        
        mock_client.agents.get.assert_called_once_with("agent-123")
    
    @patch('smcp.plugins.promptyoself.letta_client._get_letta_client')
    def test_validate_agent_exists_missing_name(self, mock_get_client):
        """Test validate_agent_exists with agent missing name."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        
        mock_agent = MagicMock()
        mock_agent.id = "agent-123"
        del mock_agent.name
        
        mock_client.agents.get.return_value = mock_agent
        
        result = validate_agent_exists("agent-123")
        
        assert result["status"] == "success"
        assert result["exists"] is True
        assert result["agent_name"] == "Unknown"
    
    @patch('smcp.plugins.promptyoself.letta_client._get_letta_client')
    def test_validate_agent_exists_not_found(self, mock_get_client):
        """Test validate_agent_exists with non-existent agent."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        
        mock_client.agents.get.return_value = None
        
        result = validate_agent_exists("agent-999")
        
        assert result["status"] == "error"
        assert result["exists"] is False
        assert "Agent agent-999 not found" in result["message"]
    
    @patch('smcp.plugins.promptyoself.letta_client._get_letta_client')
    def test_validate_agent_exists_client_error(self, mock_get_client):
        """Test validate_agent_exists with client error."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        
        mock_client.agents.get.side_effect = Exception("API Error")
        
        result = validate_agent_exists("agent-123")
        
        assert result["status"] == "error"
        assert result["exists"] is False
        assert "Failed to validate agent agent-123" in result["message"]
        assert "API Error" in result["message"]
    
    @patch('smcp.plugins.promptyoself.letta_client._get_letta_client')
    def test_validate_agent_exists_get_client_error(self, mock_get_client):
        """Test validate_agent_exists with client initialization error."""
        mock_get_client.side_effect = RuntimeError("LETTA_API_KEY environment variable not set")
        
        result = validate_agent_exists("agent-123")
        
        assert result["status"] == "error"
        assert result["exists"] is False
        assert "LETTA_API_KEY environment variable not set" in result["message"]


class TestLettaClientIntegration:
    """Test class for integration scenarios."""
    
    def setup_method(self):
        """Reset global client before each test."""
        import smcp.plugins.promptyoself.letta_client
        smcp.plugins.promptyoself.letta_client._letta_client = None
    
    @patch.dict(os.environ, {"LETTA_API_KEY": "test-key"})
    @patch('smcp.plugins.promptyoself.letta_client.Letta')
    def test_multiple_function_calls_same_client(self, mock_letta):
        """Test that multiple function calls use the same client instance."""
        mock_client = MagicMock()
        mock_letta.return_value = mock_client
        
        # Mock responses
        mock_client.agents.list.return_value = []
        mock_client.agents.get.return_value = MagicMock(id="agent-123", name="Test")
        mock_client.agents.messages.create.return_value = {"id": "msg-123"}
        
        # Call multiple functions
        test_letta_connection()
        list_available_agents()
        validate_agent_exists("agent-123")
        send_prompt_to_agent("agent-123", "Test prompt")
        
        # Client should only be created once
        mock_letta.assert_called_once()
    
    @patch.dict(os.environ, {}, clear=True)
    def test_all_functions_fail_without_api_key(self):
        """Test that all functions fail gracefully without API key."""
        result1 = test_letta_connection()
        result2 = list_available_agents()
        result3 = validate_agent_exists("agent-123")
        result4 = send_prompt_to_agent("agent-123", "Test prompt")
        
        # All should return error status
        assert result1["status"] == "error"
        assert result2["status"] == "error"
        assert result3["status"] == "error"
        assert result4 is False
        
        # All should mention API key error
        assert "LETTA_API_KEY" in result1["message"]
        assert "LETTA_API_KEY" in result2["message"]
        assert "LETTA_API_KEY" in result3["message"]