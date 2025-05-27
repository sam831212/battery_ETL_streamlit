#!/usr/bin/env python3
"""
Debug script to investigate experiment 18 and why measurements aren't being saved.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
from sqlmodel import select, func
from app.utils.database import get_session
from app.models import Experiment, Step, Measurement, ProcessedFile

def debug_experiment_18():
    """Debug experiment 18 specifically"""
    print("=" * 80)
    print("DEBUGGING EXPERIMENT 18 - MEASUREMENT SAVING ISSUE")
    print("=" * 80)
    
    with get_session() as session:
        # Get experiment 18
        experiment = session.get(Experiment, 18)
        if not experiment:
            print("❌ EXPERIMENT 18 NOT FOUND!")
            return
            
        print(f"✅ EXPERIMENT 18 FOUND:")
        print(f"   Name: {experiment.name}")
        print(f"   Start Date: {experiment.start_date}")
        print(f"   Battery Type: {experiment.battery_type}")
        print(f"   Nominal Capacity: {experiment.nominal_capacity}")
        print()
        
        # Get all steps for experiment 18
        steps = session.exec(
            select(Step).where(Step.experiment_id == 18).order_by(Step.step_number)
        ).all()
        
        print(f"📊 STEPS IN EXPERIMENT 18: {len(steps)}")
        print("=" * 50)
        
        for step in steps:
            measurement_count = session.exec(
                select(func.count(Measurement.id)).where(Measurement.step_id == step.id)
            ).one()
            
            print(f"Step ID: {step.id:3d} | Step Number: {step.step_number:3d} | Type: {step.step_type:15s} | Measurements: {measurement_count:3d}")
            print(f"    Start Time: {step.start_time}")
            print(f"    End Time: {step.end_time}")
            print(f"    Duration: {step.duration}")
            print(f"    Current: {step.current}")
            print(f"    Data Meta Keys: {list(step.data_meta.keys()) if step.data_meta else 'None'}")
            print()
                
        # Get processed files for experiment 18
        processed_files = session.exec(
            select(ProcessedFile).where(ProcessedFile.experiment_id == 18)
        ).all()
        
        print(f"\n📁 PROCESSED FILES FOR EXPERIMENT 18: {len(processed_files)}")
        print("=" * 50)
        
        for pf in processed_files:
            print(f"File: {pf.filename}")
            print(f"  Type: {pf.file_type}")
            print(f"  Hash: {pf.file_hash}")
            print(f"  Row Count: {pf.row_count}")
            print(f"  Metadata: {pf.data_meta}")
            print()

def test_measurement_saving_for_step_28():
    """Test if we can manually save measurements to step 28"""
    print("\n🧪 TESTING MEASUREMENT SAVING FOR STEP 28:")
    print("=" * 50)
    
    from app.services.database_service import save_measurements_to_db
    
    # Create test data for step number 21 (which maps to step ID 28)
    test_data = {
        'step_number': [21] * 10,
        'execution_time': [i * 10.0 for i in range(10)],
        'voltage': [4.0 - i * 0.1 for i in range(10)],
        'current': [-2.0] * 10,
        'temperature': [25.0 + i * 0.1 for i in range(10)],
        'capacity': [i * 0.5 for i in range(10)],
        'energy': [i * 1.0 for i in range(10)],
        'soc': [100.0 - i * 10.0 for i in range(10)]
    }
    
    test_df = pd.DataFrame(test_data)
    step_mapping = {21: 28}  # Map step number 21 to step ID 28
    
    print(f"Test data created:")
    print(f"  DataFrame shape: {test_df.shape}")
    print(f"  Step mapping: {step_mapping}")
    print(f"  Sample data:\n{test_df.head()}")
    
    try:
        save_measurements_to_db(
            experiment_id=18,
            details_df=test_df,
            step_mapping=step_mapping,
            nominal_capacity=20.0
        )
        print("✅ save_measurements_to_db completed successfully")
        
        # Check if measurements were actually saved
        with get_session() as session:
            count = session.exec(
                select(func.count(Measurement.id)).where(Measurement.step_id == 28)
            ).one()
            print(f"✅ Step 28 now has {count} measurements")
            
    except Exception as e:
        print(f"❌ save_measurements_to_db failed: {e}")
        import traceback
        traceback.print_exc()

def check_session_state_data():
    """Check if there's any session state data that might give us clues"""
    print("\n🔍 CHECKING FOR SESSION STATE CLUES:")
    print("=" * 50)
    
    # Look for any temporary files or session data
    import glob
    temp_files = glob.glob("temp_*") + glob.glob("session_*") + glob.glob("*_temp_*")
    
    if temp_files:
        print(f"Found temporary files: {temp_files}")
    else:
        print("No temporary files found")

if __name__ == "__main__":
    debug_experiment_18()
    test_measurement_saving_for_step_28()
    check_session_state_data()
