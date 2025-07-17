"""
Unit tests for promptyoself scheduler functionality.
"""

import pytest
import time
from unittest.mock import patch, MagicMock, call
from datetime import datetime, timedelta
from croniter import croniter

from smcp.plugins.promptyoself.scheduler import (
    calculate_next_run,
    calculate_next_run_for_schedule,
    execute_due_prompts,
    PromptScheduler,
    run_scheduler_loop
)


class TestSchedulerCalculations:
    """Test class for scheduler calculation functions."""
    
    def test_calculate_next_run_basic(self):
        """Test calculate_next_run with basic cron expression."""
        # Test daily at 9 AM
        cron_expr = "0 9 * * *"
        base_time = datetime(2024, 1, 1, 8, 0, 0)  # 8 AM
        
        next_run = calculate_next_run(cron_expr, base_time)
        
        assert next_run.hour == 9
        assert next_run.minute == 0
        assert next_run.day == 1  # Same day since it's before 9 AM
    
    def test_calculate_next_run_next_day(self):
        """Test calculate_next_run when next run is tomorrow."""
        # Test daily at 9 AM when current time is 10 AM
        cron_expr = "0 9 * * *"
        base_time = datetime(2024, 1, 1, 10, 0, 0)  # 10 AM
        
        next_run = calculate_next_run(cron_expr, base_time)
        
        assert next_run.hour == 9
        assert next_run.minute == 0
        assert next_run.day == 2  # Next day since it's after 9 AM
    
    def test_calculate_next_run_without_base_time(self):
        """Test calculate_next_run without providing base time."""
        cron_expr = "0 9 * * *"
        
        with patch('smcp.plugins.promptyoself.scheduler.datetime') as mock_datetime:
            mock_datetime.utcnow.return_value = datetime(2024, 1, 1, 8, 0, 0)
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
            
            next_run = calculate_next_run(cron_expr)
            
            assert next_run.hour == 9
            assert next_run.minute == 0
    
    def test_calculate_next_run_every_minute(self):
        """Test calculate_next_run with every minute cron."""
        cron_expr = "* * * * *"
        base_time = datetime(2024, 1, 1, 12, 30, 45)  # 12:30:45
        
        next_run = calculate_next_run(cron_expr, base_time)
        
        assert next_run.minute == 31
        assert next_run.second == 0
    
    def test_calculate_next_run_weekly(self):
        """Test calculate_next_run with weekly cron."""
        # Every Monday at 9 AM
        cron_expr = "0 9 * * 1"
        base_time = datetime(2024, 1, 1, 12, 0, 0)  # Monday 12 PM
        
        next_run = calculate_next_run(cron_expr, base_time)
        
        # Should be next Monday at 9 AM
        assert next_run.weekday() == 0  # Monday
        assert next_run.hour == 9
        assert next_run.minute == 0
    
    def test_calculate_next_run_for_schedule_once(self):
        """Test calculate_next_run_for_schedule with once schedule."""
        schedule = MagicMock()
        schedule.schedule_type = "once"
        
        result = calculate_next_run_for_schedule(schedule)
        assert result is None
    
    def test_calculate_next_run_for_schedule_cron(self):
        """Test calculate_next_run_for_schedule with cron schedule."""
        schedule = MagicMock()
        schedule.schedule_type = "cron"
        schedule.schedule_value = "0 9 * * *"
        
        with patch('smcp.plugins.promptyoself.scheduler.calculate_next_run') as mock_calc:
            mock_calc.return_value = datetime(2024, 1, 2, 9, 0, 0)
            
            result = calculate_next_run_for_schedule(schedule)
            
            assert result == datetime(2024, 1, 2, 9, 0, 0)
            mock_calc.assert_called_once_with("0 9 * * *")
    
    def test_calculate_next_run_for_schedule_interval_seconds(self):
        """Test calculate_next_run_for_schedule with interval in seconds."""
        schedule = MagicMock()
        schedule.schedule_type = "interval"
        schedule.schedule_value = "30s"
        
        with patch('smcp.plugins.promptyoself.scheduler.datetime') as mock_datetime:
            mock_datetime.utcnow.return_value = datetime(2024, 1, 1, 12, 0, 0)
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
            
            result = calculate_next_run_for_schedule(schedule)
            
            expected = datetime(2024, 1, 1, 12, 0, 30)
            assert result == expected
    
    def test_calculate_next_run_for_schedule_interval_minutes(self):
        """Test calculate_next_run_for_schedule with interval in minutes."""
        schedule = MagicMock()
        schedule.schedule_type = "interval"
        schedule.schedule_value = "5m"
        
        with patch('smcp.plugins.promptyoself.scheduler.datetime') as mock_datetime:
            mock_datetime.utcnow.return_value = datetime(2024, 1, 1, 12, 0, 0)
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
            
            result = calculate_next_run_for_schedule(schedule)
            
            expected = datetime(2024, 1, 1, 12, 5, 0)
            assert result == expected
    
    def test_calculate_next_run_for_schedule_interval_hours(self):
        """Test calculate_next_run_for_schedule with interval in hours."""
        schedule = MagicMock()
        schedule.schedule_type = "interval"
        schedule.schedule_value = "2h"
        
        with patch('smcp.plugins.promptyoself.scheduler.datetime') as mock_datetime:
            mock_datetime.utcnow.return_value = datetime(2024, 1, 1, 12, 0, 0)
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
            
            result = calculate_next_run_for_schedule(schedule)
            
            expected = datetime(2024, 1, 1, 14, 0, 0)
            assert result == expected
    
    def test_calculate_next_run_for_schedule_interval_default(self):
        """Test calculate_next_run_for_schedule with interval default format."""
        schedule = MagicMock()
        schedule.schedule_type = "interval"
        schedule.schedule_value = "60"  # Default to seconds
        
        with patch('smcp.plugins.promptyoself.scheduler.datetime') as mock_datetime:
            mock_datetime.utcnow.return_value = datetime(2024, 1, 1, 12, 0, 0)
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
            
            result = calculate_next_run_for_schedule(schedule)
            
            expected = datetime(2024, 1, 1, 12, 1, 0)
            assert result == expected
    
    def test_calculate_next_run_for_schedule_unknown_type(self):
        """Test calculate_next_run_for_schedule with unknown schedule type."""
        schedule = MagicMock()
        schedule.schedule_type = "unknown"
        
        with pytest.raises(ValueError, match="Unknown schedule type"):
            calculate_next_run_for_schedule(schedule)


