# Phase 6: Testing Integration

## Overview
Add comprehensive testing suite following the existing test structure in the sanctum-letta-mcp project, including unit tests, integration tests, and end-to-end tests.

## Prerequisites
- Phase 5 completed
- Existing test infrastructure in `tests/` directory
- pytest and testing dependencies from requirements.txt

## Tasks

### 6.1 Create Unit Tests for Database Operations
**File**: `tests/unit/test_plugins/test_promptyoself_db.py`

```python
"""Unit tests for promptyoself database operations."""

import pytest
import tempfile
import os
from datetime import datetime, timedelta
from unittest.mock import patch

from smcp.plugins.promptyoself.db import (
    add_schedule, list_schedules, get_schedule, 
    update_schedule, cancel_schedule, get_due_schedules
)
from smcp.plugins.promptyoself.models import create_tables, PromptSchedule

@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name
    
    # Set environment variable for test database
    with patch.dict(os.environ, {'PROMPTYOSELF_DB_PATH': db_path}):
        # Create tables
        create_tables()
        yield db_path
    
    # Cleanup
    os.unlink(db_path)

class TestDatabaseOperations:
    """Test database CRUD operations."""
    
    def test_add_schedule(self, temp_db):
        """Test adding a new schedule."""
        future_time = datetime.utcnow() + timedelta(hours=1)
        
        schedule_id = add_schedule(
            agent_id="test-agent",
            prompt_text="Test prompt",
            schedule_type="once",
            schedule_value="2024-12-31 12:00:00",
            next_run=future_time
        )
        
        assert isinstance(schedule_id, int)
        assert schedule_id > 0
    
    def test_list_schedules_empty(self, temp_db):
        """Test listing schedules when none exist."""
        schedules = list_schedules()
        assert schedules == []
    
    def test_list_schedules_with_data(self, temp_db):
        """Test listing schedules with data."""
        future_time = datetime.utcnow() + timedelta(hours=1)
        
        # Add two schedules
        id1 = add_schedule("agent1", "Prompt 1", "once", "value1", future_time)
        id2 = add_schedule("agent2", "Prompt 2", "cron", "0 9 * * *", future_time)
        
        schedules = list_schedules()
        assert len(schedules) == 2
        
        # Check structure
        schedule = schedules[0]
        assert "id" in schedule
        assert "agent_id" in schedule
        assert "prompt_text" in schedule
        assert "schedule_type" in schedule
        assert "next_run" in schedule
        assert "active" in schedule
    
    def test_list_schedules_filter_by_agent(self, temp_db):
        """Test filtering schedules by agent."""
        future_time = datetime.utcnow() + timedelta(hours=1)
        
        add_schedule("agent1", "Prompt 1", "once", "value1", future_time)
        add_schedule("agent2", "Prompt 2", "once", "value2", future_time)
        
        agent1_schedules = list_schedules(agent_id="agent1")
        assert len(agent1_schedules) == 1
        assert agent1_schedules[0]["agent_id"] == "agent1"
    
    def test_get_schedule(self, temp_db):
        """Test getting a specific schedule."""
        future_time = datetime.utcnow() + timedelta(hours=1)
        
        schedule_id = add_schedule("test-agent", "Test", "once", "value", future_time)
        
        schedule = get_schedule(schedule_id)
        assert schedule is not None
        assert schedule.id == schedule_id
        assert schedule.agent_id == "test-agent"
    
    def test_get_schedule_not_found(self, temp_db):
        """Test getting non-existent schedule."""
        schedule = get_schedule(999)
        assert schedule is None
    
    def test_update_schedule(self, temp_db):
        """Test updating a schedule."""
        future_time = datetime.utcnow() + timedelta(hours=1)
        new_time = datetime.utcnow() + timedelta(hours=2)
        
        schedule_id = add_schedule("test-agent", "Test", "once", "value", future_time)
        
        success = update_schedule(schedule_id, next_run=new_time, active=False)
        assert success is True
        
        schedule = get_schedule(schedule_id)
        assert schedule.active is False
        assert schedule.next_run == new_time
    
    def test_cancel_schedule(self, temp_db):
        """Test cancelling a schedule."""
        future_time = datetime.utcnow() + timedelta(hours=1)
        
        schedule_id = add_schedule("test-agent", "Test", "once", "value", future_time)
        
        success = cancel_schedule(schedule_id)
        assert success is True
        
        schedule = get_schedule(schedule_id)
        assert schedule.active is False
    
    def test_get_due_schedules(self, temp_db):
        """Test getting due schedules."""
        past_time = datetime.utcnow() - timedelta(minutes=1)
        future_time = datetime.utcnow() + timedelta(hours=1)
        
        # Add due and not-due schedules
        due_id = add_schedule("agent1", "Due prompt", "once", "value1", past_time)
        not_due_id = add_schedule("agent2", "Future prompt", "once", "value2", future_time)
        
        due_schedules = get_due_schedules()
        
        assert len(due_schedules) == 1
        assert due_schedules[0].id == due_id
```

