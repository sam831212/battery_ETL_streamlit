#!/usr/bin/env python3
"""
Test script to verify the complete data_meta flow from UI to database.
This script simulates the user flow and checks if data_meta is properly saved.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
from sqlmodel import select
from datetime import datetime, UTC
from app.utils.database import get_session
from app.models import Experiment, Step, Cell, Machine
from app.etl import convert_numpy_types
from app.utils.data_helpers import convert_datetime_to_python

def test_data_meta_flow():
    """Test the complete data_meta flow"""
    print("Testing complete data_meta flow...")
    
    # Step 1: Create test data similar to what would come from UI
    test_steps_data = [
        {
            "step_number": 1,
            "step_type": "charge",
            "start_time": datetime.now(UTC),
            "end_time": datetime.now(UTC),
            "duration": 3600.0,
            "voltage_start": 3.0,
            "voltage_end": 4.2,
            "current": 1.0,
            "capacity": 3.0,
            "energy": 12.0,
            "temperature": 25.0,
            "c_rate": 0.3,
            "soc_start": 0.0,
            "soc_end": 100.0,
            "data_meta": "測試備註：這是一個充電工步"
        },
        {
            "step_number": 2,
            "step_type": "discharge",
            "start_time": datetime.now(UTC),
            "end_time": datetime.now(UTC),
            "duration": 7200.0,
            "voltage_start": 4.2,
            "voltage_end": 3.0,
            "current": -1.0,
            "capacity": 3.0,
            "energy": 12.0,
            "temperature": 25.0,
            "c_rate": 0.3,
            "soc_start": 100.0,
            "soc_end": 0.0,
            "data_meta": "測試備註：這是一個放電工步"
        }
    ]
    
    # Step 2: Simulate the database storage process
    with get_session() as session:
        try:
            # Clean up any existing test data
            existing_experiment = session.exec(
                select(Experiment).where(Experiment.name == "DataMeta_Test_Experiment")
            ).first()
            
            if existing_experiment:
                print(f"Cleaning up existing test experiment ID: {existing_experiment.id}")
                session.delete(existing_experiment)
                session.commit()
              # Create test cell and machine if they don't exist
            test_cell = session.exec(select(Cell).where(Cell.name == "TestCell_DataMeta")).first()
            if not test_cell:
                test_cell = Cell(
                    name="TestCell_DataMeta",
                    chemistry="NMC",  # 使用有效的 enum 值
                    form_factor="CYLINDRICAL",  # 使用有效的 enum 值
                    capacity=3.0
                )
                session.add(test_cell)
                session.flush()
            
            test_machine = session.exec(select(Machine).where(Machine.name == "TestMachine_DataMeta")).first()
            if not test_machine:
                test_machine = Machine(name="TestMachine_DataMeta")
                session.add(test_machine)
                session.flush()
            
            # Create experiment
            experiment = Experiment(
                name="DataMeta_Test_Experiment",
                description="Testing data_meta functionality",
                battery_type="NMC",
                nominal_capacity=3.0,
                start_date=datetime.now(UTC),
                cell_id=test_cell.id,
                machine_id=test_machine.id,
                operator="Test_User",
                temperature=25.0
            )
            session.add(experiment)
            session.flush()
            
            print(f"Created test experiment with ID: {experiment.id}")
            
            # Step 3: Create steps with data_meta (simulating the fixed code)
            created_steps = []
            for step_data in test_steps_data:
                row_dict = convert_numpy_types(step_data)
                
                # Convert datetime
                start_time = convert_datetime_to_python(row_dict.get("start_time"))
                end_time = convert_datetime_to_python(row_dict.get("end_time"))
                
                # Handle data_meta conversion (string to dict)
                step_data_meta = row_dict.get("data_meta", "")
                if isinstance(step_data_meta, str):
                    if step_data_meta.strip():
                        step_data_meta = {"user_note": step_data_meta}
                    else:
                        step_data_meta = {}
                
                # Create Step with data_meta
                step = Step(
                    experiment_id=experiment.id,
                    step_number=row_dict["step_number"],
                    step_type=row_dict["step_type"],
                    start_time=start_time,
                    end_time=end_time,
                    duration=row_dict.get("duration", 0.0),
                    voltage_start=row_dict.get("voltage_start", 0.0),
                    voltage_end=row_dict.get("voltage_end", 0.0),
                    current=row_dict.get("current", 0.0),
                    capacity=row_dict.get("capacity", 0.0),
                    energy=row_dict.get("energy", 0.0),
                    temperature=row_dict.get("temperature", 25.0),
                    c_rate=row_dict.get("c_rate", 0.0),
                    soc_start=row_dict.get("soc_start"),
                    soc_end=row_dict.get("soc_end"),
                    data_meta=step_data_meta
                )
                session.add(step)
                created_steps.append(step)
            
            session.commit()
            print(f"Created {len(created_steps)} steps with data_meta")
            
            # Step 4: Verify the data was saved correctly
            saved_steps = session.exec(
                select(Step).where(Step.experiment_id == experiment.id)
            ).all()
            
            print("\n=== Verification Results ===")
            all_passed = True
            
            for step in saved_steps:
                print(f"\nStep {step.step_number} ({step.step_type}):")
                print(f"  - ID: {step.id}")
                print(f"  - data_meta type: {type(step.data_meta)}")
                print(f"  - data_meta content: {step.data_meta}")
                
                # Check if data_meta was saved correctly
                if step.data_meta and "user_note" in step.data_meta:
                    original_note = test_steps_data[step.step_number - 1]["data_meta"]
                    saved_note = step.data_meta["user_note"]
                    
                    if original_note == saved_note:
                        print(f"  ✅ data_meta correctly saved: '{saved_note}'")
                    else:
                        print(f"  ❌ data_meta mismatch!")
                        print(f"     Expected: '{original_note}'")
                        print(f"     Got: '{saved_note}'")
                        all_passed = False
                else:
                    print(f"  ❌ data_meta not found or incorrect format")
                    all_passed = False
            
            if all_passed:
                print("\n🎉 All tests PASSED! The data_meta flow is working correctly.")
            else:
                print("\n❌ Some tests FAILED! There are issues with the data_meta flow.")
            
            return all_passed
            
        except Exception as e:
            print(f"❌ Error during testing: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

def main():
    """Main function"""
    print("Starting data_meta flow test...")
    success = test_data_meta_flow()
    
    if success:
        print("\n✅ Test completed successfully!")
        return 0
    else:
        print("\n❌ Test failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())
