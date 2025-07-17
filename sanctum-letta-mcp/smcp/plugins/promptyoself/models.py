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