### 6.2 Create Unit Tests for CLI Commands
**File**: `tests/unit/test_plugins/test_promptyoself_cli.py`

```python
"""Unit tests for promptyoself CLI commands."""

import pytest
import json
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

from smcp.plugins.promptyoself.cli import (
    register_prompt, list_prompts, cancel_prompt, execute_prompts,
    test_connection, list_agents
)

class TestCLICommands:
    """Test CLI command functions."""
    
    @patch('smcp.plugins.promptyoself.cli.add_schedule')
    @patch('smcp.plugins.promptyoself.cli.validate_agent_exists')
    def test_register_prompt_once(self, mock_validate, mock_add):
        """Test registering a one-time prompt."""
        mock_validate.return_value = True
        mock_add.return_value = 123
        
        args = {
            "agent-id": "test-agent",
            "prompt": "Test prompt",
            "time": "2024-12-31 12:00:00",
            "cron": None,
            "every": None,
            "skip-validation": False
        }
        
        result = register_prompt(args)
        
        assert result["status"] == "success"
        assert result["id"] == 123
        assert "next_run" in result
        mock_add.assert_called_once()
    
    @patch('smcp.plugins.promptyoself.cli.add_schedule')
    @patch('smcp.plugins.promptyoself.cli.validate_agent_exists')
    def test_register_prompt_cron(self, mock_validate, mock_add):
        """Test registering a cron-based prompt."""
        mock_validate.return_value = True
        mock_add.return_value = 456
        
        args = {
            "agent-id": "test-agent",
            "prompt": "Daily prompt",
            "time": None,
            "cron": "0 9 * * *",
            "every": None,
            "skip-validation": False
        }
        
        result = register_prompt(args)
        
        assert result["status"] == "success"
        assert result["id"] == 456
    
    def test_register_prompt_missing_args(self):
        """Test registering with missing arguments."""
        args = {
            "agent-id": None,
            "prompt": "Test prompt"
        }
        
        result = register_prompt(args)
        
        assert "error" in result
        assert "Missing required arguments" in result["error"]
    
    def test_register_prompt_multiple_schedules(self):
        """Test registering with multiple schedule types."""
        args = {
            "agent-id": "test-agent",
            "prompt": "Test prompt",
            "time": "2024-12-31 12:00:00",
            "cron": "0 9 * * *",
            "every": None
        }
        
        result = register_prompt(args)
        
        assert "error" in result
        assert "exactly one of" in result["error"]
    
    @patch('smcp.plugins.promptyoself.cli.list_schedules')
    def test_list_prompts(self, mock_list):
        """Test listing prompts."""
        mock_list.return_value = [
            {"id": 1, "agent_id": "agent1", "prompt_text": "Test"}
        ]
        
        args = {"agent-id": None, "all": False}
        result = list_prompts(args)
        
        assert result["status"] == "success"
        assert result["count"] == 1
        assert len(result["schedules"]) == 1
    
    @patch('smcp.plugins.promptyoself.cli.cancel_schedule')
    def test_cancel_prompt_success(self, mock_cancel):
        """Test successful prompt cancellation."""
        mock_cancel.return_value = True
        
        args = {"id": "123"}
        result = cancel_prompt(args)
        
        assert result["status"] == "success"
        assert result["cancelled_id"] == 123
    
    @patch('smcp.plugins.promptyoself.cli.cancel_schedule')
    def test_cancel_prompt_not_found(self, mock_cancel):
        """Test cancelling non-existent prompt."""
        mock_cancel.return_value = False
        
        args = {"id": "999"}
        result = cancel_prompt(args)
        
        assert "error" in result
        assert "not found" in result["error"]
    
    def test_cancel_prompt_invalid_id(self):
        """Test cancelling with invalid ID."""
        args = {"id": "not-a-number"}
        result = cancel_prompt(args)
        
        assert "error" in result
        assert "must be a number" in result["error"]
    
    @patch('smcp.plugins.promptyoself.cli.execute_due_prompts')
    def test_execute_prompts(self, mock_execute):
        """Test executing prompts."""
        mock_execute.return_value = [
            {"id": 1, "agent_id": "agent1", "delivered": True}
        ]
        
        args = {"loop": False}
        result = execute_prompts(args)
        
        assert result["status"] == "success"
        assert len(result["executed"]) == 1
        assert "1 prompts executed" in result["message"]
    
    @patch('smcp.plugins.promptyoself.cli.test_letta_connection')
    def test_test_connection_success(self, mock_test):
        """Test successful connection test."""
        mock_test.return_value = {
            "success": True,
            "agent_count": 5,
            "server_url": "https://test.server"
        }
        
        result = test_connection({})
        
        assert result["status"] == "success"
        assert "Connected to" in result["message"]
    
    @patch('smcp.plugins.promptyoself.cli.test_letta_connection')
    def test_test_connection_failure(self, mock_test):
        """Test failed connection test."""
        mock_test.return_value = {
            "success": False,
            "error": "Connection refused"
        }
        
        result = test_connection({})
        
        assert "error" in result
        assert "Connection failed" in result["error"]
```

