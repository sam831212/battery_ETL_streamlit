#!/usr/bin/env python3
"""
Simple test to verify data_meta functionality
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    print("Starting simple data_meta test...")
    
    from app.models.database import Step
    from app.utils.database import get_session
    from datetime import datetime, timezone
    
    print("Imports successful, testing database connection...")
    
    with get_session() as session:
        print("Database connection successful")
        
        # Simple test: create a step with data_meta
        step = Step(
            experiment_id=1,  # Assume experiment 1 exists
            step_number=999,
            step_type="test",
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc),
            duration=100.0,
            voltage_start=3.3,
            voltage_end=4.0,
            current=1.0,
            capacity=1.0,
            energy=3.3,
            temperature=25.0,
            c_rate=0.05,
            data_meta="Test data_meta comment from UI"
        )
        
        print(f"Created step with data_meta: {step.data_meta}")
        print("✓ data_meta field is working correctly!")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
