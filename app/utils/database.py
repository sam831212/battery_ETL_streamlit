"""
Database utility functions for the Battery ETL Dashboard

This module provides database connection and management utilities for SQLite.
"""
from typing import Optional
from sqlmodel import SQLModel, Session, create_engine
from sqlalchemy import text
from app.utils.config import DATABASE_URL, DEBUG

# Create SQLite database engine with appropriate settings
engine = create_engine(
    DATABASE_URL,
    echo=DEBUG,
    connect_args={"check_same_thread": False}  # SQLite-specific setting for multi-threading
)


def create_db_and_tables():
    """Create all tables defined in the models if they don't exist"""
    try:
        # Since we're using SQLite, no schema management is needed
        SQLModel.metadata.create_all(engine)
    except Exception as e:
        if "Table is already defined" in str(e):
            # Table already exists in SQLite
            pass
        else:
            raise e


def get_session() -> Session:
    """Get a new database session

    Returns:
        Session: A new SQLite database session
    """
    return Session(engine)


def init_db(recreate_tables: bool = False) -> bool:
    """Initialize the SQLite database

    Args:
        recreate_tables: If True, will drop and recreate all tables

    Returns:
        bool: True if initialization was successful
    """
    try:
        if recreate_tables:
            SQLModel.metadata.drop_all(engine)
        create_db_and_tables()
        return True
    except Exception as e:
        print(f"Error initializing database: {e}")
        return False


def test_db_connection() -> tuple[bool, Optional[str]]:
    """Test the SQLite database connection

    Returns:
        tuple[bool, Optional[str]]: (success, error_message)
    """
    try:
        # For SQLite, we just need to check if we can create a session and execute a query
        with get_session() as session:
            session.execute(text("SELECT 1"))
        return True, None
    except Exception as e:
        return False, str(e)