### 6.3 Create Unit Tests for Scheduler
**File**: `tests/unit/test_plugins/test_promptyoself_scheduler.py`

```python
"""Unit tests for promptyoself scheduler."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from smcp.plugins.promptyoself.scheduler import (
    calculate_next_run, calculate_next_run_for_schedule,
    execute_due_prompts, PromptScheduler
)

class TestSchedulerFunctions:
    """Test scheduler utility functions."""
    
    def test_calculate_next_run_cron(self):
        """Test calculating next run from cron expression."""
        # Test daily at 9 AM
        cron_expr = "0 9 * * *"
        base_time = datetime(2024, 1, 1, 8, 0, 0)  # 8 AM
        
        next_run = calculate_next_run(cron_expr, base_time)
        
        # Should be 9 AM same day
        expected = datetime(2024, 1, 1, 9, 0, 0)
        assert next_run == expected
    
    def test_calculate_next_run_cron_next_day(self):
        """Test cron calculation when next run is tomorrow."""
        cron_expr = "0 9 * * *"
        base_time = datetime(2024, 1, 1, 10, 0, 0)  # 10 AM (after 9 AM)
        
        next_run = calculate_next_run(cron_expr, base_time)
        
        # Should be 9 AM next day
        expected = datetime(2024, 1, 2, 9, 0, 0)
        assert next_run == expected
    
    def test_calculate_next_run_for_schedule_once(self):
        """Test next run calculation for one-time schedule."""
        schedule = MagicMock()
        schedule.schedule_type = "once"
        
        result = calculate_next_run_for_schedule(schedule)
        
        assert result is None
    
    def test_calculate_next_run_for_schedule_cron(self):
        """Test next run calculation for cron schedule."""
        schedule = MagicMock()
        schedule.schedule_type = "cron"
        schedule.schedule_value = "0 9 * * *"
        
        with patch('smcp.plugins.promptyoself.scheduler.calculate_next_run') as mock_calc:
            mock_calc.return_value = datetime(2024, 1, 2, 9, 0, 0)
            
            result = calculate_next_run_for_schedule(schedule)
            
            assert result == datetime(2024, 1, 2, 9, 0, 0)
            mock_calc.assert_called_once_with("0 9 * * *")
    
    def test_calculate_next_run_for_schedule_interval_seconds(self):
        """Test next run calculation for interval schedule (seconds)."""
        schedule = MagicMock()
        schedule.schedule_type = "interval"
        schedule.schedule_value = "30s"
        
        with patch('smcp.plugins.promptyoself.scheduler.datetime') as mock_dt:
            mock_dt.utcnow.return_value = datetime(2024, 1, 1, 12, 0, 0)
            
            result = calculate_next_run_for_schedule(schedule)
            
            expected = datetime(2024, 1, 1, 12, 0, 30)
            assert result == expected
    
    def test_calculate_next_run_for_schedule_interval_minutes(self):
        """Test next run calculation for interval schedule (minutes)."""
        schedule = MagicMock()
        schedule.schedule_type = "interval"
        schedule.schedule_value = "5m"
        
        with patch('smcp.plugins.promptyoself.scheduler.datetime') as mock_dt:
            mock_dt.utcnow.return_value = datetime(2024, 1, 1, 12, 0, 0)
            
            result = calculate_next_run_for_schedule(schedule)
            
            expected = datetime(2024, 1, 1, 12, 5, 0)
            assert result == expected
    
    @patch('smcp.plugins.promptyoself.scheduler.get_due_schedules')
    @patch('smcp.plugins.promptyoself.scheduler.send_prompt_to_agent')
    @patch('smcp.plugins.promptyoself.scheduler.update_schedule')
    def test_execute_due_prompts_success(self, mock_update, mock_send, mock_get_due):
        """Test successful execution of due prompts."""
        # Mock schedule
        schedule = MagicMock()
        schedule.id = 1
        schedule.agent_id = "agent1"
        schedule.prompt_text = "Test prompt"
        schedule.schedule_type = "once"
        schedule.next_run = datetime.utcnow() - timedelta(minutes=1)
        
        mock_get_due.return_value = [schedule]
        mock_send.return_value = True
        
        with patch('smcp.plugins.promptyoself.scheduler.calculate_next_run_for_schedule') as mock_calc:
            mock_calc.return_value = None  # One-time schedule
            
            results = execute_due_prompts()
        
        assert len(results) == 1
        assert results[0]["id"] == 1
        assert results[0]["delivered"] is True
        mock_send.assert_called_once_with("agent1", "Test prompt")
        mock_update.assert_called_once()

class TestPromptScheduler:
    """Test PromptScheduler class."""
    
    def test_scheduler_init(self):
        """Test scheduler initialization."""
        scheduler = PromptScheduler(interval_seconds=30)
        
        assert scheduler.interval_seconds == 30
        assert scheduler.running is False
        assert scheduler.scheduler is None
    
    @patch('smcp.plugins.promptyoself.scheduler.BackgroundScheduler')
    def test_scheduler_start(self, mock_scheduler_class):
        """Test starting the scheduler."""
        mock_scheduler = MagicMock()
        mock_scheduler_class.return_value = mock_scheduler
        
        scheduler = PromptScheduler(interval_seconds=60)
        scheduler.start()
        
        assert scheduler.running is True
        mock_scheduler.add_job.assert_called_once()
        mock_scheduler.start.assert_called_once()
    
    @patch('smcp.plugins.promptyoself.scheduler.BackgroundScheduler')
    def test_scheduler_stop(self, mock_scheduler_class):
        """Test stopping the scheduler."""
        mock_scheduler = MagicMock()
        mock_scheduler_class.return_value = mock_scheduler
        
        scheduler = PromptScheduler()
        scheduler.start()
        scheduler.stop()
        
        assert scheduler.running is False
        mock_scheduler.shutdown.assert_called_once()
```

