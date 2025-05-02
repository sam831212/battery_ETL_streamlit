#!/usr/bin/env python
"""
Setup script for initializing the database migration system
"""
import os
import sys
from pathlib import Path

# Add the parent directory to the path to allow imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.utils.database import engine
from app.utils.migration import init_migration_system, create_migration


def main():
    """Initialize the migration system and create the initial migration"""
    print("Setting up database migration system...")
    
    # Initialize the migration system
    if init_migration_system(engine):
        print("Migration system initialized successfully.")
    else:
        print("Failed to initialize migration system.")
        return 1
    
    # Create the initial migration
    success, message = create_migration(engine, "Initial migration")
    if success:
        print(message)
    else:
        print(f"Error: {message}")
        return 1
    
    print("Migration setup complete. Use the following commands:")
    print("  python -m scripts.migrate upgrade head    # Apply all migrations")
    print("  python -m scripts.migrate downgrade -1    # Rollback one revision")
    print("  python -m scripts.migrate create 'message'# Create a new migration")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())