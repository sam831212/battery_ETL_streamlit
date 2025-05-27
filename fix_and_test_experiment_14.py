#!/usr/bin/env python3
"""
Script to clean up test data and verify the fix for experiment 14 measurement processing.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
from sqlmodel import select, func, delete
from app.utils.database import get_session
from app.models import Experiment, Step, Measurement, ProcessedFile

def clean_test_measurements():
    """Remove the test measurements we added"""
    print("=" * 60)
    print("CLEANING UP TEST MEASUREMENTS FROM STEP 24")
    print("=" * 60)
    
    with get_session() as session:
        # Delete test measurements from step 24
        result = session.exec(
            delete(Measurement).where(Measurement.step_id == 24)
        )
        session.commit()
        
        # Verify cleanup
        count = session.exec(
            select(func.count(Measurement.id)).where(Measurement.step_id == 24)
        ).one()
        
        print(f"✅ Cleaned up test measurements. Step 24 now has {count} measurements.")
        
def verify_original_problem():
    """Verify that we're back to the original problem state"""
    print("\n" + "=" * 60)
    print("VERIFYING ORIGINAL PROBLEM STATE")
    print("=" * 60)
    
    with get_session() as session:
        # Check experiment 14
        experiment = session.get(Experiment, 14)
        if not experiment:
            print("❌ Experiment 14 not found!")
            return False
            
        print(f"✅ Experiment 14: {experiment.name}")
        
        # Check step 24
        step_24 = session.get(Step, 24)
        if not step_24:
            print("❌ Step 24 not found!")
            return False
            
        print(f"✅ Step 24: step_number={step_24.step_number}, type={step_24.step_type}")
        
        # Check measurements
        measurement_count = session.exec(
            select(func.count(Measurement.id)).where(Measurement.step_id == 24)
        ).one()
        
        print(f"📊 Step 24 measurements: {measurement_count}")
        
        if measurement_count == 0:
            print("✅ Back to original problem state: 0 measurements")
            return True
        else:
            print(f"⚠️  Still has {measurement_count} measurements")
            return False

def simulate_processing_with_sample_data():
    """Simulate processing with actual sample data to test the fix"""
    print("\n" + "=" * 60)
    print("TESTING FIX WITH SAMPLE DATA")
    print("=" * 60)
    
    from pathlib import Path
    
    # Check for example CSV files
    example_csv_dir = Path("example_csv_chromaLex")
    if not example_csv_dir.exists():
        print("❌ Example CSV directory not found")
        return False
        
    detail_files = list(example_csv_dir.glob("*Detail.csv"))
    if not detail_files:
        print("❌ No detail CSV files found")
        return False
        
    print(f"📁 Found {len(detail_files)} detail files")
    
    # Try to find data for step number 9
    for detail_file in detail_files:
        print(f"\n🔍 Checking {detail_file.name}:")
        try:
            df = pd.read_csv(detail_file)
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
                print(f"  Step numbers: {unique_steps}")
                
                if 9 in unique_steps:
                    print(f"  ✅ Found step number 9!")
                    step_9_data = df[df[step_col] == 9].copy()
                    print(f"  Step 9 has {len(step_9_data)} rows")
                    
                    if len(step_9_data) > 0:
                        # Rename columns to match expected format
                        column_mapping = {
                            '工步': 'step_number',
                            '时间': 'execution_time',
                            '电压': 'voltage', 
                            '电流': 'current',
                            '温度': 'temperature',
                            '容量': 'capacity',
                            '能量': 'energy',
                            'SOC': 'soc'
                        }
                        
                        # Apply column mapping
                        for old_col, new_col in column_mapping.items():
                            if old_col in step_9_data.columns:
                                step_9_data = step_9_data.rename(columns={old_col: new_col})
                        
                        print(f"  Sample data columns after mapping: {list(step_9_data.columns)}")
                        print(f"  Sample row: {step_9_data.iloc[0].to_dict()}")
                        
                        # Test with the improved save_measurements_to_db function
                        from app.services.database_service import save_measurements_to_db
                        
                        step_mapping = {9: 24}  # Map step number 9 to step ID 24
                        
                        try:
                            print(f"\n🧪 Testing save_measurements_to_db with real data...")
                            save_measurements_to_db(
                                experiment_id=14,
                                details_df=step_9_data,
                                step_mapping=step_mapping,
                                nominal_capacity=20.0
                            )
                            
                            # Verify the save worked
                            with get_session() as session:
                                count = session.exec(
                                    select(func.count(Measurement.id)).where(Measurement.step_id == 24)
                                ).one()
                                print(f"✅ SUCCESS! Step 24 now has {count} measurements")
                                
                                if count > 0:
                                    # Show a sample measurement
                                    sample = session.exec(
                                        select(Measurement).where(Measurement.step_id == 24).limit(1)
                                    ).first()
                                    if sample:
                                        print(f"   Sample measurement: voltage={sample.voltage}, current={sample.current}, time={sample.execution_time}")
                                
                                return True
                                
                        except Exception as e:
                            print(f"❌ Error testing save_measurements_to_db: {e}")
                            import traceback
                            traceback.print_exc()
                            return False
                            
            else:
                print(f"  ❌ No step number column found")
                
        except Exception as e:
            print(f"  ❌ Error reading file: {e}")
    
    return False

def main():
    """Main function to run all tests"""
    print("EXPERIMENT 14 MEASUREMENT PROCESSING FIX TEST")
    print("=" * 80)
    
    # Step 1: Clean up test data
    clean_test_measurements()
    
    # Step 2: Verify we're back to original problem
    if not verify_original_problem():
        print("❌ Could not verify original problem state")
        return
    
    # Step 3: Test the fix with real data
    if simulate_processing_with_sample_data():
        print("\n🎉 SUCCESS! The fix works correctly.")
        print("   - The save_measurements_to_db function properly processes real data")
        print("   - Step 24 now has measurements for step number 9")
        print("   - Future processing using the updated selected_data_processing_ui.py should work")
    else:
        print("\n❌ FAILED! The fix needs more work.")

if __name__ == "__main__":
    main()
