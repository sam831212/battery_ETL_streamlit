#!/usr/bin/env python
"""
Database initialization script for Battery ETL Dashboard
"""
import os
import sys
from pathlib import Path

# Add the parent directory to the path to allow imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.utils.database import init_db, test_db_connection, engine
from app.utils.migration import init_migration_system, create_migration
from app.utils.config import DATABASE_URL

def main():
    """Initialize the database and migration system"""
    print("Initializing database...")
    
    # Test database connection
    success, error = test_db_connection()
    if not success:
        print(f"Error connecting to database: {error}")
        print("\nPlease ensure PostgreSQL is installed and running.")
        print("You can download PostgreSQL from: https://www.postgresql.org/download/windows/")
        print("\nAfter installation, please set the following environment variables:")
        print("PGHOST=localhost")
        print("PGPORT=5432")
        print("PGDATABASE=battery_db")
        print("PGUSER=postgres")
        print("PGPASSWORD=your_password")
        return 1
    
    print("Database connection successful!")
    
    # Initialize database tables
    if init_db():
        print("Database tables created successfully!")
    else:
        print("Error creating database tables!")
        return 1
    
    # Initialize migration system
    print("\nSetting up database migration system...")
    if init_migration_system(engine):
        print("Migration system initialized successfully!")
        
        # Create initial migration
        success, message = create_migration(engine, "Initial migration")
        if success:
            print(message)
        else:
            print(f"Error creating initial migration: {message}")
            return 1
    else:
        print("Error initializing migration system!")
        return 1
    
    print("\nDatabase initialization complete!")
    print("\nYou can now use the following commands:")
    print("  python -m scripts.migrate upgrade head    # Apply all migrations")
    print("  python -m scripts.migrate downgrade -1    # Rollback one revision")
    print("  python -m scripts.migrate create 'message'# Create a new migration")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 