"""
Unit tests for promptyoself CLI commands.
"""

import pytest
import json
from unittest.mock import patch, MagicMock, call
from datetime import datetime, timedelta
from io import StringIO

from smcp.plugins.promptyoself.cli import (
    register_prompt,
    list_prompts,
    cancel_prompt,
    execute_prompts,
    test_connection,
    list_agents,
    main
)


class TestPromptyoselfCLI:
    """Test class for promptyoself CLI commands."""
    
    def test_register_prompt_missing_args(self):
        """Test register_prompt with missing arguments."""
        # Missing agent_id
        result = register_prompt({"prompt": "Test prompt"})
        assert "error" in result
        assert "Missing required arguments" in result["error"]
        
        # Missing prompt
        result = register_prompt({"agent_id": "agent-123"})
        assert "error" in result
        assert "Missing required arguments" in result["error"]
        
        # Missing both agent_id and prompt
        result = register_prompt({})
        assert "error" in result
        assert "Missing required arguments" in result["error"]
    
    def test_register_prompt_no_schedule_options(self):
        """Test register_prompt with no scheduling options."""
        result = register_prompt({
            "agent_id": "agent-123",
            "prompt": "Test prompt"
        })
        assert "error" in result
        assert "Must specify one of --time, --cron, or --every" in result["error"]
    
    def test_register_prompt_multiple_schedule_options(self):
        """Test register_prompt with multiple scheduling options."""
        result = register_prompt({
            "agent_id": "agent-123",
            "prompt": "Test prompt",
            "time": "2024-01-01T12:00:00",
            "cron": "0 9 * * *"
        })
        assert "error" in result
        assert "Cannot specify multiple scheduling options" in result["error"]
        
        result = register_prompt({
            "agent_id": "agent-123",
            "prompt": "Test prompt",
            "time": "2024-01-01T12:00:00",
            "every": "5m"
        })
        assert "error" in result
        assert "Cannot specify multiple scheduling options" in result["error"]
    
    @patch('smcp.plugins.promptyoself.cli.validate_agent_exists')
    def test_register_prompt_agent_validation_failure(self, mock_validate):
        """Test register_prompt with agent validation failure."""
        mock_validate.return_value = {
            "status": "error",
            "message": "Agent not found"
        }
        
        result = register_prompt({
            "agent_id": "agent-123",
            "prompt": "Test prompt",
            "time": "2024-01-01T12:00:00"
        })
        assert "error" in result
        assert "Agent validation failed" in result["error"]
        assert "Agent not found" in result["error"]
    
    @patch('smcp.plugins.promptyoself.cli.validate_agent_exists')
    def test_register_prompt_skip_validation(self, mock_validate):
        """Test register_prompt with validation skipped."""
        with patch('smcp.plugins.promptyoself.cli.add_schedule') as mock_add:
            mock_add.return_value = 1
            
            result = register_prompt({
                "agent_id": "agent-123",
                "prompt": "Test prompt",
                "time": "2024-01-01T12:00:00",
                "skip_validation": True
            })
            
            # Should not call validation
            mock_validate.assert_not_called()
            assert result["status"] == "success"
    
    @patch('smcp.plugins.promptyoself.cli.validate_agent_exists')
    @patch('smcp.plugins.promptyoself.cli.add_schedule')
    def test_register_prompt_once_schedule(self, mock_add, mock_validate):
        """Test register_prompt with one-time schedule."""
        mock_validate.return_value = {"status": "success"}
        mock_add.return_value = 1
        
        result = register_prompt({
            "agent_id": "agent-123",
            "prompt": "Test prompt",
            "time": "2024-01-01T12:00:00"
        })
        
        assert result["status"] == "success"
        assert result["id"] == 1
        assert "next_run" in result
        assert "Prompt scheduled with ID 1" in result["message"]
        
        # Check add_schedule was called with correct parameters
        mock_add.assert_called_once()
        call_args = mock_add.call_args[1]
        assert call_args["agent_id"] == "agent-123"
        assert call_args["prompt_text"] == "Test prompt"
        assert call_args["schedule_type"] == "once"
        assert call_args["schedule_value"] == "2024-01-01T12:00:00"
    
    @patch('smcp.plugins.promptyoself.cli.validate_agent_exists')
    @patch('smcp.plugins.promptyoself.cli.add_schedule')
    def test_register_prompt_past_time(self, mock_add, mock_validate):
        """Test register_prompt with past time."""
        mock_validate.return_value = {"status": "success"}
        
        past_time = (datetime.utcnow() - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S")
        result = register_prompt({
            "agent_id": "agent-123",
            "prompt": "Test prompt",
            "time": past_time
        })
        
        assert "error" in result
        assert "Scheduled time must be in the future" in result["error"]
        mock_add.assert_not_called()
    
    @patch('smcp.plugins.promptyoself.cli.validate_agent_exists')
    @patch('smcp.plugins.promptyoself.cli.add_schedule')
    @patch('smcp.plugins.promptyoself.cli.calculate_next_run')
    def test_register_prompt_cron_schedule(self, mock_calc, mock_add, mock_validate):
        """Test register_prompt with cron schedule."""
        mock_validate.return_value = {"status": "success"}
        mock_add.return_value = 2
        mock_calc.return_value = datetime(2024, 1, 1, 9, 0, 0)
        
        result = register_prompt({
            "agent_id": "agent-123",
            "prompt": "Daily reminder",
            "cron": "0 9 * * *"
        })
        
        assert result["status"] == "success"
        assert result["id"] == 2
        
        # Check add_schedule was called with correct parameters
        call_args = mock_add.call_args[1]
        assert call_args["schedule_type"] == "cron"
        assert call_args["schedule_value"] == "0 9 * * *"
    
    @patch('smcp.plugins.promptyoself.cli.validate_agent_exists')
    @patch('smcp.plugins.promptyoself.cli.add_schedule')
    def test_register_prompt_invalid_cron(self, mock_add, mock_validate):
        """Test register_prompt with invalid cron expression."""
        mock_validate.return_value = {"status": "success"}
        
        result = register_prompt({
            "agent_id": "agent-123",
            "prompt": "Test prompt",
            "cron": "invalid cron"
        })
        
        assert "error" in result
        assert "Invalid cron expression" in result["error"]
        mock_add.assert_not_called()
    
    @patch('smcp.plugins.promptyoself.cli.validate_agent_exists')
    @patch('smcp.plugins.promptyoself.cli.add_schedule')
    def test_register_prompt_interval_schedule(self, mock_add, mock_validate):
        """Test register_prompt with interval schedule."""
        mock_validate.return_value = {"status": "success"}
        mock_add.return_value = 3
        
        result = register_prompt({
            "agent_id": "agent-123",
            "prompt": "Every 5 minutes",
            "every": "5m"
        })
        
        assert result["status"] == "success"
        assert result["id"] == 3
        
        # Check add_schedule was called with correct parameters
        call_args = mock_add.call_args[1]
        assert call_args["schedule_type"] == "interval"
        assert call_args["schedule_value"] == "5m"
    
    @patch('smcp.plugins.promptyoself.cli.validate_agent_exists')
    @patch('smcp.plugins.promptyoself.cli.add_schedule')
    def test_register_prompt_interval_formats(self, mock_add, mock_validate):
        """Test register_prompt with different interval formats."""
        mock_validate.return_value = {"status": "success"}
        mock_add.return_value = 1
        
        # Test seconds
        result = register_prompt({
            "agent_id": "agent-123",
            "prompt": "Every 30 seconds",
            "every": "30s"
        })
        assert result["status"] == "success"
        
        # Test minutes  
        result = register_prompt({
            "agent_id": "agent-123",
            "prompt": "Every 5 minutes",
            "every": "5m"
        })
        assert result["status"] == "success"
        
        # Test hours
        result = register_prompt({
            "agent_id": "agent-123",
            "prompt": "Every hour",
            "every": "1h"
        })
        assert result["status"] == "success"
        
        # Test default (seconds)
        result = register_prompt({
            "agent_id": "agent-123",
            "prompt": "Every 60 seconds",
            "every": "60"
        })
        assert result["status"] == "success"
    
    @patch('smcp.plugins.promptyoself.cli.validate_agent_exists')
    def test_register_prompt_invalid_interval(self, mock_validate):
        """Test register_prompt with invalid interval format."""
        mock_validate.return_value = {"status": "success"}
        
        result = register_prompt({
            "agent_id": "agent-123",
            "prompt": "Test prompt",
            "every": "invalid"
        })
        
        assert "error" in result
        assert "Invalid interval format" in result["error"]
    
    @patch('smcp.plugins.promptyoself.cli.list_schedules')
    def test_list_prompts_success(self, mock_list):
        """Test list_prompts successful execution."""
        mock_list.return_value = [
            {
                "id": 1,
                "agent_id": "agent-123",
                "prompt_text": "Test prompt",
                "schedule_type": "once",
                "next_run": "2024-01-01T12:00:00",
                "active": True
            }
        ]
        
        result = list_prompts({})
        
        assert result["status"] == "success"
        assert result["count"] == 1
        assert len(result["schedules"]) == 1
        assert result["schedules"][0]["id"] == 1
    
    @patch('smcp.plugins.promptyoself.cli.list_schedules')
    def test_list_prompts_with_agent_filter(self, mock_list):
        """Test list_prompts with agent filter."""
        mock_list.return_value = []
        
        result = list_prompts({"agent_id": "agent-123"})
        
        mock_list.assert_called_once_with(agent_id="agent-123", active_only=True)
        assert result["status"] == "success"
    
    @patch('smcp.plugins.promptyoself.cli.list_schedules')
    def test_list_prompts_show_all(self, mock_list):
        """Test list_prompts with show all flag."""
        mock_list.return_value = []
        
        result = list_prompts({"all": True})
        
        mock_list.assert_called_once_with(agent_id=None, active_only=False)
        assert result["status"] == "success"
    
    @patch('smcp.plugins.promptyoself.cli.list_schedules')
    def test_list_prompts_exception(self, mock_list):
        """Test list_prompts with exception."""
        mock_list.side_effect = Exception("Database error")
        
        result = list_prompts({})
        
        assert "error" in result
        assert "Failed to list prompts" in result["error"]
        assert "Database error" in result["error"]
    
    def test_cancel_prompt_missing_id(self):
        """Test cancel_prompt with missing ID."""
        result = cancel_prompt({})
        
        assert "error" in result
        assert "Missing required argument: id" in result["error"]
    
    def test_cancel_prompt_invalid_id(self):
        """Test cancel_prompt with invalid ID."""
        result = cancel_prompt({"id": "not-a-number"})
        
        assert "error" in result
        assert "Schedule ID must be a number" in result["error"]
    
    @patch('smcp.plugins.promptyoself.cli.cancel_schedule')
    def test_cancel_prompt_success(self, mock_cancel):
        """Test cancel_prompt successful execution."""
        mock_cancel.return_value = True
        
        result = cancel_prompt({"id": "123"})
        
        assert result["status"] == "success"
        assert result["cancelled_id"] == 123
        assert "Schedule 123 cancelled" in result["message"]
        mock_cancel.assert_called_once_with(123)
    
    @patch('smcp.plugins.promptyoself.cli.cancel_schedule')
    def test_cancel_prompt_not_found(self, mock_cancel):
        """Test cancel_prompt with non-existent schedule."""
        mock_cancel.return_value = False
        
        result = cancel_prompt({"id": "999"})
        
        assert "error" in result
        assert "Schedule 999 not found or already cancelled" in result["error"]
    
    @patch('smcp.plugins.promptyoself.cli.cancel_schedule')
    def test_cancel_prompt_exception(self, mock_cancel):
        """Test cancel_prompt with exception."""
        mock_cancel.side_effect = Exception("Database error")
        
        result = cancel_prompt({"id": "123"})
        
        assert "error" in result
        assert "Failed to cancel prompt" in result["error"]
    
    @patch('smcp.plugins.promptyoself.cli.execute_due_prompts')
    def test_execute_prompts_success(self, mock_execute):
        """Test execute_prompts successful execution."""
        mock_execute.return_value = [
            {"id": 1, "agent_id": "agent-123", "delivered": True},
            {"id": 2, "agent_id": "agent-456", "delivered": True}
        ]
        
        result = execute_prompts({})
        
        assert result["status"] == "success"
        assert len(result["executed"]) == 2
        assert "2 prompts executed" in result["message"]
    
    @patch('smcp.plugins.promptyoself.cli.run_scheduler_loop')
    def test_execute_prompts_loop_mode(self, mock_loop):
        """Test execute_prompts in loop mode."""
        result = execute_prompts({"loop": True, "interval": 30})
        
        assert result["status"] == "success"
        assert "Scheduler loop completed" in result["message"]
        mock_loop.assert_called_once_with(30)
    
    @patch('smcp.plugins.promptyoself.cli.run_scheduler_loop')
    def test_execute_prompts_loop_mode_default_interval(self, mock_loop):
        """Test execute_prompts in loop mode with default interval."""
        result = execute_prompts({"loop": True})
        
        mock_loop.assert_called_once_with(60)
    
    def test_execute_prompts_loop_mode_invalid_interval(self):
        """Test execute_prompts with invalid interval."""
        result = execute_prompts({"loop": True, "interval": "invalid"})
        
        assert "error" in result
        assert "Interval must be a number" in result["error"]
    
    @patch('smcp.plugins.promptyoself.cli.execute_due_prompts')
    def test_execute_prompts_exception(self, mock_execute):
        """Test execute_prompts with exception."""
        mock_execute.side_effect = Exception("Execution error")
        
        result = execute_prompts({})
        
        assert "error" in result
        assert "Failed to execute prompts" in result["error"]
    
    @patch('smcp.plugins.promptyoself.cli.test_letta_connection')
    def test_test_connection_success(self, mock_test):
        """Test test_connection successful execution."""
        mock_test.return_value = {
            "status": "success",
            "message": "Connection successful"
        }
        
        result = test_connection({})
        
        assert result["status"] == "success"
        assert "Connection successful" in result["message"]
    
    @patch('smcp.plugins.promptyoself.cli.test_letta_connection')
    def test_test_connection_exception(self, mock_test):
        """Test test_connection with exception."""
        mock_test.side_effect = Exception("Connection error")
        
        result = test_connection({})
        
        assert "error" in result
        assert "Failed to test connection" in result["error"]
    
    @patch('smcp.plugins.promptyoself.cli.list_available_agents')
    def test_list_agents_success(self, mock_list):
        """Test list_agents successful execution."""
        mock_list.return_value = {
            "status": "success",
            "agents": [
                {"id": "agent-123", "name": "Test Agent"}
            ],
            "count": 1
        }
        
        result = list_agents({})
        
        assert result["status"] == "success"
        assert result["count"] == 1
        assert len(result["agents"]) == 1
    
    @patch('smcp.plugins.promptyoself.cli.list_available_agents')
    def test_list_agents_exception(self, mock_list):
        """Test list_agents with exception."""
        mock_list.side_effect = Exception("API error")
        
        result = list_agents({})
        
        assert "error" in result
        assert "Failed to list agents" in result["error"]
    
    @patch('sys.stdout', new_callable=StringIO)
    @patch('sys.argv', ['cli.py', 'test'])
    @patch('smcp.plugins.promptyoself.cli.test_letta_connection')
    def test_main_test_command(self, mock_test, mock_stdout):
        """Test main function with test command."""
        mock_test.return_value = {"status": "success", "message": "Connected"}
        
        try:
            main()
        except SystemExit as e:
            assert e.code == 0
        
        output = mock_stdout.getvalue()
        result = json.loads(output)
        assert result["status"] == "success"
    
    @patch('sys.stdout', new_callable=StringIO)
    @patch('sys.argv', ['cli.py', 'agents'])
    @patch('smcp.plugins.promptyoself.cli.list_available_agents')
    def test_main_agents_command(self, mock_list, mock_stdout):
        """Test main function with agents command."""
        mock_list.return_value = {"status": "success", "agents": [], "count": 0}
        
        try:
            main()
        except SystemExit as e:
            assert e.code == 0
        
        output = mock_stdout.getvalue()
        result = json.loads(output)
        assert result["status"] == "success"
    
    @patch('sys.stdout', new_callable=StringIO)
    @patch('sys.argv', ['cli.py', 'register', '--agent-id', 'agent-123', '--prompt', 'Test', '--time', '2024-01-01T12:00:00'])
    @patch('smcp.plugins.promptyoself.cli.validate_agent_exists')
    @patch('smcp.plugins.promptyoself.cli.add_schedule')
    def test_main_register_command(self, mock_add, mock_validate, mock_stdout):
        """Test main function with register command."""
        mock_validate.return_value = {"status": "success"}
        mock_add.return_value = 1
        
        try:
            main()
        except SystemExit as e:
            assert e.code == 0
        
        output = mock_stdout.getvalue()
        result = json.loads(output)
        assert result["status"] == "success"
    
    @patch('sys.stdout', new_callable=StringIO)
    @patch('sys.argv', ['cli.py', 'unknown-command'])
    def test_main_unknown_command(self, mock_stdout):
        """Test main function with unknown command."""
        try:
            main()
        except SystemExit as e:
            assert e.code == 1
        
        output = mock_stdout.getvalue()
        result = json.loads(output)
        assert "error" in result
        assert "Unknown command" in result["error"]
    
    @patch('sys.stdout', new_callable=StringIO)
    @patch('sys.argv', ['cli.py', 'register', '--agent-id', 'agent-123', '--prompt', 'Test'])
    def test_main_error_exit_code(self, mock_stdout):
        """Test main function exits with error code on failure."""
        try:
            main()
        except SystemExit as e:
            assert e.code == 1
        
        output = mock_stdout.getvalue()
        result = json.loads(output)
        assert "error" in result