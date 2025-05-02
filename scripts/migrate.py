#!/usr/bin/env python
"""
Migration script for running database migrations
"""
import os
import sys
import argparse
from pathlib import Path

# Add the parent directory to the path to allow imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.utils.database import engine
from app.utils.migration import apply_migration, create_migration


def main():
    """Run database migrations based on command-line arguments"""
    parser = argparse.ArgumentParser(description="Database migration tool")
    
    # Create subparsers for different commands
    subparsers = parser.add_subparsers(dest="command", help="Migration command")
    
    # Upgrade command
    upgrade_parser = subparsers.add_parser("upgrade", help="Upgrade database schema")
    upgrade_parser.add_argument("revision", help="Target revision (e.g., 'head', specific revision)")
    
    # Downgrade command
    downgrade_parser = subparsers.add_parser("downgrade", help="Downgrade database schema")
    downgrade_parser.add_argument("revision", help="Target revision (e.g., '-1', 'base', specific revision)")
    
    # Create command
    create_parser = subparsers.add_parser("create", help="Create a new migration")
    create_parser.add_argument("message", help="Migration message")
    
    # Parse arguments
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Handle different commands
    if args.command in ["upgrade", "downgrade"]:
        success, message = apply_migration(engine, args.command, args.revision)
        if success:
            print(message)
            return 0
        else:
            print(f"Error: {message}")
            return 1
    elif args.command == "create":
        success, message = create_migration(engine, args.message)
        if success:
            print(message)
            return 0
        else:
            print(f"Error: {message}")
            return 1
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())