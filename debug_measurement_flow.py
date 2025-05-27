#!/usr/bin/env python3
"""
Debug script to trace the measurement data saving flow and identify where the problem occurs.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
try:
    from app.utils.database import get_session
    from app.models import Experiment, Step, Measurement
    from app.services.database_service import save_measurements_to_db
    from app.services.file_processing_service import handle_file_processing_pipeline
    from app.etl.extraction import parse_detail_csv
except ImportError as e:
    print(f"Import error: {e}")
    sys.exit(1)

def debug_measurement_saving_flow():
    """Debug the complete measurement saving flow"""
    print("=" * 60)
    print("DEBUGGING MEASUREMENT SAVING FLOW")
    print("=" * 60)    # Step 1: Check current database state
    print("\n1. CURRENT DATABASE STATE:")
    with get_session() as session:
        from sqlmodel import select, func
        
        experiment_count = session.exec(select(func.count(Experiment.id))).one()
        step_count = session.exec(select(func.count(Step.id))).one()
        measurement_count = session.exec(select(func.count(Measurement.id))).one()
        
        print(f"  Experiments: {experiment_count}")
        print(f"  Steps: {step_count}")
        print(f"  Measurements: {measurement_count}")
        
        if experiment_count > 0:
            # Get the latest experiment
            latest_experiment = session.exec(
                select(Experiment).order_by(Experiment.id.desc())
            ).first()
            print(f"  Latest Experiment ID: {latest_experiment.id}")
            print(f"  Latest Experiment Name: {latest_experiment.name}")
            
            # Get steps for this experiment
            steps = session.exec(
                select(Step).where(Step.experiment_id == latest_experiment.id)
            ).all()
            print(f"  Steps in latest experiment: {len(steps)}")
            
            for step in steps:
                measurement_count_for_step = session.exec(
                    select(func.count(Measurement.id)).where(Measurement.step_id == step.id)
                ).one()
                print(f"    Step {step.step_number} (ID: {step.id}): {measurement_count_for_step} measurements")    # Step 2: Check session state (commented out since we're not in Streamlit context)
    print("\n2. STREAMLIT SESSION STATE:")
    print("  (Skipped - not in Streamlit context)")
    # Streamlit session state check removed since we're running standalone

    # Step 3: Test with example file
    print("\n3. TESTING WITH EXAMPLE FILE:")
    example_detail_file = "example_csv_chromaLex/CALB20Ah_ BMW power map_as 24Ah_0331_Detail.csv"
    
    if os.path.exists(example_detail_file):
        print(f"  Example file found: {example_detail_file}")
        
        try:
            # Load and parse the example file
            with open(example_detail_file, 'rb') as f:
                detail_content = f.read()
            
            # Parse the detail file
            detail_df = parse_detail_csv(detail_content)
            
            print(f"  Parsed detail DataFrame:")
            print(f"    Shape: {detail_df.shape}")
            print(f"    Columns: {list(detail_df.columns)}")
            print(f"    Step numbers: {sorted(detail_df['step_number'].unique()) if 'step_number' in detail_df.columns else 'No step_number column'}")
            
            # Show sample data
            if not detail_df.empty:
                print(f"  Sample data (first 3 rows):")
                print(detail_df.head(3).to_string())
                
        except Exception as e:
            print(f"  Error parsing example file: {str(e)}")
    else:
        print(f"  Example file not found: {example_detail_file}")

    # Step 4: Test save_measurements_to_db function directly
    print("\n4. TESTING save_measurements_to_db FUNCTION DIRECTLY:")
    
    # Create a simple test dataset
    test_detail_df = pd.DataFrame({
        'step_number': [1, 1, 1, 2, 2, 2],
        'execution_time': [0.0, 1.0, 2.0, 0.0, 1.0, 2.0],
        'voltage': [3.2, 3.3, 3.4, 3.4, 3.3, 3.2],
        'current': [1.0, 1.0, 1.0, -1.0, -1.0, -1.0],
        'temperature': [25.0, 25.1, 25.2, 25.2, 25.1, 25.0],
        'capacity': [0.0, 0.5, 1.0, 1.0, 0.5, 0.0],
        'energy': [0.0, 1.0, 2.0, 2.0, 1.0, 0.0]
    })
    
    test_step_mapping = {1: 101, 2: 102}  # step_number -> step_id (fake IDs)
    test_experiment_id = 999  # fake experiment ID
    
    print(f"  Test data shape: {test_detail_df.shape}")
    print(f"  Test step mapping: {test_step_mapping}")
    
    # This will fail because the step IDs don't exist, but it will show us the debug output
    try:
        save_measurements_to_db(
            experiment_id=test_experiment_id,
            details_df=test_detail_df,
            step_mapping=test_step_mapping,
            nominal_capacity=3.2
        )
    except Exception as e:
        print(f"  Expected error (fake IDs): {str(e)}")

    print("\n5. CHECKING CALL CHAIN:")
    print("  The expected call chain is:")
    print("  UI -> handle_file_processing_pipeline -> save_measurements_to_db")
    print("  Let's verify each step...")

    # Step 5: Check if function is imported correctly
    print("\n6. IMPORT CHECK:")
    try:
        from app.services.database_service import save_measurements_to_db as imported_func
        print(f"  save_measurements_to_db imported successfully: {imported_func}")
        print(f"  Function location: {imported_func.__module__}")
    except ImportError as e:
        print(f"  Import error: {str(e)}")

def main():
    """Main function"""
    debug_measurement_saving_flow()

if __name__ == "__main__":
    main()
