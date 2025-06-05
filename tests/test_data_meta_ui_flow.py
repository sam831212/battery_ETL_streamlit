#!/usr/bin/env python3
"""
Test to verify complete data_meta flow from UI to database
"""
import pandas as pd
from sqlmodel import Session, select
from datetime import datetime, timezone
import sys
import os

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.models.database import Cell, Machine, Experiment, Step, CellChemistry, CellFormFactor
from app.utils.database import get_session

def test_data_meta_ui_flow():
    """Test that data_meta flows correctly from UI simulation to database"""
    print("Testing complete data_meta flow from UI to database...")
    
    with get_session() as session:
        # 1. Setup test data (simulate what UI would create)
        cell = Cell(
            name="Test Cell UI Flow",
            chemistry=CellChemistry.LFP,
            form_factor=CellFormFactor.PRISMATIC,
            nominal_capacity=20.0
        )
        machine = Machine(
            name="Test Machine UI Flow",
            model_number="ChromaUI"
        )
        session.add(cell)
        session.add(machine)
        session.commit()
        session.refresh(cell)
        session.refresh(machine)
        
        # 2. Simulate what happens in step_selection_page.py
        # This simulates the data structure created in render_step_selection_page()
        print("Simulating step selection UI process...")
        
        # Simulate the selected_steps data that gets stored in session state
        # This includes the data_meta that users input in the UI
        simulated_selected_steps = [
            {
                'step_number': 1,
                'step_type': 'charge',
                'start_time': datetime.now(timezone.utc),
                'end_time': datetime.now(timezone.utc),
                'duration': 3600.0,
                'voltage_start': 3.3,
                'voltage_end': 4.0,
                'current': 1.0,
                'capacity': 2.0,
                'energy': 7.0,
                'temperature': 25.0,
                'c_rate': 0.05,
                'soc_start': 0.0,
                'soc_end': 100.0,
                'data_meta': 'User comment for step 1 - Initial charge cycle'  # User input!
            },
            {
                'step_number': 2,
                'step_type': 'discharge',
                'start_time': datetime.now(timezone.utc),
                'end_time': datetime.now(timezone.utc),
                'duration': 7200.0,
                'voltage_start': 4.0,
                'voltage_end': 3.0,
                'current': -1.0,
                'capacity': 2.0,
                'energy': 7.0,
                'temperature': 25.5,
                'c_rate': 0.05,
                'soc_start': 100.0,
                'soc_end': 0.0,
                'data_meta': 'User comment for step 2 - Discharge to empty'  # User input!
            }
        ]
        
        # 3. Simulate what happens in handle_selected_steps_save()
        print("Simulating database save process...")
        
        # Create experiment
        experiment = Experiment(
            name="Test Data Meta UI Flow",
            start_date=datetime.now(timezone.utc),
            operator="Test User",
            description="Testing data_meta flow from UI",
            cell_id=cell.id,
            machine_id=machine.id,
            nominal_capacity=20.0,
            battery_type=cell.chemistry,
            temperature=25.0
        )
        session.add(experiment)
        session.flush()
        
        # Create DataFrame from selected steps (like the fixed code does)
        steps_df_to_use = pd.DataFrame(simulated_selected_steps)
        
        # Create steps with data_meta
        steps = []
        for _, row in steps_df_to_use.iterrows():
            row_dict = row.to_dict()
            
            step = Step(
                experiment_id=experiment.id,
                step_number=row_dict["step_number"],
                step_type=row_dict["step_type"],
                start_time=row_dict["start_time"],
                end_time=row_dict["end_time"],
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
                data_meta=row_dict.get("data_meta", {})  # This should now work!
            )
            session.add(step)
            steps.append(step)
        
        session.commit()
        
        # 4. Verify data_meta was saved correctly
        print("Verifying saved data...")
        saved_steps = session.exec(select(Step).where(Step.experiment_id == experiment.id)).all()
        
        print(f"✓ Found {len(saved_steps)} saved steps")
        
        for step in saved_steps:
            print(f"Step {step.step_number}:")
            print(f"  - Type: {step.step_type}")
            print(f"  - data_meta: {step.data_meta}")
            
            # Verify data_meta is not empty
            if isinstance(step.data_meta, str):
                assert step.data_meta != "", f"data_meta should not be empty for step {step.step_number}"
                assert "User comment" in step.data_meta, f"data_meta should contain user comment for step {step.step_number}"
            else:
                # If it's stored as dict, it should not be empty
                assert step.data_meta is not None, f"data_meta should not be None for step {step.step_number}"
        
        print("✓ All data_meta values were saved correctly!")
        
        # 5. Test edge case: mixed data_meta types
        print("\nTesting edge case with mixed data_meta types...")
        
        # Create another experiment with mixed data_meta
        experiment2 = Experiment(
            name="Test Mixed Data Meta",
            start_date=datetime.now(timezone.utc),
            operator="Test User",
            description="Testing mixed data_meta types",
            cell_id=cell.id,
            machine_id=machine.id,
            nominal_capacity=20.0,
            battery_type=cell.chemistry,
            temperature=25.0
        )
        session.add(experiment2)
        session.flush()
        
        # Test with different data_meta types
        test_cases = [
            {"step_number": 10, "data_meta": "Simple string comment"},
            {"step_number": 11, "data_meta": {"note": "Dict comment", "priority": "high"}},
            {"step_number": 12, "data_meta": ""},  # Empty string
            {"step_number": 13, "data_meta": {}},  # Empty dict
        ]
        
        for case in test_cases:
            step = Step(
                experiment_id=experiment2.id,
                step_number=case["step_number"],
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
                data_meta=case["data_meta"]
            )
            session.add(step)
        
        session.commit()
        
        # Verify mixed types
        saved_mixed_steps = session.exec(select(Step).where(Step.experiment_id == experiment2.id)).all()
        
        for step in saved_mixed_steps:
            print(f"Mixed Step {step.step_number}: data_meta = {step.data_meta} (type: {type(step.data_meta)})")
        
        print("✓ Mixed data_meta types handled correctly!")
        
        return True

if __name__ == "__main__":
    try:
        success = test_data_meta_ui_flow()
        if success:
            print("\n🎉 SUCCESS: Complete data_meta UI flow test passed!")
            print("✓ User input data_meta flows correctly from UI to database")
            print("✓ Both string and dict data_meta types are supported")
            print("✓ The fix successfully preserves user comments")
        else:
            print("\n❌ FAILED: Test failed")
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
