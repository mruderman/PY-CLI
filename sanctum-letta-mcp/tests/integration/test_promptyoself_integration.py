"""
Integration tests for promptyoself plugin workflows.
These tests verify complete workflows from CLI to database to Letta server.
"""

import pytest
import subprocess
import json
import tempfile
import os
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock


class TestPromptyoselfCLIIntegration:
    """Integration tests for promptyoself CLI commands."""
    
    @pytest.fixture(autouse=True)
    def setup_test_environment(self):
        """Setup test environment with temporary database."""
        # Create temporary database
        self.db_fd, self.db_path = tempfile.mkstemp(suffix='.db')
        
        # Set environment variables
        self.env_vars = {
            'PROMPTYOSELF_DB': self.db_path,
            'LETTA_API_KEY': 'test-key',
            'LETTA_BASE_URL': 'https://test.letta.com',
            'PYTHONPATH': '/home/cyansam/GitProjTWO/_PYP-CLI/sanctum-letta-mcp'
        }
        
        yield
        
        # Cleanup
        os.close(self.db_fd)
        os.unlink(self.db_path)
    
    def run_cli_command(self, command_args):
        """Run CLI command and return parsed JSON result."""
        cmd = ['python', '-m', 'smcp.plugins.promptyoself.cli'] + command_args
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env={**os.environ, **self.env_vars},
            cwd='/home/cyansam/GitProjTWO/_PYP-CLI/sanctum-letta-mcp'
        )
        
        try:
            output = json.loads(result.stdout)
        except json.JSONDecodeError:
            output = {"error": f"Invalid JSON output: {result.stdout}", "stderr": result.stderr}
        
        return output, result.returncode
    
    def test_cli_help_command(self):
        """Test CLI help command works."""
        result = subprocess.run(
            ['python', '-m', 'smcp.plugins.promptyoself.cli', '--help'],
            capture_output=True,
            text=True,
            env={**os.environ, **self.env_vars},
            cwd='/home/cyansam/GitProjTWO/_PYP-CLI/sanctum-letta-mcp'
        )
        
        assert result.returncode == 0
        assert "Schedule and manage prompts for Letta agents" in result.stdout
        assert "Available commands:" in result.stdout
        assert "register" in result.stdout
        assert "list" in result.stdout
        assert "cancel" in result.stdout
        assert "execute" in result.stdout
        assert "test" in result.stdout
        assert "agents" in result.stdout
    
    @patch('smcp.plugins.promptyoself.letta_client.validate_agent_exists')
    def test_register_list_workflow(self, mock_validate):
        """Test complete register and list workflow."""
        mock_validate.return_value = {"status": "success"}
        
        # Register a prompt
        future_time = (datetime.utcnow() + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S")
        output, code = self.run_cli_command([
            'register',
            '--agent-id', 'agent-123',
            '--prompt', 'Test prompt',
            '--time', future_time
        ])
        
        assert code == 0
        assert output["status"] == "success"
        assert "id" in output
        assert "next_run" in output
        schedule_id = output["id"]
        
        # List prompts
        output, code = self.run_cli_command(['list'])
        
        assert code == 0
        assert output["status"] == "success"
        assert output["count"] == 1
        assert len(output["schedules"]) == 1
        
        schedule = output["schedules"][0]
        assert schedule["id"] == schedule_id
        assert schedule["agent_id"] == "agent-123"
        assert schedule["prompt_text"] == "Test prompt"
        assert schedule["schedule_type"] == "once"
        assert schedule["active"] is True
    
    @patch('smcp.plugins.promptyoself.letta_client.validate_agent_exists')
    def test_register_cancel_workflow(self, mock_validate):
        """Test complete register and cancel workflow."""
        mock_validate.return_value = {"status": "success"}
        
        # Register a prompt
        future_time = (datetime.utcnow() + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S")
        output, code = self.run_cli_command([
            'register',
            '--agent-id', 'agent-123',
            '--prompt', 'Test prompt',
            '--time', future_time
        ])
        
        assert code == 0
        schedule_id = output["id"]
        
        # Cancel the prompt
        output, code = self.run_cli_command(['cancel', '--id', str(schedule_id)])
        
        assert code == 0
        assert output["status"] == "success"
        assert output["cancelled_id"] == schedule_id
        
        # Verify it's cancelled (should not appear in active list)
        output, code = self.run_cli_command(['list'])
        
        assert code == 0
        assert output["count"] == 0
        
        # Should appear in all list
        output, code = self.run_cli_command(['list', '--all'])
        
        assert code == 0
        assert output["count"] == 1
        assert output["schedules"][0]["active"] is False
    
    @patch('smcp.plugins.promptyoself.letta_client.validate_agent_exists')
    def test_register_cron_schedule(self, mock_validate):
        """Test registering a cron schedule."""
        mock_validate.return_value = {"status": "success"}
        
        output, code = self.run_cli_command([
            'register',
            '--agent-id', 'agent-123',
            '--prompt', 'Daily reminder',
            '--cron', '0 9 * * *'
        ])
        
        assert code == 0
        assert output["status"] == "success"
        
        # Verify schedule details
        output, code = self.run_cli_command(['list'])
        
        assert code == 0
        schedule = output["schedules"][0]
        assert schedule["schedule_type"] == "cron"
        assert schedule["schedule_value"] == "0 9 * * *"
    
    @patch('smcp.plugins.promptyoself.letta_client.validate_agent_exists')
    def test_register_interval_schedule(self, mock_validate):
        """Test registering an interval schedule."""
        mock_validate.return_value = {"status": "success"}
        
        output, code = self.run_cli_command([
            'register',
            '--agent-id', 'agent-123',
            '--prompt', 'Every 5 minutes',
            '--every', '5m'
        ])
        
        assert code == 0
        assert output["status"] == "success"
        
        # Verify schedule details
        output, code = self.run_cli_command(['list'])
        
        assert code == 0
        schedule = output["schedules"][0]
        assert schedule["schedule_type"] == "interval"
        assert schedule["schedule_value"] == "5m"
    
    def test_register_missing_arguments(self):
        """Test register command with missing arguments."""
        # Missing agent-id
        output, code = self.run_cli_command([
            'register',
            '--prompt', 'Test prompt',
            '--time', '2024-01-01T12:00:00'
        ])
        
        assert code != 0  # Should fail
        
        # Missing prompt
        output, code = self.run_cli_command([
            'register',
            '--agent-id', 'agent-123',
            '--time', '2024-01-01T12:00:00'
        ])
        
        assert code != 0  # Should fail
        
        # Missing schedule option
        output, code = self.run_cli_command([
            'register',
            '--agent-id', 'agent-123',
            '--prompt', 'Test prompt'
        ])
        
        assert code == 1
        assert "error" in output
        assert "Must specify one of" in output["error"]
    
    def test_register_invalid_time(self):
        """Test register command with invalid time."""
        # Past time
        past_time = (datetime.utcnow() - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S")
        output, code = self.run_cli_command([
            'register',
            '--agent-id', 'agent-123',
            '--prompt', 'Test prompt',
            '--time', past_time,
            '--skip-validation'
        ])
        
        assert code == 1
        assert "error" in output
        assert "must be in the future" in output["error"]
    
    def test_register_invalid_cron(self):
        """Test register command with invalid cron expression."""
        output, code = self.run_cli_command([
            'register',
            '--agent-id', 'agent-123',
            '--prompt', 'Test prompt',
            '--cron', 'invalid cron expression',
            '--skip-validation'
        ])
        
        assert code == 1
        assert "error" in output
        assert "Invalid cron expression" in output["error"]
    
    def test_register_invalid_interval(self):
        """Test register command with invalid interval."""
        output, code = self.run_cli_command([
            'register',
            '--agent-id', 'agent-123',
            '--prompt', 'Test prompt',
            '--every', 'invalid interval',
            '--skip-validation'
        ])
        
        assert code == 1
        assert "error" in output
        assert "Invalid interval format" in output["error"]
    
    def test_cancel_invalid_id(self):
        """Test cancel command with invalid ID."""
        output, code = self.run_cli_command(['cancel', '--id', 'not-a-number'])
        
        assert code == 1
        assert "error" in output
        assert "must be a number" in output["error"]
    
    def test_cancel_nonexistent_id(self):
        """Test cancel command with non-existent ID."""
        output, code = self.run_cli_command(['cancel', '--id', '999'])
        
        assert code == 1
        assert "error" in output
        assert "not found" in output["error"]
    
    def test_list_with_agent_filter(self):
        """Test list command with agent filter."""
        with patch('smcp.plugins.promptyoself.letta_client.validate_agent_exists') as mock_validate:
            mock_validate.return_value = {"status": "success"}
            
            # Register prompts for different agents
            future_time = (datetime.utcnow() + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S")
            
            self.run_cli_command([
                'register',
                '--agent-id', 'agent-123',
                '--prompt', 'Prompt 1',
                '--time', future_time
            ])\n            
            self.run_cli_command([
                'register',
                '--agent-id', 'agent-456',
                '--prompt', 'Prompt 2',
                '--time', future_time
            ])
            
            # List all prompts
            output, code = self.run_cli_command(['list'])
            assert code == 0
            assert output["count"] == 2
            
            # List prompts for specific agent
            output, code = self.run_cli_command(['list', '--agent-id', 'agent-123'])
            assert code == 0
            assert output["count"] == 1
            assert output["schedules"][0]["agent_id"] == "agent-123"
    
    @patch('smcp.plugins.promptyoself.letta_client.send_prompt_to_agent')
    @patch('smcp.plugins.promptyoself.letta_client.validate_agent_exists')
    def test_execute_workflow(self, mock_validate, mock_send):
        """Test execute command workflow."""
        mock_validate.return_value = {"status": "success"}
        mock_send.return_value = True
        
        # Register a prompt that's due now
        past_time = (datetime.utcnow() - timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%S")
        output, code = self.run_cli_command([
            'register',
            '--agent-id', 'agent-123',
            '--prompt', 'Test prompt',
            '--time', past_time
        ])
        
        assert code == 0
        schedule_id = output["id"]
        
        # Execute due prompts
        output, code = self.run_cli_command(['execute'])
        
        assert code == 0
        assert output["status"] == "success"
        assert len(output["executed"]) == 1
        assert output["executed"][0]["id"] == schedule_id
        assert output["executed"][0]["delivered"] is True
    
    @patch('smcp.plugins.promptyoself.letta_client.test_letta_connection')
    def test_test_connection_command(self, mock_test):
        """Test test command."""
        mock_test.return_value = {
            "status": "success",
            "message": "Connection successful",
            "agent_count": 2
        }
        
        output, code = self.run_cli_command(['test'])
        
        assert code == 0
        assert output["status"] == "success"
        assert "Connection successful" in output["message"]
    
    @patch('smcp.plugins.promptyoself.letta_client.list_available_agents')
    def test_agents_command(self, mock_list):
        """Test agents command."""
        mock_list.return_value = {
            "status": "success",
            "agents": [
                {"id": "agent-123", "name": "Test Agent 1"},
                {"id": "agent-456", "name": "Test Agent 2"}
            ],
            "count": 2
        }
        
        output, code = self.run_cli_command(['agents'])
        
        assert code == 0
        assert output["status"] == "success"
        assert output["count"] == 2
        assert len(output["agents"]) == 2
    
    def test_multiple_register_operations(self):
        """Test multiple register operations to verify database consistency."""
        with patch('smcp.plugins.promptyoself.letta_client.validate_agent_exists') as mock_validate:
            mock_validate.return_value = {"status": "success"}
            
            future_time = (datetime.utcnow() + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S")
            
            # Register multiple prompts
            for i in range(5):
                output, code = self.run_cli_command([
                    'register',
                    '--agent-id', f'agent-{i}',
                    '--prompt', f'Prompt {i}',
                    '--time', future_time
                ])
                
                assert code == 0
                assert output["status"] == "success"
            
            # Verify all are listed
            output, code = self.run_cli_command(['list'])
            
            assert code == 0
            assert output["count"] == 5
            
            # Verify ordering (should be by next_run time)
            schedules = output["schedules"]
            for i in range(4):
                assert schedules[i]["next_run"] <= schedules[i+1]["next_run"]
    
    def test_database_persistence(self):
        """Test that database changes persist between CLI calls."""
        with patch('smcp.plugins.promptyoself.letta_client.validate_agent_exists') as mock_validate:
            mock_validate.return_value = {"status": "success"}
            
            # Register a prompt
            future_time = (datetime.utcnow() + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S")
            output, code = self.run_cli_command([
                'register',
                '--agent-id', 'agent-123',
                '--prompt', 'Persistent prompt',
                '--time', future_time
            ])
            
            assert code == 0
            schedule_id = output["id"]
            
            # Verify it exists in a separate CLI call
            output, code = self.run_cli_command(['list'])
            
            assert code == 0
            assert output["count"] == 1
            assert output["schedules"][0]["id"] == schedule_id
            assert output["schedules"][0]["prompt_text"] == "Persistent prompt"
    
    def test_error_handling_consistency(self):
        """Test that error handling is consistent across commands."""
        # Test various error conditions
        error_cases = [
            (['register', '--agent-id', 'agent-123'], "Missing required arguments"),
            (['cancel', '--id', 'invalid'], "must be a number"),
            (['cancel', '--id', '999'], "not found"),
        ]
        
        for args, expected_error in error_cases:
            output, code = self.run_cli_command(args)
            
            assert code == 1
            assert "error" in output
            assert expected_error.lower() in output["error"].lower()


class TestPromptyoselfMCPIntegration:
    """Integration tests for promptyoself MCP tool integration."""
    
    def test_mcp_tool_discovery(self):
        """Test that promptyoself tools are discoverable by MCP server."""
        # This would require the MCP server to be running
        # For now, we'll test the CLI help output format that MCP server parses
        
        result = subprocess.run(
            ['python', '-m', 'smcp.plugins.promptyoself.cli', '--help'],
            capture_output=True,
            text=True,
            env={**os.environ, 'PYTHONPATH': '/home/cyansam/GitProjTWO/_PYP-CLI/sanctum-letta-mcp'},
            cwd='/home/cyansam/GitProjTWO/_PYP-CLI/sanctum-letta-mcp'
        )
        
        assert result.returncode == 0
        
        # Check that the help output contains the expected format for MCP discovery
        help_output = result.stdout
        assert "Available commands:" in help_output
        
        # Check that all expected commands are listed
        expected_commands = ["register", "list", "cancel", "execute", "test", "agents"]
        for command in expected_commands:
            assert command in help_output
    
    def test_json_output_format(self):
        """Test that all CLI commands produce valid JSON output."""
        with patch('smcp.plugins.promptyoself.letta_client.test_letta_connection') as mock_test:
            mock_test.return_value = {"status": "success", "message": "Connected"}
            
            result = subprocess.run(
                ['python', '-m', 'smcp.plugins.promptyoself.cli', 'test'],
                capture_output=True,
                text=True,
                env={**os.environ, 'PYTHONPATH': '/home/cyansam/GitProjTWO/_PYP-CLI/sanctum-letta-mcp'},
                cwd='/home/cyansam/GitProjTWO/_PYP-CLI/sanctum-letta-mcp'
            )
            
            assert result.returncode == 0
            
            # Should be valid JSON
            try:
                output = json.loads(result.stdout)
                assert isinstance(output, dict)
                assert "status" in output
            except json.JSONDecodeError:
                pytest.fail("CLI output is not valid JSON")
    
    def test_cli_argument_parsing(self):
        """Test that CLI argument parsing handles edge cases correctly."""
        # Test with various argument formats
        test_cases = [
            # Different ways to specify agent-id
            ['register', '--agent-id', 'agent-123', '--prompt', 'Test', '--time', '2024-01-01T12:00:00', '--skip-validation'],
            ['register', '--agent_id', 'agent-123', '--prompt', 'Test', '--time', '2024-01-01T12:00:00', '--skip-validation'],
            
            # Different interval formats
            ['register', '--agent-id', 'agent-123', '--prompt', 'Test', '--every', '30s', '--skip-validation'],
            ['register', '--agent-id', 'agent-123', '--prompt', 'Test', '--every', '5m', '--skip-validation'],
            ['register', '--agent-id', 'agent-123', '--prompt', 'Test', '--every', '1h', '--skip-validation'],
        ]
        
        for args in test_cases:
            result = subprocess.run(
                ['python', '-m', 'smcp.plugins.promptyoself.cli'] + args,
                capture_output=True,
                text=True,
                env={**os.environ, 'PYTHONPATH': '/home/cyansam/GitProjTWO/_PYP-CLI/sanctum-letta-mcp'},
                cwd='/home/cyansam/GitProjTWO/_PYP-CLI/sanctum-letta-mcp'
            )
            
            # Should parse without argument errors
            try:
                output = json.loads(result.stdout)
                # May fail for business logic reasons, but not argument parsing
                assert isinstance(output, dict)
            except json.JSONDecodeError:
                pytest.fail(f"Argument parsing failed for: {args}")