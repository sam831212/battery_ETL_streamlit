#!/usr/bin/env python
"""
Script to update the database schema with the new columns
"""
import os
import sys
from pathlib import Path

# Add the parent directory to the path to allow imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.utils.database import engine, get_session


def add_columns_if_not_exist():
    """Add new columns to existing tables if they don't exist"""
    print("Checking and updating database schema...")
    
    # List of tables and their new columns to check/add
    schema_updates = [
        {
            "table": "experiment",
            "columns": [
                {"name": "cell_id", "type": "INTEGER", "fk": "cell(id)"},
                {"name": "machine_id", "type": "INTEGER", "fk": "machine(id)"}
            ]
        }
    ]
    
    with get_session() as session:
        # For each table in our update list
        for table_info in schema_updates:
            table_name = table_info["table"]
            print(f"Checking table: {table_name}")
            
            # Get existing columns for this table
            result = session.execute(text(f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table_name}'"))
            existing_columns = [row[0] for row in result]
            
            # Check each column that should be added
            for column in table_info["columns"]:
                column_name = column["name"]
                column_type = column["type"]
                
                if column_name not in existing_columns:
                    print(f"  Adding column: {column_name}")
                    
                    # Construct and execute ALTER TABLE command
                    alter_cmd = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
                    session.execute(text(alter_cmd))
                    
                    # If there's a foreign key, add it
                    if "fk" in column:
                        constraint_name = f"fk_{table_name}_{column_name}"
                        fk_cmd = f"ALTER TABLE {table_name} ADD CONSTRAINT {constraint_name} FOREIGN KEY ({column_name}) REFERENCES {column['fk']}"
                        session.execute(text(fk_cmd))
                else:
                    print(f"  Column already exists: {column_name}")
        
        # Commit the transaction
        session.commit()
    
    print("Schema update complete.")


def create_new_tables():
    """Create the new tables if they don't exist"""
    from app.models.database import Cell, Machine, SavedView
    from sqlmodel import SQLModel
    
    print("Creating new tables...")
    
    # Get a list of existing tables
    with get_session() as session:
        result = session.execute(text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'"))
        existing_tables = [row[0] for row in result]
    
    # Create each table if it doesn't exist
    tables_to_create = {
        "cell": Cell,
        "machine": Machine,
        "savedview": SavedView
    }
    
    for table_name, model in tables_to_create.items():
        if table_name not in existing_tables:
            print(f"Creating table: {table_name}")
            # Create just this table
            if hasattr(model, "__table__"):
                model.__table__.create(engine)
            else:
                # Create table from metadata
                SQLModel.metadata.create_all(engine, tables=[model.__tablename__])
        else:
            print(f"Table already exists: {table_name}")


def main():
    """Update the database schema"""
    try:
        create_new_tables()
        add_columns_if_not_exist()
        print("Database schema update successful.")
        return 0
    except Exception as e:
        print(f"Error updating database schema: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())