#!/usr/bin/env python
"""
Database setup and test script for Battery ETL Dashboard
"""
import os
import sys
import time
from pathlib import Path
import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv

# Add the parent directory to the path to allow imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.utils.database import init_db, test_db_connection, engine
from app.utils.migration import init_migration_system, create_migration
from app.utils.config import DATABASE_URL, DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT

def test_postgres_connection():
    """Test PostgreSQL connection without using SQLAlchemy"""
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        conn.close()
        return True, None
    except Exception as e:
        return False, str(e)

def create_database():
    """Create database if it doesn't exist"""
    try:
        # Connect to default postgres database
        conn = psycopg2.connect(
            dbname="postgres",
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Check if database exists
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (DB_NAME,))
        exists = cursor.fetchone()
        
        if not exists:
            # Create database
            cursor.execute(sql.SQL("CREATE DATABASE {}").format(
                sql.Identifier(DB_NAME)
            ))
            print(f"Database '{DB_NAME}' created successfully!")
        else:
            print(f"Database '{DB_NAME}' already exists.")
        
        cursor.close()
        conn.close()
        return True, None
    except Exception as e:
        return False, str(e)

def setup_database():
    """Main function to setup and test database"""
    print("=== BatteryETL Database Setup ===")
    
    # 1. Test PostgreSQL connection
    print("\n1. Testing PostgreSQL connection...")
    success, error = test_postgres_connection()
    if not success:
        print(f"Error connecting to PostgreSQL: {error}")
        print("\nPlease check your PostgreSQL installation and environment variables:")
        print(f"DB_HOST: {DB_HOST}")
        print(f"DB_PORT: {DB_PORT}")
        print(f"DB_NAME: {DB_NAME}")
        print(f"DB_USER: {DB_USER}")
        print("DB_PASSWORD: [hidden]")
        return False
    print("PostgreSQL connection successful!")
    
    # 2. Create database if not exists
    print("\n2. Creating database if not exists...")
    success, error = create_database()
    if not success:
        print(f"Error creating database: {error}")
        return False
    
    # 3. Test SQLAlchemy connection
    print("\n3. Testing SQLAlchemy connection...")
    success, error = test_db_connection()
    if not success:
        print(f"Error connecting to database: {error}")
        return False
    print("SQLAlchemy connection successful!")
    
    # 4. Initialize database tables
    print("\n4. Initializing database tables...")
    if init_db():
        print("Database tables created successfully!")
    else:
        print("Error creating database tables!")
        return False
    
    # 5. Setup migration system
    print("\n5. Setting up migration system...")
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

def test_database_operations():
    """Test basic database operations"""
    print("\n=== Testing Database Operations ===")
    
    from app.models.database import Cell
    from sqlmodel import Session, select
    
    try:
        # Create a test cell
        with Session(engine) as session:
            test_cell = Cell(
                name="Test Cell",
                manufacturer="Test Manufacturer",
                chemistry="NMC",
                capacity=1000,
                form="PRISMATIC",
                nominal_capacity=1000,
                nominal_voltage=3.7,
                form_factor="PRISMATIC",
                serial_number="TEST123",
                date_received="2024-01-01",
                notes="Test Notes"
            )
            session.add(test_cell)
            session.commit()
            print("✓ Test cell created successfully")
            
            # Query the test cell
            statement = select(Cell).where(Cell.name == "Test Cell")
            result = session.exec(statement).first()
            if result:
                print("✓ Test cell queried successfully")
                
                # Delete the test cell
                session.delete(result)
                session.commit()
                print("✓ Test cell deleted successfully")
            else:
                print("✗ Failed to query test cell")
                return False
    except Exception as e:
        print(f"✗ Error during database operations test: {e}")
        return False
    
    print("=== Database Operations Test Complete ===")
    return True

if __name__ == "__main__":
    # Load environment variables
    load_dotenv()
    
    # Setup database
    if setup_database():
        # Test database operations
        if test_database_operations():
            print("\nAll tests passed successfully!")
            sys.exit(0)
        else:
            print("\nDatabase operations test failed!")
            sys.exit(1)
    else:
        print("\nDatabase setup failed!")
        sys.exit(1) 