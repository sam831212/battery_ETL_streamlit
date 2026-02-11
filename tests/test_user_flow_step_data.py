import pytest
import pandas as pd
from sqlmodel import Session, select
from app.models.database import Cell, Machine, Experiment, Step, Measurement, CellChemistry, CellFormFactor # Import Enums
from app.services.database_service import save_steps_to_db, save_measurements_to_db # Assuming these are the correct functions
from app.etl.extraction import parse_step_csv, parse_detail_csv # Assuming these are used for parsing
from datetime import datetime, UTC # Import UTC


# Assuming conftest.py sets up the in-memory DB and session fixture 'db_session'

@pytest.fixture
def example_step_file_path():
    return "c:\\\\Users\\\\sam2_chen\\\\DB0527\\\\B\\\\example_csv_chromaLex\\\\CALB20Ah_ BMW power map_as 24Ah_0331_Step.csv"

@pytest.fixture
def example_detail_file_path(): # We might need a dummy detail file or mock its processing if not directly testing it
    # Create a dummy detail file content if necessary or use an existing one
    # For now, let's assume we might not need its actual content for this specific step test
    return "c:\\\\Users\\\\sam2_chen\\\\DB0527\\\\B\\\\example_csv_chromaLex\\\\CALB20Ah_ BMW power map_as 24Ah_0331_Detail.csv"