### 6.4 Create Integration Tests
**File**: `tests/integration/test_promptyoself_integration.py`

```python
"""Integration tests for promptyoself plugin."""

import pytest
import tempfile
import os
import subprocess
import json
from pathlib import Path
from unittest.mock import patch

class TestPromptyoselfIntegration:
    """Integration tests for the complete plugin."""
    
    @pytest.fixture
    def temp_env(self):
        """Create temporary environment for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            
            env_vars = {
                'PROMPTYOSELF_DB_PATH': db_path,
                'LETTA_BASE_URL': 'https://mock.letta.server',
                'LETTA_API_KEY': 'mock-api-key'
            }
            
            with patch.dict(os.environ, env_vars):
                yield temp_dir
    
    def run_cli_command(self, cmd):
        """Helper to run CLI commands."""
        plugin_path = Path(__file__).parent.parent.parent / "smcp" / "plugins" / "promptyoself"
        
        result = subprocess.run(
            ["python", str(plugin_path / "cli.py")] + cmd,
            capture_output=True,
            text=True
        )
        
        if result.stdout:
            try:
                return json.loads(result.stdout)
            except json.JSONDecodeError:
                return {"error": f"Invalid JSON: {result.stdout}"}
        else:
            return {"error": result.stderr}
    
    def test_cli_help(self, temp_env):
        """Test CLI help output."""
        result = subprocess.run(
            ["python", "-c", """
import sys
sys.path.insert(0, 'smcp/plugins/promptyoself')
from cli import main
main()
            """],
            args=["--help"],
            capture_output=True,
            text=True
        )
        
        assert "Available commands:" in result.stdout
        assert "register" in result.stdout
        assert "list" in result.stdout
        assert "cancel" in result.stdout
        assert "execute" in result.stdout
    
    @patch('smcp.plugins.promptyoself.letta_client.validate_agent_exists')
    def test_register_and_list_workflow(self, mock_validate, temp_env):
        """Test complete register and list workflow."""
        mock_validate.return_value = True
        
        # Register a prompt
        register_result = self.run_cli_command([
            "register",
            "--agent-id", "test-agent",
            "--prompt", "Integration test prompt",
            "--every", "1h"
        ])
        
        assert register_result.get("status") == "success"
        schedule_id = register_result["id"]
        
        # List prompts
        list_result = self.run_cli_command(["list"])
        
        assert list_result.get("status") == "success"
        assert list_result["count"] == 1
        assert list_result["schedules"][0]["id"] == schedule_id
    
    @patch('smcp.plugins.promptyoself.letta_client.validate_agent_exists')
    def test_register_and_cancel_workflow(self, mock_validate, temp_env):
        """Test register and cancel workflow."""
        mock_validate.return_value = True
        
        # Register a prompt
        register_result = self.run_cli_command([
            "register",
            "--agent-id", "test-agent",
            "--prompt", "Cancel test prompt",
            "--time", "2024-12-31 23:59:59"
        ])
        
        assert register_result.get("status") == "success"
        schedule_id = register_result["id"]
        
        # Cancel the prompt
        cancel_result = self.run_cli_command([
            "cancel",
            "--id", str(schedule_id)
        ])
        
        assert cancel_result.get("status") == "success"
        assert cancel_result["cancelled_id"] == schedule_id
        
        # Verify it's cancelled (list with --all)
        list_result = self.run_cli_command(["list", "--all"])
        schedule = next(s for s in list_result["schedules"] if s["id"] == schedule_id)
        assert schedule["active"] is False
    
    @patch('smcp.plugins.promptyoself.letta_client.send_prompt_to_agent')
    @patch('smcp.plugins.promptyoself.letta_client.validate_agent_exists')
    def test_execute_workflow(self, mock_validate, mock_send, temp_env):
        """Test execute workflow."""
        mock_validate.return_value = True
        mock_send.return_value = True
        
        # Register a prompt that's due now
        past_time = "2024-01-01 00:00:00"
        register_result = self.run_cli_command([
            "register",
            "--agent-id", "test-agent",
            "--prompt", "Execute test prompt",
            "--time", past_time,
            "--skip-validation"
        ])
        
        assert register_result.get("status") == "success"
        
        # Execute prompts
        execute_result = self.run_cli_command(["execute"])
        
        assert execute_result.get("status") == "success"
        assert len(execute_result["executed"]) == 1
        assert execute_result["executed"][0]["delivered"] is True
```

