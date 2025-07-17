import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
from typing import List, Dict, Any, Optional

# --- Database Setup ---
DB_FILE = os.environ.get("PROMPTYOSELF_DB", "promptyoself.db")
engine = create_engine(f"sqlite:///{DB_FILE}")
Base = declarative_base()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# --- Models ---
class PromptSchedule(Base):
    __tablename__ = "schedules"
    id = Column(Integer, primary_key=True)
    agent_id = Column(String, nullable=False, index=True)
    prompt_text = Column(Text, nullable=False)
    schedule_type = Column(String, nullable=False)  # 'once' or 'cron'
    schedule_value = Column(String, nullable=False)
    next_run = Column(DateTime, nullable=False, index=True)
    active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_run = Column(DateTime, nullable=True)

def initialize_db():
    """Create all tables in the database."""
    Base.metadata.create_all(bind=engine)

def get_session() -> Session:
    """Get a new database session."""
    return SessionLocal()

# --- CRUD Operations ---

def add_schedule(agent_id: str, prompt_text: str, schedule_type: str, schedule_value: str, next_run: datetime) -> int:
    """Add a new schedule to the database."""
    session = get_session()
    try:
        new_schedule = PromptSchedule(
            agent_id=agent_id,
            prompt_text=prompt_text,
            schedule_type=schedule_type,
            schedule_value=schedule_value,
            next_run=next_run
        )
        session.add(new_schedule)
        session.commit()
        session.refresh(new_schedule)
        return new_schedule.id
    finally:
        session.close()

def list_schedules(agent_id: Optional[str] = None, active_only: bool = True) -> List[Dict[str, Any]]:
    """List schedules with optional filtering."""
    session = get_session()
    try:
        query = session.query(PromptSchedule)
        if agent_id:
            query = query.filter(PromptSchedule.agent_id == agent_id)
        if active_only:
            query = query.filter(PromptSchedule.active == True)
        
        schedules = query.order_by(PromptSchedule.next_run).all()
        return [
            {
                "id": s.id,
                "agent_id": s.agent_id,
                "prompt_text": s.prompt_text,
                "schedule_type": s.schedule_type,
                "schedule_value": s.schedule_value,
                "next_run": s.next_run.isoformat(),
                "active": s.active,
                "created_at": s.created_at.isoformat(),
                "last_run": s.last_run.isoformat() if s.last_run else None,
            }
            for s in schedules
        ]
    finally:
        session.close()

def get_schedule(schedule_id: int) -> Optional[PromptSchedule]:
    """Get a specific schedule by its ID."""
    session = get_session()
    try:
        return session.query(PromptSchedule).filter(PromptSchedule.id == schedule_id).first()
    finally:
        session.close()

def update_schedule(schedule_id: int, **kwargs) -> bool:
    """Update a schedule's attributes."""
    session = get_session()
    try:
        schedule = session.query(PromptSchedule).filter(PromptSchedule.id == schedule_id).first()
        if not schedule:
            return False
        
        for key, value in kwargs.items():
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

if __name__ == "__main__":
    print("Initializing database...")
    initialize_db()
    print("Database initialized.")