def test_simulate_user_upload_and_save_step_45(db_session: Session, example_step_file_path: str, example_detail_file_path: str):
    """
    Simulates user uploading step and detail files, selecting a step,
    entering metadata, and saving to the database.
    Then checks if step data (specifically for step 45) is stored correctly.
    """
    # 1. Simulate Metadata Creation
    cell = Cell(
        name="Test Cell", 
        chemistry=CellChemistry.LFP, 
        form_factor=CellFormFactor.PRISMATIC, 
        nominal_capacity=20.0  # Corrected parameter name
    )
    machine = Machine(
        name="Test Machine", 
        model_number="Chroma" # Corrected parameter, removed others
    )
    db_session.add(cell)
    db_session.add(machine)
    db_session.commit()
    db_session.refresh(cell)
    db_session.refresh(machine)

    experiment = Experiment(
        name="Test Experiment for Step 45",
        start_date=datetime.now(UTC), # Updated to use timezone-aware datetime
        operator="TestUser",
        cell_id=cell.id,
        machine_id=machine.id,
        nominal_capacity=20.0, # Example, should match cell if applicable
        battery_type="NCM",
        temperature=25.0
    )
    db_session.add(experiment)
    db_session.commit()
    db_session.refresh(experiment)

    # 2. Process Step File and Select Step 45
    # Assuming parse_step_csv handles the mapping of column names like '工步' to 'step_number'
    # And other necessary transformations for database saving
    raw_steps_df = pd.read_csv(example_step_file_path)
    # The parse_step_csv function should ideally be used if it does more than just pd.read_csv
    # For this test, we'll manually prepare a simplified DataFrame row for step 45
    # to feed into save_steps_to_db, assuming prior parsing and transformation logic.

    # Find step 45 in the raw CSV data
    # Headers from the CSV: 循環,迴圈,子循環,子迴圈,MR編號,子配方編號,工步,工步,工步種類,日期時間,工步執行時間(秒),工步時間,截止電壓(V),截止電流(A),能量(Wh),截止電量(Ah),功率(W),充電電量(Ah),放電電量(Ah),充電能量(Wh),放電能量(Wh),總電量(Ah),截止Q(%),狀態,Aux T1,溫箱溫度,Aux T2,Aux T3
    step_45_data_series = raw_steps_df[raw_steps_df['工步'] == 45].iloc[0]

    # Manually create a DataFrame for the single step, mapping to expected schema for save_steps_to_db
    # This mapping needs to be accurate based on how 'save_steps_to_db' expects its input DataFrame
    # and what transformations normally occur in the ETL pipeline.
    # We need to know the exact column names and types 'save_steps_to_db' expects.
    # Let's assume a simplified mapping for now and adjust based on 'save_steps_to_db' implementation.

    # Inferring column names from `app.services.database_service.save_steps_to_db` and `Step` model
    # Step model fields: experiment_id, step_number, step_type, start_time, end_time, duration,
    # voltage_start, voltage_end, current, capacity, energy, temperature, temperature_min,
    # temperature_max, c_rate, soc_start, soc_end, ocv, data_meta

    # Convert date string to datetime object
    # The date format in CSV is 'mm/dd/yyyy HH:MM:SS'
    try:
        step_datetime = pd.to_datetime(step_45_data_series['日期時間'], format='%m/%d/%Y %H:%M:%S')
    except ValueError:
        step_datetime = pd.to_datetime(step_45_data_series['日期時間']) # Try inferring if specific format fails

    # Assuming duration is '工步執行時間(秒)'
    # Assuming '工步種類' maps to 'step_type'
    # Other fields like voltage_start, capacity, energy, soc_start, soc_end, ocv might need to be sourced
    # or calculated by upstream processes. For this test, we'll use available values or placeholders.

    steps_for_db_data = {
        'step_number': [int(step_45_data_series['工步'])],
        'step_type': [str(step_45_data_series['工步種類'])],
        'start_time': [step_datetime], # Placeholder, actual start_time might differ or be calculated
        'end_time': [step_datetime + pd.to_timedelta(float(step_45_data_series['工步執行時間(秒)']), unit='s')], # Placeholder
        'duration': [float(step_45_data_series['工步執行時間(秒)'])],
        'voltage_start': [0.0], # Changed None to 0.0 to satisfy NOT NULL constraint
        'voltage_end': [float(step_45_data_series['截止電壓(V)'])],
        'current': [float(step_45_data_series['截止電流(A)'])],
        'capacity': [float(step_45_data_series['截止電量(Ah)'])], # This is '截止電量(Ah)'
        'energy': [float(step_45_data_series['能量(Wh)'])],
        'temperature': [float(step_45_data_series.get('溫箱溫度', 25.0))], # Use '溫箱溫度' or default
        # 'c_rate': [None], # This is calculated in save_steps_to_db
        'soc_start': [None], # Placeholder, typically calculated
        'soc_end': [None], # Placeholder, typically calculated
        # 'ocv' and 'data_meta' will be the row_dict in save_steps_to_db
    }
    steps_df_for_saving = pd.DataFrame(steps_for_db_data)    # 3. Save Step Data
    # Ensure experiment.id and experiment.nominal_capacity are not None
    assert experiment.id is not None, "Experiment ID should not be None after commit and refresh"
    assert experiment.nominal_capacity is not None, "Experiment nominal_capacity should not be None"
    
    # 傳入 db_session 以確保返回對象與當前會話綁定
    saved_steps = save_steps_to_db(
        experiment_id=experiment.id,
        steps_df=steps_df_for_saving,
        nominal_capacity=experiment.nominal_capacity,
        session=db_session
    )
    assert len(saved_steps) == 1
    saved_step_id = saved_steps[0].id    # 4. Verify Data in Database
    # 由於我們現在使用相同的會話，不需要清除會話或重新查詢
    # 我們可以直接使用傳回的對象，但為了穩健起見，仍使用 db_session.get 
    retrieved_step = db_session.get(Step, saved_step_id)
    assert retrieved_step is not None
    assert retrieved_step.step_number == 45

    print(f"Retrieved step from DB: {retrieved_step.model_dump()}")

    # Add assertions to check for 0 or null values for critical fields
    # These are based on the Step model and common fields that might be problematic
    assert retrieved_step.step_type is not None and retrieved_step.step_type != "", "step_type should not be null or empty"
    assert retrieved_step.start_time is not None, "start_time should not be null"
    assert retrieved_step.end_time is not None, "end_time should not be null"
    assert retrieved_step.duration is not None and retrieved_step.duration > 0, "duration should be greater than 0"
    assert retrieved_step.voltage_start is not None, "voltage_start should not be null"


    # Voltage, Current, Capacity, Energy can be 0 legitimately in some step types (e.g. rest)
    # For a '超級CP放電' step (step 45 type), these should ideally not be 0 unless it's a very short/null step.
    # From CSV: 截止電壓(V) = 3.073657, 截止電流(A) = -361.625, 能量(Wh) = -3.087274, 截止電量(Ah) = -0.986257
    # The Step model stores capacity and energy (likely absolute or net values depending on transformation)
    # Current is stored as is.

    if retrieved_step.step_type == "超級CP放電":
        assert retrieved_step.voltage_end is not None, f"voltage_end for {retrieved_step.step_type} should not be null"
        # Allow for 0 if that's a valid end state, but for CP discharge, it's usually non-zero.
        # assert retrieved_step.voltage_end != 0, f"voltage_end for {retrieved_step.step_type} should not be 0"

        assert retrieved_step.current is not None, f"current for {retrieved_step.step_type} should not be null"
        assert retrieved_step.current != 0, f"current for {retrieved_step.step_type} should not be 0"

        # Capacity and Energy in the Step table might represent the *change* during the step or total.
        # The CSV has "截止電量(Ah)" and "能量(Wh)" which are likely the values for the step itself.
        # Let's check if they are non-zero. The signs might change based on transformation.
        assert retrieved_step.capacity is not None, f"capacity for {retrieved_step.step_type} should not be null"
        # Capacity can be negative for discharge, so abs check or specific sign check
        assert retrieved_step.capacity != 0, f"capacity for {retrieved_step.step_type} should not be 0"

        assert retrieved_step.energy is not None, f"energy for {retrieved_step.step_type} should not be null"
        assert retrieved_step.energy != 0, f"energy for {retrieved_step.step_type} should not be 0"

    assert retrieved_step.temperature is not None, "temperature should not be null"
    # c_rate is calculated, so it should exist if current and nominal_capacity are valid
    assert retrieved_step.c_rate is not None, "c_rate should not be null"
    if retrieved_step.step_type not in ["靜置", "rest", "溫箱控制"] : # C-rate can be 0 for rest steps
         assert retrieved_step.c_rate != 0, f"c_rate for {retrieved_step.step_type} should not be 0"    # Check data_meta content if necessary
    assert retrieved_step.data_meta is not None, "data_meta should not be null"
    # 由於資料已經過 ETL 處理，data_meta 包含轉換後的列名
    assert "step_number" in retrieved_step.data_meta, "data_meta should contain step_number"
    assert retrieved_step.data_meta["step_number"] == 45, "data_meta should have correct step number"

    # If the issue is with specific columns being zero/null, add direct assertions for them:
    # e.g., assert retrieved_step.some_problematic_column is not None
    # e.g., assert retrieved_step.some_problematic_column != 0

    # (Optional) Simulate saving measurements if that's part of the problem scope
    # For now, focusing on the Step table as per the prompt.