class TestExecuteDuePrompts:
    """Test class for execute_due_prompts function."""
    
    @patch('smcp.plugins.promptyoself.scheduler.get_due_schedules')
    def test_execute_due_prompts_no_schedules(self, mock_get_due):
        """Test execute_due_prompts with no due schedules."""
        mock_get_due.return_value = []
        
        result = execute_due_prompts()
        
        assert result == []
    
    @patch('smcp.plugins.promptyoself.scheduler.get_due_schedules')
    @patch('smcp.plugins.promptyoself.scheduler.send_prompt_to_agent')
    @patch('smcp.plugins.promptyoself.scheduler.update_schedule')
    @patch('smcp.plugins.promptyoself.scheduler.calculate_next_run_for_schedule')
    def test_execute_due_prompts_success(self, mock_calc, mock_update, mock_send, mock_get_due):
        """Test execute_due_prompts with successful execution."""
        # Mock due schedule
        schedule = MagicMock()
        schedule.id = 1
        schedule.agent_id = "agent-123"
        schedule.prompt_text = "Test prompt"
        schedule.next_run = datetime(2024, 1, 1, 12, 0, 0)
        
        mock_get_due.return_value = [schedule]
        mock_send.return_value = True
        mock_calc.return_value = datetime(2024, 1, 2, 12, 0, 0)
        
        result = execute_due_prompts()
        
        assert len(result) == 1
        assert result[0]["id"] == 1
        assert result[0]["agent_id"] == "agent-123"
        assert result[0]["delivered"] is True
        assert result[0]["next_run"] == "2024-01-02T12:00:00"
        
        # Verify calls
        mock_send.assert_called_once_with("agent-123", "Test prompt")
        mock_update.assert_called_once()
        update_args = mock_update.call_args[1]
        assert "last_run" in update_args
        assert "next_run" in update_args
    
    @patch('smcp.plugins.promptyoself.scheduler.get_due_schedules')
    @patch('smcp.plugins.promptyoself.scheduler.send_prompt_to_agent')
    @patch('smcp.plugins.promptyoself.scheduler.update_schedule')
    @patch('smcp.plugins.promptyoself.scheduler.calculate_next_run_for_schedule')
    def test_execute_due_prompts_once_schedule(self, mock_calc, mock_update, mock_send, mock_get_due):
        """Test execute_due_prompts with once schedule (should deactivate)."""
        schedule = MagicMock()
        schedule.id = 1
        schedule.agent_id = "agent-123"
        schedule.prompt_text = "Test prompt"
        schedule.next_run = datetime(2024, 1, 1, 12, 0, 0)
        
        mock_get_due.return_value = [schedule]
        mock_send.return_value = True
        mock_calc.return_value = None  # No next run for once schedule
        
        result = execute_due_prompts()
        
        assert len(result) == 1
        assert result[0]["next_run"] is None
        
        # Verify schedule is deactivated
        update_args = mock_update.call_args[1]
        assert update_args["active"] is False
    
    @patch('smcp.plugins.promptyoself.scheduler.get_due_schedules')
    @patch('smcp.plugins.promptyoself.scheduler.send_prompt_to_agent')
    @patch('smcp.plugins.promptyoself.scheduler.update_schedule')
    def test_execute_due_prompts_send_failure(self, mock_update, mock_send, mock_get_due):
        """Test execute_due_prompts with send failure."""
        schedule = MagicMock()
        schedule.id = 1
        schedule.agent_id = "agent-123"
        schedule.prompt_text = "Test prompt"
        schedule.next_run = datetime(2024, 1, 1, 12, 0, 0)
        
        mock_get_due.return_value = [schedule]
        mock_send.return_value = False
        
        result = execute_due_prompts()
        
        assert len(result) == 1
        assert result[0]["delivered"] is False
        assert result[0]["error"] == "Failed to deliver prompt"
        assert result[0]["next_run"] == "2024-01-01T12:00:00"  # Keep same next_run
    
    @patch('smcp.plugins.promptyoself.scheduler.get_due_schedules')
    @patch('smcp.plugins.promptyoself.scheduler.send_prompt_to_agent')
    def test_execute_due_prompts_exception(self, mock_send, mock_get_due):
        """Test execute_due_prompts with exception during execution."""
        schedule = MagicMock()
        schedule.id = 1
        schedule.agent_id = "agent-123"
        schedule.prompt_text = "Test prompt"
        schedule.next_run = datetime(2024, 1, 1, 12, 0, 0)
        
        mock_get_due.return_value = [schedule]
        mock_send.side_effect = Exception("Connection error")
        
        result = execute_due_prompts()
        
        assert len(result) == 1
        assert result[0]["delivered"] is False
        assert "Connection error" in result[0]["error"]
    
    @patch('smcp.plugins.promptyoself.scheduler.get_due_schedules')
    @patch('smcp.plugins.promptyoself.scheduler.send_prompt_to_agent')
    @patch('smcp.plugins.promptyoself.scheduler.update_schedule')
    @patch('smcp.plugins.promptyoself.scheduler.calculate_next_run_for_schedule')
    def test_execute_due_prompts_multiple_schedules(self, mock_calc, mock_update, mock_send, mock_get_due):
        """Test execute_due_prompts with multiple schedules."""
        schedule1 = MagicMock()
        schedule1.id = 1
        schedule1.agent_id = "agent-123"
        schedule1.prompt_text = "Test prompt 1"
        schedule1.next_run = datetime(2024, 1, 1, 12, 0, 0)
        
        schedule2 = MagicMock()
        schedule2.id = 2
        schedule2.agent_id = "agent-456"
        schedule2.prompt_text = "Test prompt 2"
        schedule2.next_run = datetime(2024, 1, 1, 12, 0, 0)
        
        mock_get_due.return_value = [schedule1, schedule2]
        mock_send.return_value = True
        mock_calc.return_value = datetime(2024, 1, 2, 12, 0, 0)
        
        result = execute_due_prompts()
        
        assert len(result) == 2
        assert result[0]["id"] == 1
        assert result[1]["id"] == 2
        assert all(r["delivered"] for r in result)
        
        # Verify all schedules were processed
        assert mock_send.call_count == 2
        assert mock_update.call_count == 2


