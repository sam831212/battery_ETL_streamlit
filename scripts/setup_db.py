#!/usr/bin/env python
"""
Database setup and test script for Battery ETL Dashboard
"""
import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

# Add the parent directory to the path to allow imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.utils.database import init_db, test_db_connection, engine
from app.utils.migration import init_migration_system, create_migration
from app.utils.config import DATABASE_URL, DB_PATH

def setup_database():
    """Main function to setup and test database"""
    print("=== BatteryETL Database Setup ===")
    
    # 1. Test database connection
    print("\n1. Testing database connection...")
    success, error = test_db_connection()
    if not success:
        print(f"Error connecting to database: {error}")
        print("\nPlease check your database configuration:")
        print(f"DB_PATH: {DB_PATH}")
        return False
    print("Database connection successful!")
    
    # 2. Initialize database tables
    print("\n2. Initializing database tables...")
    if init_db():
        print("Database tables created successfully!")
    else:
        print("Error creating database tables!")
        return False
    
    # 3. Setup migration system
    print("\n3. Setting up migration system...")
    if init_migration_system(engine):
        print("Migration system initialized successfully!")
        
        # Create initial migration
        success, message = create_migration(engine, "Initial migration")
        if success:
            print(message)
        else:
            print(f"Error creating initial migration: {message}")
            return False
    else:
        print("Migration system already exists, skipping initialization.")
    
    print("\n=== Database Setup Complete ===")
    print("\nYou can now use the following commands:")
    print("  python -m scripts.migrate upgrade head    # Apply all migrations")
    print("  python -m scripts.migrate downgrade -1    # Rollback one revision")
    print("  python -m scripts.migrate create 'message'# Create a new migration")
    
    return True

if __name__ == "__main__":
    # Load environment variables
    load_dotenv()
    
    # Setup database
    if setup_database():
        print("\nAll tests passed successfully!")
        sys.exit(0)
    else:
        print("\nDatabase setup failed!")
        sys.exit(1) 