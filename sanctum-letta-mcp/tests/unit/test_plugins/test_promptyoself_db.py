"""
Unit tests for promptyoself database operations.
"""

import pytest
import tempfile
import os
from datetime import datetime, timedelta
from unittest.mock import patch

from smcp.plugins.promptyoself.db import (
    PromptSchedule, 
    initialize_db, 
    add_schedule, 
    list_schedules, 
    get_schedule, 
    update_schedule, 
    cancel_schedule, 
    get_due_schedules,
    get_session,
    Base,
    engine
)


class TestPromptScheduleDatabase:
    """Test class for promptyoself database operations."""
    
    @pytest.fixture(autouse=True)
    def setup_test_db(self):
        """Setup test database before each test."""
        # Create temporary database file
        self.db_fd, self.db_path = tempfile.mkstemp(suffix='.db')
        
        # Mock the database path
        with patch.dict(os.environ, {'PROMPTYOSELF_DB': self.db_path}):
            # Re-import to get new engine with test database
            from smcp.plugins.promptyoself.db import engine, Base
            Base.metadata.drop_all(bind=engine)
            Base.metadata.create_all(bind=engine)
            
            yield
            
        # Cleanup
        os.close(self.db_fd)
        os.unlink(self.db_path)
    
    def test_initialize_db(self):
        """Test database initialization."""
        # Database should be initialized in setup
        session = get_session()
        try:
            # Should be able to query without error
            result = session.query(PromptSchedule).count()
            assert result == 0
        finally:
            session.close()
    
    def test_add_schedule(self):
        """Test adding a schedule to database."""
        agent_id = "test-agent-123"
        prompt_text = "Test prompt"
        schedule_type = "once"
        schedule_value = "2024-01-01T12:00:00"
        next_run = datetime(2024, 1, 1, 12, 0, 0)
        
        schedule_id = add_schedule(
            agent_id=agent_id,
            prompt_text=prompt_text,
            schedule_type=schedule_type,
            schedule_value=schedule_value,
            next_run=next_run
        )
        
        assert isinstance(schedule_id, int)
        assert schedule_id > 0
        
        # Verify the schedule was added
        schedule = get_schedule(schedule_id)
        assert schedule is not None
        assert schedule.agent_id == agent_id
        assert schedule.prompt_text == prompt_text
        assert schedule.schedule_type == schedule_type
        assert schedule.schedule_value == schedule_value
        assert schedule.next_run == next_run
        assert schedule.active is True
        assert schedule.created_at is not None
        assert schedule.last_run is None
    
    def test_add_schedule_cron(self):
        """Test adding a cron schedule."""
        schedule_id = add_schedule(
            agent_id="test-agent-456",
            prompt_text="Daily reminder",
            schedule_type="cron",
            schedule_value="0 9 * * *",
            next_run=datetime(2024, 1, 2, 9, 0, 0)
        )
        
        assert schedule_id > 0
        
        schedule = get_schedule(schedule_id)
        assert schedule.schedule_type == "cron"
        assert schedule.schedule_value == "0 9 * * *"
    
    def test_add_schedule_interval(self):
        """Test adding an interval schedule."""
        schedule_id = add_schedule(
            agent_id="test-agent-789",
            prompt_text="Every 5 minutes",
            schedule_type="interval",
            schedule_value="5m",
            next_run=datetime.utcnow() + timedelta(minutes=5)
        )
        
        assert schedule_id > 0
        
        schedule = get_schedule(schedule_id)
        assert schedule.schedule_type == "interval"
        assert schedule.schedule_value == "5m"
    
    def test_list_schedules_empty(self):
        """Test listing schedules when database is empty."""
        schedules = list_schedules()
        assert schedules == []
    
    def test_list_schedules_with_data(self):
        """Test listing schedules with data."""
        # Add some test schedules
        id1 = add_schedule("agent-1", "Prompt 1", "once", "2024-01-01T12:00:00", datetime(2024, 1, 1, 12, 0, 0))
        id2 = add_schedule("agent-2", "Prompt 2", "cron", "0 9 * * *", datetime(2024, 1, 2, 9, 0, 0))
        
        schedules = list_schedules()
        
        assert len(schedules) == 2
        assert schedules[0]["id"] == id1
        assert schedules[1]["id"] == id2
        
        # Verify schedule structure
        schedule = schedules[0]
        assert "id" in schedule
        assert "agent_id" in schedule
        assert "prompt_text" in schedule
        assert "schedule_type" in schedule
        assert "schedule_value" in schedule
        assert "next_run" in schedule
        assert "active" in schedule
        assert "created_at" in schedule
        assert "last_run" in schedule
    
    def test_list_schedules_filter_by_agent(self):
        """Test listing schedules filtered by agent."""
        add_schedule("agent-1", "Prompt 1", "once", "2024-01-01T12:00:00", datetime(2024, 1, 1, 12, 0, 0))
        add_schedule("agent-2", "Prompt 2", "cron", "0 9 * * *", datetime(2024, 1, 2, 9, 0, 0))
        add_schedule("agent-1", "Prompt 3", "once", "2024-01-03T12:00:00", datetime(2024, 1, 3, 12, 0, 0))
        
        schedules = list_schedules(agent_id="agent-1")
        
        assert len(schedules) == 2
        assert all(s["agent_id"] == "agent-1" for s in schedules)
    
    def test_list_schedules_active_only(self):
        """Test listing only active schedules."""
        id1 = add_schedule("agent-1", "Prompt 1", "once", "2024-01-01T12:00:00", datetime(2024, 1, 1, 12, 0, 0))
        id2 = add_schedule("agent-2", "Prompt 2", "cron", "0 9 * * *", datetime(2024, 1, 2, 9, 0, 0))
        
        # Cancel one schedule
        cancel_schedule(id1)
        
        # List only active schedules
        schedules = list_schedules(active_only=True)
        assert len(schedules) == 1
        assert schedules[0]["id"] == id2
        
        # List all schedules
        schedules = list_schedules(active_only=False)
        assert len(schedules) == 2
    
    def test_get_schedule_exists(self):
        """Test getting an existing schedule."""
        schedule_id = add_schedule("agent-1", "Test prompt", "once", "2024-01-01T12:00:00", datetime(2024, 1, 1, 12, 0, 0))
        
        schedule = get_schedule(schedule_id)
        
        assert schedule is not None
        assert schedule.id == schedule_id
        assert schedule.agent_id == "agent-1"
        assert schedule.prompt_text == "Test prompt"
    
    def test_get_schedule_not_exists(self):
        """Test getting a non-existent schedule."""
        schedule = get_schedule(999)
        assert schedule is None
    
    def test_update_schedule_exists(self):
        """Test updating an existing schedule."""
        schedule_id = add_schedule("agent-1", "Test prompt", "once", "2024-01-01T12:00:00", datetime(2024, 1, 1, 12, 0, 0))
        
        new_next_run = datetime(2024, 1, 2, 12, 0, 0)
        success = update_schedule(schedule_id, next_run=new_next_run, last_run=datetime.utcnow())
        
        assert success is True
        
        schedule = get_schedule(schedule_id)
        assert schedule.next_run == new_next_run
        assert schedule.last_run is not None
    
    def test_update_schedule_not_exists(self):
        """Test updating a non-existent schedule."""
        success = update_schedule(999, next_run=datetime.utcnow())
        assert success is False
    
    def test_update_schedule_multiple_fields(self):
        """Test updating multiple fields of a schedule."""
        schedule_id = add_schedule("agent-1", "Test prompt", "once", "2024-01-01T12:00:00", datetime(2024, 1, 1, 12, 0, 0))
        
        updates = {
            "prompt_text": "Updated prompt",
            "active": False,
            "last_run": datetime.utcnow()
        }
        
        success = update_schedule(schedule_id, **updates)
        assert success is True
        
        schedule = get_schedule(schedule_id)
        assert schedule.prompt_text == "Updated prompt"
        assert schedule.active is False
        assert schedule.last_run is not None
    
    def test_cancel_schedule_exists(self):
        """Test canceling an existing schedule."""
        schedule_id = add_schedule("agent-1", "Test prompt", "once", "2024-01-01T12:00:00", datetime(2024, 1, 1, 12, 0, 0))
        
        success = cancel_schedule(schedule_id)
        assert success is True
        
        schedule = get_schedule(schedule_id)
        assert schedule.active is False
    
    def test_cancel_schedule_not_exists(self):
        """Test canceling a non-existent schedule."""
        success = cancel_schedule(999)
        assert success is False
    
    def test_get_due_schedules_empty(self):
        """Test getting due schedules when none are due."""
        # Add future schedule
        future_time = datetime.utcnow() + timedelta(hours=1)
        add_schedule("agent-1", "Future prompt", "once", "2024-01-01T12:00:00", future_time)
        
        due_schedules = get_due_schedules()
        assert len(due_schedules) == 0
    
    def test_get_due_schedules_with_due(self):
        """Test getting due schedules when some are due."""
        # Add past schedule (due)
        past_time = datetime.utcnow() - timedelta(minutes=5)
        id1 = add_schedule("agent-1", "Past prompt", "once", "2024-01-01T12:00:00", past_time)
        
        # Add future schedule (not due)
        future_time = datetime.utcnow() + timedelta(hours=1)
        add_schedule("agent-2", "Future prompt", "once", "2024-01-01T12:00:00", future_time)
        
        # Add current schedule (due)
        current_time = datetime.utcnow()
        id2 = add_schedule("agent-3", "Current prompt", "once", "2024-01-01T12:00:00", current_time)
        
        due_schedules = get_due_schedules()
        
        assert len(due_schedules) == 2
        due_ids = [s.id for s in due_schedules]
        assert id1 in due_ids
        assert id2 in due_ids
    
    def test_get_due_schedules_ignores_inactive(self):
        """Test that get_due_schedules ignores inactive schedules."""
        # Add due schedule
        past_time = datetime.utcnow() - timedelta(minutes=5)
        schedule_id = add_schedule("agent-1", "Past prompt", "once", "2024-01-01T12:00:00", past_time)
        
        # Cancel the schedule
        cancel_schedule(schedule_id)
        
        due_schedules = get_due_schedules()
        assert len(due_schedules) == 0
    
    def test_schedule_ordering(self):
        """Test that schedules are ordered by next_run."""
        # Add schedules in random order
        time1 = datetime(2024, 1, 3, 12, 0, 0)
        time2 = datetime(2024, 1, 1, 12, 0, 0)
        time3 = datetime(2024, 1, 2, 12, 0, 0)
        
        add_schedule("agent-1", "Third", "once", "2024-01-03T12:00:00", time1)
        add_schedule("agent-2", "First", "once", "2024-01-01T12:00:00", time2)
        add_schedule("agent-3", "Second", "once", "2024-01-02T12:00:00", time3)
        
        schedules = list_schedules()
        
        assert len(schedules) == 3
        assert schedules[0]["prompt_text"] == "First"
        assert schedules[1]["prompt_text"] == "Second"
        assert schedules[2]["prompt_text"] == "Third"
    
    def test_schedule_datetime_handling(self):
        """Test proper datetime handling in schedules."""
        now = datetime.utcnow()
        schedule_id = add_schedule("agent-1", "Test prompt", "once", "2024-01-01T12:00:00", now)
        
        schedule = get_schedule(schedule_id)
        
        # Check datetime fields are preserved
        assert isinstance(schedule.next_run, datetime)
        assert isinstance(schedule.created_at, datetime)
        assert schedule.last_run is None
        
        # Check ISO format in list output
        schedules = list_schedules()
        schedule_dict = schedules[0]
        
        # Should be ISO format strings
        assert isinstance(schedule_dict["next_run"], str)
        assert isinstance(schedule_dict["created_at"], str)
        assert schedule_dict["last_run"] is None
        
        # Should be parseable back to datetime
        from datetime import datetime
        parsed_time = datetime.fromisoformat(schedule_dict["next_run"].replace('Z', '+00:00'))
        assert isinstance(parsed_time, datetime)