class TestPromptScheduler:
    """Test class for PromptScheduler class."""
    
    def test_init(self):
        """Test PromptScheduler initialization."""
        scheduler = PromptScheduler(interval_seconds=30)
        
        assert scheduler.interval_seconds == 30
        assert scheduler.scheduler is None
        assert scheduler.running is False
    
    def test_init_default_interval(self):
        """Test PromptScheduler initialization with default interval."""
        scheduler = PromptScheduler()
        
        assert scheduler.interval_seconds == 60
    
    @patch('smcp.plugins.promptyoself.scheduler.BackgroundScheduler')
    def test_start(self, mock_scheduler_class):
        """Test PromptScheduler start method."""
        mock_scheduler = MagicMock()
        mock_scheduler_class.return_value = mock_scheduler
        
        scheduler = PromptScheduler(interval_seconds=30)
        scheduler.start()
        
        assert scheduler.running is True
        mock_scheduler.add_job.assert_called_once()
        mock_scheduler.start.assert_called_once()
        
        # Check job configuration
        job_args = mock_scheduler.add_job.call_args
        assert job_args[1]["trigger"].interval == 30
        assert job_args[1]["id"] == "execute_prompts"
    
    @patch('smcp.plugins.promptyoself.scheduler.BackgroundScheduler')
    def test_start_already_running(self, mock_scheduler_class):
        """Test PromptScheduler start when already running."""
        scheduler = PromptScheduler()
        scheduler.running = True
        
        scheduler.start()
        
        # Should not create new scheduler
        mock_scheduler_class.assert_not_called()
    
    def test_stop_not_running(self):
        """Test PromptScheduler stop when not running."""
        scheduler = PromptScheduler()
        
        scheduler.stop()
        
        # Should not raise error
        assert scheduler.running is False
    
    def test_stop_running(self):
        """Test PromptScheduler stop when running."""
        scheduler = PromptScheduler()
        scheduler.running = True
        scheduler.scheduler = MagicMock()
        
        scheduler.stop()
        
        assert scheduler.running is False
        scheduler.scheduler.shutdown.assert_called_once()
    
    @patch('smcp.plugins.promptyoself.scheduler.execute_due_prompts')
    def test_execute_job_success(self, mock_execute):
        """Test PromptScheduler _execute_job method with success."""
        mock_execute.return_value = [{"id": 1, "delivered": True}]
        
        scheduler = PromptScheduler()
        scheduler._execute_job()
        
        mock_execute.assert_called_once()
    
    @patch('smcp.plugins.promptyoself.scheduler.execute_due_prompts')
    def test_execute_job_no_results(self, mock_execute):
        """Test PromptScheduler _execute_job method with no results."""
        mock_execute.return_value = []
        
        scheduler = PromptScheduler()
        scheduler._execute_job()
        
        mock_execute.assert_called_once()
    
    @patch('smcp.plugins.promptyoself.scheduler.execute_due_prompts')
    def test_execute_job_exception(self, mock_execute):
        """Test PromptScheduler _execute_job method with exception."""
        mock_execute.side_effect = Exception("Test error")
        
        scheduler = PromptScheduler()
        scheduler._execute_job()
        
        # Should handle exception gracefully
        mock_execute.assert_called_once()
    
    @patch('smcp.plugins.promptyoself.scheduler.time')
    def test_run_loop_keyboard_interrupt(self, mock_time):
        """Test PromptScheduler run_loop with keyboard interrupt."""
        scheduler = PromptScheduler()
        scheduler.start = MagicMock()
        scheduler.stop = MagicMock()
        
        # Mock time.sleep to raise KeyboardInterrupt
        mock_time.sleep.side_effect = KeyboardInterrupt()
        
        scheduler.run_loop()
        
        scheduler.start.assert_called_once()
        scheduler.stop.assert_called_once()
    
    @patch('smcp.plugins.promptyoself.scheduler.time')
    def test_run_loop_exception(self, mock_time):
        """Test PromptScheduler run_loop with general exception."""
        scheduler = PromptScheduler()
        scheduler.start = MagicMock()
        scheduler.stop = MagicMock()
        
        # Mock time.sleep to raise general exception
        mock_time.sleep.side_effect = Exception("Test error")
        
        with pytest.raises(Exception, match="Test error"):
            scheduler.run_loop()
        
        scheduler.start.assert_called_once()
        scheduler.stop.assert_called_once()


class TestRunSchedulerLoop:
    """Test class for run_scheduler_loop function."""
    
    @patch('smcp.plugins.promptyoself.scheduler.PromptScheduler')
    def test_run_scheduler_loop_default(self, mock_scheduler_class):
        """Test run_scheduler_loop with default interval."""
        mock_scheduler = MagicMock()
        mock_scheduler_class.return_value = mock_scheduler
        
        run_scheduler_loop()
        
        mock_scheduler_class.assert_called_once_with(60)
        mock_scheduler.run_loop.assert_called_once()
    
    @patch('smcp.plugins.promptyoself.scheduler.PromptScheduler')
    def test_run_scheduler_loop_custom_interval(self, mock_scheduler_class):
        """Test run_scheduler_loop with custom interval."""
        mock_scheduler = MagicMock()
        mock_scheduler_class.return_value = mock_scheduler
        
        run_scheduler_loop(interval_seconds=30)
        
        mock_scheduler_class.assert_called_once_with(30)
        mock_scheduler.run_loop.assert_called_once()