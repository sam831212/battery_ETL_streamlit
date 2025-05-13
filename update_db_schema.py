"""
One-time script to update the database schema to match our models
"""
from app.utils.database import init_db

# Run the database initialization with recreate_tables=True
# This will drop and recreate all tables according to the current models
init_db(recreate_tables=True)