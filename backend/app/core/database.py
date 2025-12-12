"""
Database configuration and session management.
"""
import time
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError
from app.core.config import settings

logger = logging.getLogger(__name__)

Base = declarative_base()

engine = None
SessionLocal = None


def create_engine_with_retry(max_retries: int = 30, retry_delay: int = 2):
    """Create database engine with retry logic for container startup."""
    global engine, SessionLocal
    
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Attempting database connection (attempt {attempt}/{max_retries})...")
            
            _engine = create_engine(
                settings.DATABASE_URL,
                pool_pre_ping=True,
                pool_size=10,
                max_overflow=20
            )
            
            with _engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            
            engine = _engine
            SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
            
            logger.info("Database connection established successfully!")
            return engine
            
        except OperationalError as e:
            if attempt < max_retries:
                logger.warning(f"Database connection failed: {e}. Retrying in {retry_delay}s...")
                time.sleep(retry_delay)
            else:
                logger.error(f"Failed to connect to database after {max_retries} attempts")
                raise
        except Exception as e:
            logger.error(f"Unexpected error connecting to database: {e}")
            raise
    
    return None


def get_db():
    """
    Dependency that provides a database session.
    Yields a session and ensures it's closed after use.
    """
    if SessionLocal is None:
        raise RuntimeError("Database not initialized. Call create_engine_with_retry first.")
    
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize the database by creating all tables."""
    if engine is None:
        raise RuntimeError("Database engine not initialized. Call create_engine_with_retry first.")
    
    from app.models import user, company, campaign, email_template, campaign_target, email_task, security_recommendation
    Base.metadata.create_all(bind=engine)
