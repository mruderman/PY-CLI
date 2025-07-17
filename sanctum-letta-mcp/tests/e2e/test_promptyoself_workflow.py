"""
End-to-end tests for complete promptyoself workflow.
These tests verify the complete system including database, scheduler, and Letta integration.
"""

import pytest
import subprocess
import json
import tempfile
import os
import time
import threading
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, Mock


class TestPromptyoselfE2EWorkflow:
    """End-to-end tests for promptyoself complete workflow."""
    
    @pytest.fixture(autouse=True)
    def setup_test_environment(self):
        """Setup test environment with temporary database and mocked Letta."""
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
    
    def run_cli_command(self, command_args, timeout=30):
        """Run CLI command and return parsed JSON result."""
        cmd = ['python', '-m', 'smcp.plugins.promptyoself.cli'] + command_args
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env={**os.environ, **self.env_vars},
            cwd='/home/cyansam/GitProjTWO/_PYP-CLI/sanctum-letta-mcp',
            timeout=timeout
        )
        
        try:
            output = json.loads(result.stdout)
        except json.JSONDecodeError:
            output = {"error": f"Invalid JSON output: {result.stdout}", "stderr": result.stderr}
        
        return output, result.returncode
    
    @patch('smcp.plugins.promptyoself.letta_client.validate_agent_exists')
    @patch('smcp.plugins.promptyoself.letta_client.send_prompt_to_agent')
    def test_complete_scheduling_workflow(self, mock_send, mock_validate):
        """Test complete workflow: register -> list -> execute -> verify."""
        mock_validate.return_value = {"status": "success"}
        mock_send.return_value = True
        
        # Step 1: Register a prompt that's due in 2 seconds
        future_time = (datetime.utcnow() + timedelta(seconds=2)).strftime("%Y-%m-%dT%H:%M:%S")
        output, code = self.run_cli_command([
            'register',
            '--agent-id', 'agent-123',
            '--prompt', 'Test scheduled prompt',
            '--time', future_time
        ])\n        
        assert code == 0
        assert output["status"] == "success"
        schedule_id = output["id"]
        
        # Step 2: Verify it's in the list
        output, code = self.run_cli_command(['list'])
        
        assert code == 0
        assert output["count"] == 1
        assert output["schedules"][0]["id"] == schedule_id
        assert output["schedules"][0]["active"] is True
        
        # Step 3: Wait for the scheduled time to pass
        time.sleep(3)
        
        # Step 4: Execute due prompts
        output, code = self.run_cli_command(['execute'])
        
        assert code == 0
        assert output["status"] == "success"
        assert len(output["executed"]) == 1
        assert output["executed"][0]["id"] == schedule_id
        assert output["executed"][0]["delivered"] is True
        
        # Step 5: Verify the prompt was sent to Letta
        mock_send.assert_called_once_with('agent-123', 'Test scheduled prompt')
        
        # Step 6: Verify the schedule is now inactive (one-time)
        output, code = self.run_cli_command(['list'])
        
        assert code == 0
        assert output["count"] == 0  # Should be empty since it's a one-time schedule
        
        # Step 7: Verify it shows up in the complete list
        output, code = self.run_cli_command(['list', '--all'])
        
        assert code == 0
        assert output["count"] == 1
        assert output["schedules"][0]["active"] is False
    
    @patch('smcp.plugins.promptyoself.letta_client.validate_agent_exists')
    @patch('smcp.plugins.promptyoself.letta_client.send_prompt_to_agent')
    def test_recurring_schedule_workflow(self, mock_send, mock_validate):
        """Test recurring schedule workflow with interval."""
        mock_validate.return_value = {"status": "success"}
        mock_send.return_value = True
        
        # Register a prompt that runs every 2 seconds
        output, code = self.run_cli_command([
            'register',
            '--agent-id', 'agent-123',
            '--prompt', 'Recurring prompt',
            '--every', '2s'
        ])
        
        assert code == 0
        schedule_id = output["id"]
        
        # Wait for first execution
        time.sleep(2.5)
        
        # Execute first time
        output, code = self.run_cli_command(['execute'])
        
        assert code == 0
        assert len(output["executed"]) == 1
        assert output["executed"][0]["delivered"] is True
        
        # Schedule should still be active
        output, code = self.run_cli_command(['list'])
        
        assert code == 0
        assert output["count"] == 1
        assert output["schedules"][0]["active"] is True
        
        # Wait for second execution
        time.sleep(2.5)
        
        # Execute second time
        output, code = self.run_cli_command(['execute'])
        
        assert code == 0
        assert len(output["executed"]) == 1
        assert output["executed"][0]["delivered"] is True
        
        # Should have been called twice
        assert mock_send.call_count == 2
        
        # Cancel the recurring schedule
        output, code = self.run_cli_command(['cancel', '--id', str(schedule_id)])
        
        assert code == 0
        assert output["status"] == "success"
    
    @patch('smcp.plugins.promptyoself.letta_client.validate_agent_exists')
    @patch('smcp.plugins.promptyoself.letta_client.send_prompt_to_agent')
    def test_multiple_agents_workflow(self, mock_send, mock_validate):
        """Test workflow with multiple agents."""
        mock_validate.return_value = {"status": "success"}
        mock_send.return_value = True
        
        # Register prompts for multiple agents
        agents = ['agent-1', 'agent-2', 'agent-3']
        schedule_ids = []
        
        for i, agent in enumerate(agents):
            future_time = (datetime.utcnow() + timedelta(seconds=2)).strftime("%Y-%m-%dT%H:%M:%S")
            output, code = self.run_cli_command([
                'register',
                '--agent-id', agent,
                '--prompt', f'Prompt for {agent}',
                '--time', future_time
            ])
            
            assert code == 0
            schedule_ids.append(output["id"])
        
        # Verify all are listed
        output, code = self.run_cli_command(['list'])
        
        assert code == 0
        assert output["count"] == 3
        
        # Test agent-specific listing
        output, code = self.run_cli_command(['list', '--agent-id', 'agent-1'])
        
        assert code == 0
        assert output["count"] == 1
        assert output["schedules"][0]["agent_id"] == "agent-1"
        
        # Wait and execute all
        time.sleep(3)
        
        output, code = self.run_cli_command(['execute'])
        
        assert code == 0
        assert len(output["executed"]) == 3
        
        # Verify all agents received their prompts
        expected_calls = [
            ('agent-1', 'Prompt for agent-1'),
            ('agent-2', 'Prompt for agent-2'),
            ('agent-3', 'Prompt for agent-3')
        ]
        
        actual_calls = [call[0] for call in mock_send.call_args_list]
        for expected_call in expected_calls:
            assert expected_call in actual_calls
    
    @patch('smcp.plugins.promptyoself.letta_client.validate_agent_exists')
    @patch('smcp.plugins.promptyoself.letta_client.send_prompt_to_agent')
    def test_error_handling_workflow(self, mock_send, mock_validate):
        """Test workflow with error conditions."""
        mock_validate.return_value = {"status": "success"}
        
        # Test with agent that fails to receive prompt
        mock_send.return_value = False
        
        # Register a prompt
        future_time = (datetime.utcnow() + timedelta(seconds=2)).strftime("%Y-%m-%dT%H:%M:%S")
        output, code = self.run_cli_command([
            'register',
            '--agent-id', 'failing-agent',
            '--prompt', 'This will fail',
            '--time', future_time
        ])
        
        assert code == 0
        schedule_id = output["id"]
        
        # Wait and execute
        time.sleep(3)
        
        output, code = self.run_cli_command(['execute'])
        
        assert code == 0
        assert len(output["executed"]) == 1
        assert output["executed"][0]["delivered"] is False
        assert "error" in output["executed"][0]
        
        # Schedule should still be active (retry opportunity)
        output, code = self.run_cli_command(['list'])
        
        assert code == 0
        assert output["count"] == 1
        assert output["schedules"][0]["active"] is True
    
    @patch('smcp.plugins.promptyoself.letta_client.test_letta_connection')
    @patch('smcp.plugins.promptyoself.letta_client.list_available_agents')
    def test_connection_testing_workflow(self, mock_list_agents, mock_test_connection):
        """Test connection testing workflow."""
        # Mock successful connection
        mock_test_connection.return_value = {
            "status": "success",
            "message": "Connection successful",
            "agent_count": 2
        }
        
        mock_list_agents.return_value = {
            "status": "success",
            "agents": [
                {"id": "agent-1", "name": "Agent 1"},
                {"id": "agent-2", "name": "Agent 2"}
            ],
            "count": 2
        }
        
        # Test connection
        output, code = self.run_cli_command(['test'])
        
        assert code == 0
        assert output["status"] == "success"
        assert "Connection successful" in output["message"]
        
        # List agents
        output, code = self.run_cli_command(['agents'])
        
        assert code == 0
        assert output["status"] == "success"
        assert output["count"] == 2
        assert len(output["agents"]) == 2
    
    @patch('smcp.plugins.promptyoself.letta_client.validate_agent_exists')
    def test_validation_workflow(self, mock_validate):
        """Test agent validation workflow."""
        # Test with non-existent agent
        mock_validate.return_value = {
            "status": "error",
            "exists": False,
            "message": "Agent not found"
        }
        
        output, code = self.run_cli_command([
            'register',
            '--agent-id', 'non-existent-agent',
            '--prompt', 'Test prompt',
            '--time', '2024-01-01T12:00:00'
        ])
        
        assert code == 1
        assert "error" in output
        assert "Agent validation failed" in output["error"]
        
        # Test with validation skipped
        output, code = self.run_cli_command([
            'register',
            '--agent-id', 'non-existent-agent',
            '--prompt', 'Test prompt',
            '--time', '2024-01-01T12:00:00',
            '--skip-validation'
        ])
        
        assert code == 1  # Should still fail due to past time
        assert "must be in the future" in output["error"]
    
    @patch('smcp.plugins.promptyoself.letta_client.validate_agent_exists')
    def test_cron_schedule_workflow(self, mock_validate):
        """Test cron schedule workflow."""
        mock_validate.return_value = {"status": "success"}
        
        # Register a cron schedule (every minute)
        output, code = self.run_cli_command([
            'register',
            '--agent-id', 'agent-123',
            '--prompt', 'Cron prompt',
            '--cron', '* * * * *'
        ])
        
        assert code == 0
        schedule_id = output["id"]
        
        # Verify it's registered correctly
        output, code = self.run_cli_command(['list'])
        
        assert code == 0
        assert output["count"] == 1
        schedule = output["schedules"][0]
        assert schedule["schedule_type"] == "cron"
        assert schedule["schedule_value"] == "* * * * *"
        assert schedule["active"] is True
        
        # Verify next_run is calculated correctly (should be within next minute)
        next_run = datetime.fromisoformat(schedule["next_run"])
        now = datetime.utcnow()
        assert next_run > now
        assert next_run <= now + timedelta(minutes=1)
    
    def test_database_consistency_workflow(self):
        """Test database consistency across multiple operations."""
        with patch('smcp.plugins.promptyoself.letta_client.validate_agent_exists') as mock_validate:
            mock_validate.return_value = {"status": "success"}
            
            # Perform multiple operations
            operations = []
            
            # Register multiple schedules
            for i in range(5):
                future_time = (datetime.utcnow() + timedelta(hours=i+1)).strftime("%Y-%m-%dT%H:%M:%S")
                output, code = self.run_cli_command([
                    'register',
                    '--agent-id', f'agent-{i}',
                    '--prompt', f'Prompt {i}',
                    '--time', future_time
                ])
                
                assert code == 0
                operations.append(('register', output["id"]))
            
            # Cancel some schedules
            for i in range(0, 5, 2):  # Cancel 0, 2, 4
                schedule_id = operations[i][1]
                output, code = self.run_cli_command(['cancel', '--id', str(schedule_id)])
                
                assert code == 0
                operations[i] = ('cancel', schedule_id)
            
            # Verify final state
            output, code = self.run_cli_command(['list'])
            
            assert code == 0
            assert output["count"] == 2  # Should have 2 active schedules (1, 3)
            
            active_ids = [s["id"] for s in output["schedules"]]
            assert operations[1][1] in active_ids
            assert operations[3][1] in active_ids
            
            # Verify complete list
            output, code = self.run_cli_command(['list', '--all'])
            
            assert code == 0
            assert output["count"] == 5  # All 5 schedules should be there
            
            active_count = sum(1 for s in output["schedules"] if s["active"])
            inactive_count = sum(1 for s in output["schedules"] if not s["active"])
            
            assert active_count == 2
            assert inactive_count == 3
    
    def test_concurrent_operations_workflow(self):
        """Test concurrent operations to verify thread safety."""
        with patch('smcp.plugins.promptyoself.letta_client.validate_agent_exists') as mock_validate:
            mock_validate.return_value = {"status": "success"}
            
            # Function to register schedules
            def register_schedules(agent_prefix, count):
                for i in range(count):
                    future_time = (datetime.utcnow() + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S")
                    self.run_cli_command([
                        'register',
                        '--agent-id', f'{agent_prefix}-{i}',
                        '--prompt', f'Concurrent prompt {i}',
                        '--time', future_time
                    ])
            
            # Create multiple threads
            threads = []
            for i in range(3):
                thread = threading.Thread(target=register_schedules, args=(f'agent-group-{i}', 3))
                threads.append(thread)
                thread.start()
            
            # Wait for all threads to complete
            for thread in threads:
                thread.join()
            
            # Verify all schedules were created
            output, code = self.run_cli_command(['list'])
            
            assert code == 0
            assert output["count"] == 9  # 3 threads × 3 schedules each
            
            # Verify no duplicate IDs
            schedule_ids = [s["id"] for s in output["schedules"]]
            assert len(schedule_ids) == len(set(schedule_ids))
    
    @patch('smcp.plugins.promptyoself.letta_client.validate_agent_exists')
    @patch('smcp.plugins.promptyoself.letta_client.send_prompt_to_agent')
    def test_scheduler_loop_workflow(self, mock_send, mock_validate):
        """Test scheduler loop workflow (abbreviated for testing)."""
        mock_validate.return_value = {"status": "success"}
        mock_send.return_value = True
        
        # Register a prompt that will be due soon
        future_time = (datetime.utcnow() + timedelta(seconds=3)).strftime("%Y-%m-%dT%H:%M:%S")
        output, code = self.run_cli_command([
            'register',
            '--agent-id', 'agent-123',
            '--prompt', 'Loop test prompt',
            '--time', future_time
        ])
        
        assert code == 0
        
        # Start scheduler loop in background (with very short interval)
        import subprocess
        import signal
        
        scheduler_process = subprocess.Popen([
            'python', '-m', 'smcp.plugins.promptyoself.cli',
            'execute', '--loop', '--interval', '1'
        ], env={**os.environ, **self.env_vars},
           cwd='/home/cyansam/GitProjTWO/_PYP-CLI/sanctum-letta-mcp')
        
        try:
            # Wait for the schedule to be executed
            time.sleep(5)
            
            # Stop the scheduler
            scheduler_process.terminate()
            scheduler_process.wait(timeout=5)
            
            # Verify the prompt was sent
            assert mock_send.call_count >= 1
            
            # Verify the schedule was processed
            output, code = self.run_cli_command(['list'])
            
            assert code == 0
            assert output["count"] == 0  # Should be deactivated
            
        finally:
            # Ensure process is terminated
            try:
                scheduler_process.terminate()
                scheduler_process.wait(timeout=2)
            except:
                try:
                    scheduler_process.kill()
                    scheduler_process.wait(timeout=2)
                except:
                    pass  # Process might already be dead
    
    def test_performance_workflow(self):
        """Test performance with larger number of schedules."""
        with patch('smcp.plugins.promptyoself.letta_client.validate_agent_exists') as mock_validate:
            mock_validate.return_value = {"status": "success"}
            
            start_time = time.time()
            
            # Register many schedules
            num_schedules = 100
            for i in range(num_schedules):
                future_time = (datetime.utcnow() + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S")
                output, code = self.run_cli_command([
                    'register',
                    '--agent-id', f'agent-{i % 10}',  # 10 different agents
                    '--prompt', f'Performance test prompt {i}',
                    '--time', future_time
                ])
                
                assert code == 0
            
            registration_time = time.time() - start_time
            
            # List all schedules
            start_time = time.time()
            output, code = self.run_cli_command(['list'])
            
            assert code == 0
            assert output["count"] == num_schedules
            
            list_time = time.time() - start_time
            
            # Performance assertions (adjust thresholds as needed)
            assert registration_time < 60  # Should complete within 60 seconds
            assert list_time < 5  # Should list within 5 seconds
            
            # Test agent-specific filtering performance
            start_time = time.time()
            output, code = self.run_cli_command(['list', '--agent-id', 'agent-0'])
            
            assert code == 0
            assert output["count"] == 10  # agent-0 should have 10 schedules
            
            filter_time = time.time() - start_time
            assert filter_time < 2  # Should filter within 2 seconds