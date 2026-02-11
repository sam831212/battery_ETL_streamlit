"""
Script to update the Measurement table schema to add execution_time field
"""
from sqlalchemy import create_engine, Column, Float, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import inspect
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get database URL from environment variables
database_url = os.getenv("DATABASE_URL")
if not database_url:
    raise ValueError("DATABASE_URL not found in environment variables")

# Create engine
engine = create_engine(database_url)

# Create inspector to check if column exists
inspector = inspect(engine)

# Check if execution_time column already exists in the measurement table
columns = [col['name'] for col in inspector.get_columns('measurement')]
if 'execution_time' not in columns:
    print("Adding execution_time column to measurement table...")
    with engine.begin() as conn:
        conn.execute(text('ALTER TABLE measurement ADD COLUMN execution_time FLOAT'))
    print("Column added successfully!")
else:
    print("execution_time column already exists in measurement table.")

print("Schema update completed.")