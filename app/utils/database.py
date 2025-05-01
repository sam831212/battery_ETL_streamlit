"""
Database utility functions for the Battery ETL Dashboard

This module provides database connection and management utilities.
"""
from typing import Optional
from sqlmodel import SQLModel, Session, create_engine
from app.utils.config import DATABASE_URL, DEBUG

# Create database engine
engine = create_engine(DATABASE_URL, echo=DEBUG)


def create_db_and_tables():
    """Create all tables defined in the models if they don't exist"""
    SQLModel.metadata.create_all(engine)


def get_session() -> Session:
    """Get a new database session

    Returns:
        Session: A new SQLModel database session
    """
    return Session(engine)


def init_db():
    """Initialize the database and create tables
    
    This function should be called once at application startup.
    """
    try:
        create_db_and_tables()
        print("Database tables created successfully.")
        return True
    except Exception as e:
        print(f"Error creating database tables: {e}")
        return False


def test_db_connection() -> tuple[bool, Optional[str]]:
    """Test the database connection

    Returns:
        tuple[bool, Optional[str]]: Success status and error message (if any)
    """
    try:
        with get_session() as session:
            # Execute a simple query
            session.execute("SELECT 1")
        return True, None
    except Exception as e:
        error_message = f"Database connection error: {str(e)}"
        return False, error_message