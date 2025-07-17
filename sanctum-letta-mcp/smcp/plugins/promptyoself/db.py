from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from .models import PromptSchedule, get_session

def add_schedule(agent_id: str, prompt_text: str, schedule_type: str, 
                schedule_value: str, next_run: datetime) -> int:
    """Add a new schedule to the database."""
    session = get_session()
    try:
        schedule = PromptSchedule(
            agent_id=agent_id,
            prompt_text=prompt_text,
            schedule_type=schedule_type,
            schedule_value=schedule_value,
            next_run=next_run
        )
        session.add(schedule)
        session.commit()
        return schedule.id
    finally:
        session.close()

def list_schedules(agent_id: Optional[str] = None, active_only: bool = True) -> List[Dict[str, Any]]:
    """List schedules with optional filtering."""
    session = get_session()
    try:
        query = session.query(PromptSchedule)
        
        if active_only:
            query = query.filter(PromptSchedule.active == True)
        
        if agent_id:
            query = query.filter(PromptSchedule.agent_id == agent_id)
        
        schedules = query.order_by(PromptSchedule.next_run).all()
        
        return [
            {
                "id": s.id,
                "agent_id": s.agent_id,
                "prompt_text": s.prompt_text[:100] + "..." if len(s.prompt_text) > 100 else s.prompt_text,
                "schedule_type": s.schedule_type,
                "schedule_value": s.schedule_value,
                "next_run": s.next_run.isoformat(),
                "created_at": s.created_at.isoformat(),
                "active": s.active,
                "last_run": s.last_run.isoformat() if s.last_run else None
            }
            for s in schedules
        ]
    finally:
        session.close()

def get_schedule(schedule_id: int) -> Optional[PromptSchedule]:
    """Get a schedule by ID."""
    session = get_session()
    try:
        return session.query(PromptSchedule).filter(PromptSchedule.id == schedule_id).first()
    finally:
        session.close()

def update_schedule(schedule_id: int, **kwargs) -> bool:
    """Update a schedule."""
    session = get_session()
    try:
        schedule = session.query(PromptSchedule).filter(PromptSchedule.id == schedule_id).first()
        if not schedule:
            return False
        
        for key, value in kwargs.items():
            if hasattr(schedule, key):
                setattr(schedule, key, value)
        
        session.commit()
        return True
    finally:
        session.close()

def cancel_schedule(schedule_id: int) -> bool:
    """Cancel (deactivate) a schedule."""
    return update_schedule(schedule_id, active=False)

def get_due_schedules() -> List[PromptSchedule]:
    """Get all active schedules that are due to run."""
    session = get_session()
    try:
        now = datetime.utcnow()
        return session.query(PromptSchedule).filter(
            PromptSchedule.active == True,
            PromptSchedule.next_run <= now
        ).all()
    finally:
        session.close()