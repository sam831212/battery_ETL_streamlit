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
from app.utils.config import DATABASE_URL, DB_PATH
from sqlmodel import SQLModel

target_metadata = SQLModel.metadata

def main():
    """Initialize the database and migration system"""
    print("Initializing database...")
    
    # 確保資料庫目錄存在
    db_dir = os.path.dirname(DB_PATH)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir)
    
    # Test database connection
    if not test_db_connection():
        print(f"Error connecting to database")
        print("\nPlease check your database configuration:")
        print(f"DB_PATH: {DB_PATH}")
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
    try:
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
    except Exception as e:
        print(f"Error during migration setup: {str(e)}")
        return 1
    
    print("\nDatabase initialization complete!")
    print(f"\nDatabase file created at: {os.path.abspath(DB_PATH)}")
    print("\nYou can now use the following commands:")
    print("  python -m scripts.migrate upgrade head    # Apply all migrations")
    print("  python -m scripts.migrate downgrade -1    # Rollback one revision")
    print("  python -m scripts.migrate create 'message'# Create a new migration")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 