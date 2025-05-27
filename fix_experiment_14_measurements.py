#!/usr/bin/env python3
"""
Fix script to re-process and save measurements for experiment 14.
This script will extract the detail data for step 9 and save it to the database.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
from sqlmodel import select, func
from app.utils.database import get_session
from app.models import Experiment, Step, Measurement, ProcessedFile
from app.services.database_service import save_measurements_to_db
from pathlib import Path

def fix_experiment_14_measurements():
    """Fix missing measurements for experiment 14, step 24 (step_number 9)"""
    print("=" * 80)
    print("FIXING EXPERIMENT 14 - MISSING MEASUREMENTS FOR STEP 24 (step_number 9)")
    print("=" * 80)
    
    with get_session() as session:
        # Get experiment 14
        experiment = session.get(Experiment, 14)
        if not experiment:
            print("❌ EXPERIMENT 14 NOT FOUND!")
            return False
            
        print(f"✅ FOUND EXPERIMENT 14: {experiment.name}")
        
        # Get step 24 (step_number 9)
        step_24 = session.get(Step, 24)
        if not step_24:
            print("❌ STEP 24 NOT FOUND!")
            return False
            
        print(f"✅ FOUND STEP 24: step_number={step_24.step_number}, type={step_24.step_type}")
        
        # Check current measurement count
        current_count = session.exec(
            select(func.count(Measurement.id)).where(Measurement.step_id == 24)
        ).one()
        print(f"📊 CURRENT MEASUREMENT COUNT FOR STEP 24: {current_count}")
        
        if current_count > 0:
            print(f"⚠️  Step 24 already has {current_count} measurements. Proceeding to add more...")
        
        # Find the most likely CSV file based on experiment metadata
        example_csv_dir = Path("example_csv_chromaLex")
        if not example_csv_dir.exists():
            print("❌ EXAMPLE CSV DIRECTORY NOT FOUND!")
            return False
            
        # Look for CSV files that contain step 9 discharge data
        detail_files = list(example_csv_dir.glob("*Detail.csv"))
        print(f"📁 FOUND {len(detail_files)} DETAIL FILES")
        
        best_candidate = None
        max_step_9_rows = 0
        
        # Find the file with the most step 9 discharge data
        for detail_file in detail_files:
            try:
                df = pd.read_csv(detail_file)
                
                # Look for step number column (Chinese CSV files use '工步')
                step_col = '工步' if '工步' in df.columns else 'step_number'
                
                if step_col in df.columns:
                    # Filter for step 9
                    step_9_data = df[df[step_col] == 9]
                    
                    # Check if it's discharge data (look for negative current or discharge type)
                    if len(step_9_data) > 0:
                        # Check for discharge indicators
                        is_discharge = False
                        
                        # Method 1: Check step type
                        if '工步種類' in df.columns:
                            step_types = step_9_data['工步種類'].unique()
                            if any('放電' in str(st) for st in step_types):
                                is_discharge = True
                        
                        # Method 2: Check current sign
                        current_col = '電流(A)' if '電流(A)' in df.columns else 'current'
                        if current_col in df.columns and not is_discharge:
                            avg_current = step_9_data[current_col].mean()
                            if avg_current < 0:  # Negative current indicates discharge
                                is_discharge = True
                        
                        if is_discharge and len(step_9_data) > max_step_9_rows:
                            best_candidate = detail_file
                            max_step_9_rows = len(step_9_data)
                            print(f"✅ FOUND CANDIDATE: {detail_file.name} with {len(step_9_data)} step 9 discharge rows")
                        
            except Exception as e:
                print(f"❌ ERROR READING {detail_file.name}: {e}")
                continue
        
        if not best_candidate:
            print("❌ NO SUITABLE CSV FILE FOUND WITH STEP 9 DISCHARGE DATA!")
            return False
            
        print(f"🎯 BEST CANDIDATE: {best_candidate.name} with {max_step_9_rows} rows")
        
        # Process the best candidate file
        try:
            df = pd.read_csv(best_candidate)
            
            # Filter for step 9
            step_col = '工步' if '工步' in df.columns else 'step_number'
            step_9_data = df[df[step_col] == 9].copy()
            
            print(f"📊 EXTRACTED {len(step_9_data)} ROWS FOR STEP 9")
            
            if len(step_9_data) == 0:
                print("❌ NO STEP 9 DATA FOUND!")
                return False
            
            # Map Chinese column names to English
            column_mapping = {
                '工步': 'step_number',
                '執行時間(秒)': 'execution_time',
                '電壓(V)': 'voltage',
                '電流(A)': 'current',
                '溫箱溫度': 'temperature',
                'Aux T1': 'temperature',  # Alternative temperature column
                '電量(Ah)': 'capacity',
                '能量(Wh)': 'energy',
                '總電量(Ah)': 'capacity',  # Alternative capacity column
            }
            
            # Rename columns
            detail_df = step_9_data.rename(columns=column_mapping)
            
            # Ensure required columns exist
            required_columns = ['step_number', 'execution_time', 'voltage', 'current']
            missing_columns = [col for col in required_columns if col not in detail_df.columns]
            
            if missing_columns:
                print(f"❌ MISSING REQUIRED COLUMNS: {missing_columns}")
                print(f"Available columns: {list(detail_df.columns)}")
                return False
            
            # Fill missing optional columns with defaults
            if 'temperature' not in detail_df.columns:
                detail_df['temperature'] = 25.0
                print("⚠️  Added default temperature column (25.0°C)")
            
            if 'capacity' not in detail_df.columns:
                detail_df['capacity'] = 0.0
                print("⚠️  Added default capacity column (0.0 Ah)")
                
            if 'energy' not in detail_df.columns:
                detail_df['energy'] = 0.0
                print("⚠️  Added default energy column (0.0 Wh)")
            
            # Create step mapping (step number 9 -> step ID 24)
            step_mapping = {9: 24}
            
            print(f"📋 PREPARED DATA:")
            print(f"   DataFrame shape: {detail_df.shape}")
            print(f"   Columns: {list(detail_df.columns)}")
            print(f"   Step mapping: {step_mapping}")
            print(f"   Sample data:")
            print(detail_df[['step_number', 'execution_time', 'voltage', 'current', 'temperature']].head())
            
            # Save measurements using the working function
            print(f"\n🔄 SAVING MEASUREMENTS...")
            save_measurements_to_db(
                experiment_id=14,
                details_df=detail_df,
                step_mapping=step_mapping,
                nominal_capacity=experiment.nominal_capacity
            )
            
            # Verify the save worked
            final_count = session.exec(
                select(func.count(Measurement.id)).where(Measurement.step_id == 24)
            ).one()
            
            print(f"\n✅ SUCCESS!")
            print(f"   Before: {current_count} measurements")
            print(f"   After: {final_count} measurements")
            print(f"   Added: {final_count - current_count} measurements")
            
            return True
            
        except Exception as e:
            print(f"❌ ERROR PROCESSING FILE: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    success = fix_experiment_14_measurements()
    if success:
        print("\n🎉 EXPERIMENT 14 MEASUREMENTS FIXED SUCCESSFULLY!")
    else:
        print("\n💥 FAILED TO FIX EXPERIMENT 14 MEASUREMENTS")
