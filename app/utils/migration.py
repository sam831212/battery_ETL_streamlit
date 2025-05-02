"""
Database migration utilities for the Battery ETL Dashboard

This module provides utilities for managing database migrations using Alembic.
"""
import os
from pathlib import Path
from typing import Tuple, Optional
from sqlalchemy.engine import Engine
from alembic import command
from alembic.config import Config


def create_alembic_config(engine: Engine) -> Config:
    """
    Create an Alembic configuration object
    
    Args:
        engine: SQLAlchemy database engine
        
    Returns:
        Alembic Config object
    """
    # Get the base directory of the application
    base_dir = Path(__file__).parent.parent.parent
    
    # Create Alembic configuration
    config = Config(os.path.join(base_dir, "alembic.ini"))
    
    # Set the script location
    config.set_main_option("script_location", os.path.join(base_dir, "migrations"))
    
    # Get connection details from environment variables for Replit
    # This ensures we use the correct database URL with proper credentials
    from app.utils.config import DATABASE_URL
    
    # Set the SQLAlchemy URL to our configured DATABASE_URL
    config.set_main_option("sqlalchemy.url", DATABASE_URL)
    
    return config


def init_migration_system(engine: Engine) -> bool:
    """
    Initialize the migration system with Alembic
    
    Args:
        engine: SQLAlchemy database engine
        
    Returns:
        bool: True if initialization was successful, False otherwise
    """
    try:
        # Create Alembic configuration
        config = create_alembic_config(engine)
        
        # Initialize Alembic environment
        command.init(config, "migrations")
        
        return True
    except Exception as e:
        print(f"Error initializing migration system: {e}")
        return False


def apply_migration(engine: Engine, operation: str, revision: str) -> Tuple[bool, str]:
    """
    Apply a database migration
    
    Args:
        engine: SQLAlchemy database engine
        operation: Migration operation (upgrade, downgrade)
        revision: Target revision (e.g., 'head', 'base', specific revision ID)
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        # Create Alembic configuration
        config = create_alembic_config(engine)
        
        # Apply migration
        if operation == "upgrade":
            command.upgrade(config, revision)
        elif operation == "downgrade":
            command.downgrade(config, revision)
        else:
            return False, f"Unknown operation: {operation}"
        
        return True, f"Successfully applied migration {operation} to {revision}"
    except Exception as e:
        return False, f"Migration failed: {str(e)}"


def create_migration(engine: Engine, message: str) -> Tuple[bool, str]:
    """
    Create a new migration
    
    Args:
        engine: SQLAlchemy database engine
        message: Migration message/description
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        # Create Alembic configuration
        config = create_alembic_config(engine)
        
        # Create migration
        command.revision(config, message=message, autogenerate=True)
        
        return True, f"Successfully created migration: {message}"
    except Exception as e:
        return False, f"Failed to create migration: {str(e)}"