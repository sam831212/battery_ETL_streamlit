#!/usr/bin/env python3
"""
Debug script to investigate the real measurement saving issue with actual data.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
from sqlmodel import select, func

try:
    from app.utils.database import get_session
    from app.models import Experiment, Step, Measurement
    from app.services.database_service import save_measurements_to_db
    from app.etl.extraction import parse_detail_csv
except ImportError as e:
    print(f"Import error: {e}")
    sys.exit(1)

def debug_real_measurement_issue():
    """Debug the real measurement saving issue"""
    print("=" * 60)
    print("DEBUGGING REAL MEASUREMENT ISSUE")
    print("=" * 60)

    # Step 1: Check the latest experiment and its steps
    print("\n1. INVESTIGATING LATEST EXPERIMENT:")
    with get_session() as session:
        # Get the latest experiment
        latest_experiment = session.exec(
            select(Experiment).order_by(Experiment.id.desc())
        ).first()
        
        if latest_experiment:
            print(f"  Latest Experiment: ID={latest_experiment.id}, Name='{latest_experiment.name}'")
            
            # Get all steps for this experiment
            steps = session.exec(
                select(Step).where(Step.experiment_id == latest_experiment.id)
            ).all()
            
            print(f"  Steps in experiment {latest_experiment.id}:")
            for step in steps:
                measurement_count = session.exec(
                    select(func.count(Measurement.id)).where(Measurement.step_id == step.id)
                ).one()
                print(f"    Step {step.step_number} (ID: {step.id}): {measurement_count} measurements")
                print(f"      Type: {step.step_type}, Duration: {step.duration}")
    
    # Step 2: Try to parse the actual detail file
    print("\n2. PARSING ACTUAL DETAIL FILE:")
    detail_file_path = "example_csv_chromaLex/CALB20Ah_ BMW power map_as 24Ah_0331_Detail.csv"
    
    if os.path.exists(detail_file_path):
        try:
            # Read the file content properly
            with open(detail_file_path, 'r', encoding='utf-8') as f:
                file_content = f.read()
            
            # Parse using the correct method
            detail_df = parse_detail_csv(file_content)
            
            print(f"  Successfully parsed detail file:")
            print(f"    Shape: {detail_df.shape}")
            print(f"    Columns: {list(detail_df.columns)}")
            
            if 'step_number' in detail_df.columns:
                unique_steps = sorted(detail_df['step_number'].unique())
                print(f"    Unique step numbers: {unique_steps[:10]}{'...' if len(unique_steps) > 10 else ''}")
                print(f"    Total unique steps: {len(unique_steps)}")
                
                # Show sample data for first few steps
                for step_num in unique_steps[:3]:
                    step_data = detail_df[detail_df['step_number'] == step_num]
                    print(f"    Step {step_num}: {len(step_data)} rows")
                    if len(step_data) > 0:
                        print(f"      First row: {dict(step_data.iloc[0])}")
            
        except Exception as e:
            print(f"  Error parsing detail file: {str(e)}")
            import traceback
            traceback.print_exc()
    else:
        print(f"  Detail file not found: {detail_file_path}")
    
    # Step 3: Check if there are any measurements in the database at all
    print("\n3. CHECKING ALL MEASUREMENTS:")
    with get_session() as session:
        all_measurements = session.exec(select(Measurement)).all()
        print(f"  Total measurements in database: {len(all_measurements)}")
        
        if all_measurements:
            print("  Sample measurements:")
            for i, measurement in enumerate(all_measurements[:5]):
                print(f"    {i+1}. ID: {measurement.id}, Step ID: {measurement.step_id}, "
                      f"Time: {measurement.execution_time}, Voltage: {measurement.voltage}")
        
        # Check which experiments have measurements
        measurement_by_exp = session.exec(
            select(Step.experiment_id, func.count(Measurement.id))
            .join(Measurement, Step.id == Measurement.step_id)
            .group_by(Step.experiment_id)
        ).all()
        
        print(f"  Measurements by experiment:")
        for exp_id, count in measurement_by_exp:
            print(f"    Experiment {exp_id}: {count} measurements")

    # Step 4: Test with a real step from the database
    print("\n4. TESTING WITH REAL STEP DATA:")
    with get_session() as session:
        # Get a real step from the latest experiment
        latest_experiment = session.exec(
            select(Experiment).order_by(Experiment.id.desc())
        ).first()
        
        if latest_experiment:
            real_step = session.exec(
                select(Step).where(Step.experiment_id == latest_experiment.id)
            ).first()
            
            if real_step:
                print(f"  Using real step: ID={real_step.id}, Number={real_step.step_number}")
                
                # Create test data with the real step
                test_detail_df = pd.DataFrame({
                    'step_number': [real_step.step_number] * 3,
                    'execution_time': [0.0, 1.0, 2.0],
                    'voltage': [3.2, 3.3, 3.4],
                    'current': [1.0, 1.0, 1.0],
                    'temperature': [25.0, 25.1, 25.2],
                    'capacity': [0.0, 0.5, 1.0],
                    'energy': [0.0, 1.0, 2.0]
                })
                
                real_step_mapping = {real_step.step_number: real_step.id}
                
                print(f"  Test data with real step mapping: {real_step_mapping}")
                
                # Count measurements before
                before_count = session.exec(
                    select(func.count(Measurement.id)).where(Measurement.step_id == real_step.id)
                ).one()
                print(f"  Measurements before: {before_count}")
                
                try:
                    save_measurements_to_db(
                        experiment_id=latest_experiment.id,
                        details_df=test_detail_df,
                        step_mapping=real_step_mapping,
                        nominal_capacity=3.2
                    )
                    
                    # Count measurements after
                    after_count = session.exec(
                        select(func.count(Measurement.id)).where(Measurement.step_id == real_step.id)
                    ).one()
                    print(f"  Measurements after: {after_count}")
                    print(f"  New measurements added: {after_count - before_count}")
                    
                except Exception as e:
                    print(f"  Error saving with real step: {str(e)}")
                    import traceback
                    traceback.print_exc()

if __name__ == "__main__":
    debug_real_measurement_issue()
