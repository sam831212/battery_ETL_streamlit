"""
Database utility functions for the Battery ETL Dashboard

This module provides database connection and management utilities.
"""
from typing import Optional
from sqlmodel import SQLModel, Session, create_engine
from app.utils.config import DATABASE_URL, DEBUG

# Create database engine with connection pooling settings
# pool_pre_ping: Verify database connectivity before using a connection
# pool_recycle: Recycle connections after 30 minutes (1800 seconds) to avoid stale connections
# connect_args: Set SSL mode to require and keepalives to help maintain connection
engine = create_engine(
    DATABASE_URL, 
    echo=DEBUG,
    pool_pre_ping=True,
    pool_recycle=1800,  # Recycle connections after 30 minutes
    connect_args={
        "keepalives": 1,
        "keepalives_idle": 30,
        "keepalives_interval": 10,
        "keepalives_count": 5
    }
)


def create_db_and_tables():
    """Create all tables defined in the models if they don't exist"""
    try:
        # Set extend_existing=True to update existing tables
        for table in SQLModel.metadata.tables.values():
            table.schema = None  # Ensure no schema is set
            table.extend_existing = True  # Allow extending existing tables
            
        SQLModel.metadata.create_all(engine)
    except Exception as e:
        # Check if the error is about existing tables
        if "Table is already defined" in str(e):
            # This is expected when tables already exist
            pass
        else:
            # This is an unexpected error
            raise e


def get_session() -> Session:
    """Get a new database session with retry logic
    
    This function creates a session with the database engine. If the connection
    is lost due to network issues or idle timeout, it will be recreated.

    Returns:
        Session: A new SQLModel database session
    """
    # The pool_pre_ping=True setting on the engine will verify the connection
    # before using it, so we can simply return a new session
    return Session(engine)


def init_db(recreate_tables=False):
    """Initialize the database and create tables
    
    This function should be called once at application startup.
    
    Args:
        recreate_tables (bool): If True, drop existing tables and recreate them
    """
    try:
        if recreate_tables:
            # Drop all tables and recreate them
            SQLModel.metadata.drop_all(engine)
            print("Database tables dropped successfully.")
        
        # Create tables
        create_db_and_tables()
        print("Database tables created successfully.")
        return True
    except Exception as e:
        print(f"Error creating database tables: {e}")
        return False


def reset_engine_connection():
    """
    Reset the engine's connection pool
    
    This function disposes the current connection pool and creates a fresh one.
    Call this function when you suspect connection issues.
    """
    global engine
    engine.dispose()
    # No need to recreate the engine, as SQLAlchemy will establish new connections as needed


def test_db_connection() -> tuple[bool, Optional[str]]:
    """Test the database connection

    Returns:
        tuple[bool, Optional[str]]: Success status and error message (if any)
    """
    try:
        from sqlalchemy import text
        with get_session() as session:
            # Execute a simple query
            session.execute(text("SELECT 1"))
        return True, None
    except Exception as e:
        # If connection fails, try resetting the connection pool once
        try:
            reset_engine_connection()
            # Try again with a fresh connection
            with get_session() as session:
                session.execute(text("SELECT 1"))
            return True, None
        except Exception as retry_error:
            error_message = f"Database connection error: {str(retry_error)}"
            return False, error_message