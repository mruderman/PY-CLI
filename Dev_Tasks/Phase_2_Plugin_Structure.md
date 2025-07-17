# Phase 2: Plugin Structure Creation

## Overview
Create the promptyoself plugin directory structure following the existing Sanctum MCP plugin patterns (botfather/devops).

## Prerequisites
- Phase 1 completed
- Understanding of existing plugin structure in `smcp/plugins/`

## Tasks

### 2.1 Create Plugin Directory Structure
**Base Path**: `sanctum-letta-mcp/smcp/plugins/promptyoself/`

Create the following structure:
```
promptyoself/
├── __init__.py
├── cli.py              # Main CLI entry point
├── db.py              # Database operations
├── scheduler.py       # Scheduling logic
├── letta_client.py    # Letta API integration
└── models.py          # SQLAlchemy models
```

### 2.2 Initialize Plugin Module
**File**: `smcp/plugins/promptyoself/__init__.py`
```python
"""
Promptyoself Plugin

Self-hosted prompt scheduler for Letta agents delivered as a Sanctum MCP CLI plugin.
Allows Letta agents to schedule one-off and recurring prompts.
"""

__version__ = "0.1.0"
__author__ = "Promptyoself Development Team"
```

### 2.3 Create Database Models
**File**: `smcp/plugins/promptyoself/models.py`

```python
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

Base = declarative_base()

class PromptSchedule(Base):
    """Database model for scheduled prompts."""
    __tablename__ = "schedules"
    
    id = Column(Integer, primary_key=True)
    agent_id = Column(String(255), nullable=False, index=True)
    prompt_text = Column(Text, nullable=False)
    schedule_type = Column(String(50), nullable=False)  # 'once', 'cron', 'interval'
    schedule_value = Column(String(255), nullable=False)  # datetime string or cron pattern
    next_run = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    active = Column(Boolean, default=True, index=True)
    last_run = Column(DateTime, nullable=True)

def get_database_url():
    """Get database URL from environment."""
    db_path = os.getenv("PROMPTYOSELF_DB_PATH", "./promptyoself.db")
    return f"sqlite:///{db_path}"

def create_tables():
    """Create database tables if they don't exist."""
    engine = create_engine(get_database_url())
    Base.metadata.create_all(engine)
    return engine

def get_session():
    """Get database session."""
    engine = create_tables()
    Session = sessionmaker(bind=engine)
    return Session()
```

### 2.4 Create Database Operations Module
**File**: `smcp/plugins/promptyoself/db.py`

```python
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
```

### 2.5 Git Commit
```bash
git add .
git commit -m "Phase 2: Create promptyoself plugin structure

- Add plugin directory with proper module structure
- Implement SQLAlchemy models for schedule persistence
- Create database operations layer with CRUD functions
- Follow existing plugin patterns from botfather/devops

🤖 Generated with Claude Code"
git push origin main
```

## Success Criteria
- [ ] Plugin directory structure created
- [ ] Database models defined with proper relationships
- [ ] Database operations module implemented
- [ ] All modules properly documented
- [ ] Changes committed and pushed to GitHub

## Next Phase
Proceed to Phase 3: Core CLI Commands Implementation