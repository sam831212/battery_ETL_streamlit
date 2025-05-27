#!/usr/bin/env python3
"""
Debug script to test the save_measurements_to_db function and identify the issue
"""

import pandas as pd
from app.utils.database import get_session
from app.models import Measurement, Step, Experiment
from app.services.database_service import save_measurements_to_db
from app.etl import convert_numpy_types

def debug_save_measurements():
    """Test the save_measurements_to_db function with debug output"""
    print("===== DEBUG SAVE MEASUREMENTS =====")
    
    with get_session() as session:
        # Get the latest experiment
        experiment = session.query(Experiment).order_by(Experiment.id.desc()).first()
        if not experiment:
            print("❌ No experiments found")
            return
            
        print(f"✓ Found experiment: ID={experiment.id}, Name={experiment.name}")
        
        # Get steps for this experiment
        steps = session.query(Step).filter(Step.experiment_id == experiment.id).all()
        if not steps:
            print("❌ No steps found for this experiment")
            return
            
        print(f"✓ Found {len(steps)} steps")
        
        # Create step mapping
        step_mapping = {step.step_number: step.id for step in steps}
        print(f"✓ Step mapping: {step_mapping}")
        
        # Check existing measurements
        existing_measurements = session.query(Measurement).join(Step).filter(
            Step.experiment_id == experiment.id
        ).count()
        print(f"📊 Existing measurements for experiment {experiment.id}: {existing_measurements}")
        
        # Create test measurement data
        test_data = []
        step_numbers = list(step_mapping.keys())
        
        for step_number in step_numbers[:2]:  # Test with first 2 steps
            for i in range(3):  # 3 measurements per step
                test_data.append({
                    'step_number': step_number,
                    'execution_time': i * 10.0,
                    'voltage': 3.7 + (i * 0.1),
                    'current': 1.0,
                    'temperature': 25.0,
                    'capacity': i * 0.5,
                    'energy': i * 2.0,
                    'soc': 50.0 + (i * 10.0)
                })
        
        test_df = pd.DataFrame(test_data)
        print(f"✓ Created test DataFrame with {len(test_df)} rows")
        print(f"Test data columns: {list(test_df.columns)}")
        print(f"Test data sample:\n{test_df.head()}")
        
        # Test the save function
        print(f"\n🚀 Testing save_measurements_to_db...")
        
        try:
            save_measurements_to_db(
                experiment_id=experiment.id,
                details_df=test_df,
                step_mapping=step_mapping,
                nominal_capacity=experiment.nominal_capacity
            )
            
            # Check if measurements were actually saved
            new_measurement_count = session.query(Measurement).join(Step).filter(
                Step.experiment_id == experiment.id
            ).count()
            
            print(f"\n📊 Measurement count after save: {new_measurement_count}")
            print(f"📊 New measurements added: {new_measurement_count - existing_measurements}")
            
            if new_measurement_count > existing_measurements:
                print("✅ SUCCESS: Measurements were saved successfully!")
            else:
                print("❌ FAILURE: No new measurements were saved!")
                
                # Let's investigate why...
                print("\n🔍 Investigating the issue...")
                
                # Check if the step_mapping has valid step_ids
                for step_num, step_id in step_mapping.items():
                    step_exists = session.query(Step).filter(Step.id == step_id).first()
                    if step_exists:
                        print(f"✓ Step {step_num} (ID: {step_id}) exists in database")
                    else:
                        print(f"❌ Step {step_num} (ID: {step_id}) NOT found in database")
                
        except Exception as e:
            print(f"❌ ERROR during save_measurements_to_db: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    debug_save_measurements()
