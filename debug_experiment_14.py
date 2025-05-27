#!/usr/bin/env python3
"""
Debug script to specifically investigate experiment 14 and why step 24 (step_number 9) has no measurements.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
from sqlmodel import select, func
from app.utils.database import get_session
from app.models import Experiment, Step, Measurement, ProcessedFile

def debug_experiment_14():
    """Debug experiment 14 specifically"""
    print("=" * 80)
    print("DEBUGGING EXPERIMENT 14 - STEP 24 (step_number 9) MEASUREMENT ISSUE")
    print("=" * 80)
    
    with get_session() as session:
        # Get experiment 14
        experiment = session.get(Experiment, 14)
        if not experiment:
            print("❌ EXPERIMENT 14 NOT FOUND!")
            return
            
        print(f"✅ EXPERIMENT 14 FOUND:")
        print(f"   Name: {experiment.name}")
        print(f"   Start Date: {experiment.start_date}")
        print(f"   Battery Type: {experiment.battery_type}")
        print(f"   Nominal Capacity: {experiment.nominal_capacity}")
        print()
        
        # Get all steps for experiment 14
        steps = session.exec(
            select(Step).where(Step.experiment_id == 14).order_by(Step.step_number)
        ).all()
        
        print(f"📊 STEPS IN EXPERIMENT 14: {len(steps)}")
        print("=" * 50)
        
        step_24_found = False
        for step in steps:
            measurement_count = session.exec(
                select(func.count(Measurement.id)).where(Measurement.step_id == step.id)
            ).one()
            
            print(f"Step ID: {step.id:3d} | Step Number: {step.step_number:3d} | Type: {step.step_type:15s} | Measurements: {measurement_count:3d}")
            
            if step.id == 24:
                step_24_found = True
                print(f"    👆 THIS IS THE PROBLEMATIC STEP (ID: 24, step_number: {step.step_number})")
                print(f"    Step Type: {step.step_type}")
                print(f"    Start Time: {step.start_time}")
                print(f"    End Time: {step.end_time}")
                print(f"    Duration: {step.duration}")
                print(f"    Current: {step.current}")
                print(f"    Voltage Start: {step.voltage_start}")
                print(f"    Voltage End: {step.voltage_end}")
                
        print("=" * 50)
        
        if not step_24_found:
            print("❌ STEP 24 NOT FOUND!")
            return
            
        # Get processed files for experiment 14
        processed_files = session.exec(
            select(ProcessedFile).where(ProcessedFile.experiment_id == 14)
        ).all()
        
        print(f"\n📁 PROCESSED FILES FOR EXPERIMENT 14: {len(processed_files)}")
        print("=" * 50)
        
        detail_file = None
        step_file = None
        
        for pf in processed_files:
            print(f"File: {pf.filename}")
            print(f"  Type: {pf.file_type}")
            print(f"  Hash: {pf.file_hash}")
            print(f"  Row Count: {pf.row_count}")
            print(f"  Metadata: {pf.data_meta}")
            print()
            
            if pf.file_type == "detail":
                detail_file = pf
            elif pf.file_type == "step":
                step_file = pf
        
        # Try to find the original CSV files if they exist
        print("\n🔍 INVESTIGATING ORIGINAL CSV DATA:")
        print("=" * 50)
        
        if detail_file:
            print(f"Detail file was processed: {detail_file.filename}")
            print(f"Detail file had {detail_file.row_count} rows")
            
            # Try to find the actual file in the upload folder or temp files
            from pathlib import Path
            
            # Check example CSV files
            example_csv_dir = Path("example_csv_chromaLex")
            if example_csv_dir.exists():
                detail_files = list(example_csv_dir.glob("*Detail.csv"))
                print(f"\nFound example detail files: {[f.name for f in detail_files]}")
                
                # Check the first detail file to see what step numbers it contains
                if detail_files:
                    for detail_csv in detail_files:
                        print(f"\n📋 CHECKING {detail_csv.name}:")
                        try:
                            df = pd.read_csv(detail_csv)
                            print(f"  Columns: {list(df.columns)}")
                            
                            # Look for step number column
                            step_col = None
                            possible_step_cols = ['step_number', '工步', 'Step', 'step']
                            for col in possible_step_cols:
                                if col in df.columns:
                                    step_col = col
                                    break
                                    
                            if step_col:
                                unique_steps = sorted(df[step_col].unique())
                                print(f"  Step numbers in file: {unique_steps}")
                                
                                # Check if step number 9 exists
                                if 9 in unique_steps:
                                    print(f"  ✅ Step number 9 EXISTS in {detail_csv.name}")
                                    step_9_rows = df[df[step_col] == 9]
                                    print(f"  Step 9 has {len(step_9_rows)} rows")
                                    if len(step_9_rows) > 0:
                                        print(f"  Sample row: {step_9_rows.iloc[0].to_dict()}")
                                else:
                                    print(f"  ❌ Step number 9 NOT FOUND in {detail_csv.name}")
                            else:
                                print(f"  ❌ No step number column found")
                                
                        except Exception as e:
                            print(f"  ❌ Error reading {detail_csv.name}: {e}")

def test_save_measurements_function():
    """Test the save_measurements_to_db function with fake data"""
    print("\n\n🧪 TESTING save_measurements_to_db FUNCTION:")
    print("=" * 50)
    
    from app.services.database_service import save_measurements_to_db
    
    # Create fake detail data for step number 9
    fake_detail_data = {
        'step_number': [9, 9, 9, 9, 9],
        'execution_time': [0.0, 1.0, 2.0, 3.0, 4.0],
        'voltage': [3.7, 3.6, 3.5, 3.4, 3.3],
        'current': [-2.0, -2.0, -2.0, -2.0, -2.0],
        'temperature': [25.0, 25.1, 25.2, 25.3, 25.4],
        'capacity': [0.0, 0.5, 1.0, 1.5, 2.0],
        'energy': [0.0, 1.0, 2.0, 3.0, 4.0],
        'soc': [100.0, 90.0, 80.0, 70.0, 60.0]
    }
    
    fake_df = pd.DataFrame(fake_detail_data)
    fake_step_mapping = {9: 24}  # Map step number 9 to step ID 24
    
    print(f"Fake data created:")
    print(f"  DataFrame shape: {fake_df.shape}")
    print(f"  Step mapping: {fake_step_mapping}")
    print(f"  Sample data:\n{fake_df.head()}")
    
    try:
        save_measurements_to_db(
            experiment_id=14,
            details_df=fake_df,
            step_mapping=fake_step_mapping,
            nominal_capacity=20.0
        )
        print("✅ save_measurements_to_db completed successfully")
        
        # Check if measurements were actually saved
        with get_session() as session:
            count = session.exec(
                select(func.count(Measurement.id)).where(Measurement.step_id == 24)
            ).one()
            print(f"✅ Step 24 now has {count} measurements")
            
    except Exception as e:
        print(f"❌ save_measurements_to_db failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_experiment_14()
    test_save_measurements_function()