### 6.5 Update Test Configuration
**File**: Update `pytest.ini` to include promptyoself tests:

```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    --verbose
    --tb=short
    --cov=smcp
    --cov-report=html:htmlcov
    --cov-report=xml:coverage.xml
    --cov-report=term-missing
    --cov-fail-under=100
filterwarnings =
    ignore::DeprecationWarning
    ignore::PendingDeprecationWarning
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    integration: marks tests as integration tests
    unit: marks tests as unit tests
```

### 6.6 Run All Tests
```bash
cd sanctum-letta-mcp

# Run unit tests only
python -m pytest tests/unit/test_plugins/test_promptyoself* -v

# Run integration tests
python -m pytest tests/integration/test_promptyoself* -v

# Run all tests with coverage
python run_tests.py --type unit
python run_tests.py --type integration
python run_tests.py --type coverage
```

### 6.7 Git Commit
```bash
git add .
git commit -m "Phase 6: Add comprehensive testing suite

- Create unit tests for database operations
- Add CLI command testing with mocks
- Implement scheduler function tests
- Create integration tests for complete workflows
- Update test configuration for promptyoself plugin
- Ensure 100% test coverage for all modules

🤖 Generated with Claude Code"
git push origin main
```

## Success Criteria
- [ ] Unit tests cover all database operations
- [ ] CLI commands thoroughly tested with mocks
- [ ] Scheduler functionality tested
- [ ] Integration tests validate complete workflows
- [ ] All tests pass without errors
- [ ] Test coverage meets requirements (100%)
- [ ] Changes committed and pushed to GitHub

## Next Phase
Proceed to Phase 7: Local Deployment & Operations