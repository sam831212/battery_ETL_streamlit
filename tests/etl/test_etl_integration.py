"""
Integration tests for the ETL module

These tests verify that the extraction and transformation modules work together
correctly for end-to-end ETL processing of battery test data.
"""
import os
import pytest
import pandas as pd
import numpy as np
from sqlmodel import SQLModel, create_engine, Session
from datetime import datetime

from app.etl.extraction import load_and_preprocess_files
from app.etl.transformation import transform_data
from app.etl.validation import generate_validation_report
from app.models.database import (
    Experiment, 
    Step, 
    Measurement, 
    ProcessedFile
)

# Test database URL for integration tests
TEST_DB_URL = "sqlite:///:memory:"

# Paths to example data files
EXAMPLE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                          "example_csv_chromaLex")
EXAMPLE_STEP_CSV = os.path.join(EXAMPLE_DIR, "EVE_M41_CLC_FCV_M-table_Peak_charge_60s_0220_Step.csv")
EXAMPLE_DETAIL_CSV = os.path.join(EXAMPLE_DIR, "EVE_M41_CLC_FCV_M-table_Peak_charge_60s_0220_Detail.csv")


@pytest.fixture(scope="module")
def test_engine():
    """Create a test database engine for integration tests"""
    # Create engine
    engine = create_engine(TEST_DB_URL, echo=False)
    
    # Create tables
    SQLModel.metadata.create_all(engine)
    
    yield engine
    
    # Clean up
    SQLModel.metadata.drop_all(engine)


@pytest.fixture
def test_session(test_engine):
    """Create a database session for tests"""
    with Session(test_engine) as session:
        yield session
        # Roll back any changes from the test
        session.rollback()


@pytest.fixture
def processed_data():
    """Load and process example data files"""
    nominal_capacity = 3.5  # Example capacity in Ah
    
    # Load and transform the data
    step_df, detail_df, metadata = load_and_preprocess_files(
        EXAMPLE_STEP_CSV,
        EXAMPLE_DETAIL_CSV,
        nominal_capacity=nominal_capacity,
        apply_transformations=True
    )
    
    return {
        'step_df': step_df,
        'detail_df': detail_df,
        'metadata': metadata,
        'nominal_capacity': nominal_capacity
    }


def test_etl_complete_flow(processed_data):
    """Test the complete ETL flow from file loading to transformation"""
    step_df = processed_data['step_df']
    detail_df = processed_data['detail_df']
    metadata = processed_data['metadata']
    
    # Verify basic requirements of processed data
    assert isinstance(step_df, pd.DataFrame)
    assert isinstance(detail_df, pd.DataFrame)
    assert not step_df.empty
    assert not detail_df.empty
    
    # Check that all required columns exist after processing
    required_step_columns = [
        'step_number', 'step_type', 'start_time', 'end_time', 'duration',
        'voltage_end', 'current', 'capacity', 'energy', 'c_rate', 
        'temperature_avg', 'soc_start', 'soc_end'
    ]
    
    required_detail_columns = [
        'step_number', 'timestamp', 'voltage', 'current', 
        'temperature', 'capacity', 'energy', 'c_rate', 'soc'
    ]
    
    for column in required_step_columns:
        assert column in step_df.columns, f"Required column {column} missing from step_df"
    
    for column in required_detail_columns:
        assert column in detail_df.columns, f"Required column {column} missing from detail_df"
    
    # Verify data consistency
    assert step_df['step_number'].nunique() == len(step_df)  # Each step number should be unique
    
    # Check relationships between steps and details
    step_numbers = set(step_df['step_number'])
    detail_step_numbers = set(detail_df['step_number'])
    
    # All step numbers in detail_df should exist in step_df
    assert detail_step_numbers.issubset(step_numbers)
    
    # Check metadata
    assert 'step_file' in metadata
    assert 'detail_file' in metadata
    assert 'experiment' in metadata
    assert 'nominal_capacity' in metadata['experiment']
    assert metadata['experiment']['nominal_capacity'] == processed_data['nominal_capacity']
    
    # Verify transformation results
    # C-rate should be calculated
    assert 'c_rate' in step_df.columns
    assert not step_df['c_rate'].isna().all()
    
    # SOC should be calculated
    assert 'soc_start' in step_df.columns
    assert 'soc_end' in step_df.columns
    assert not step_df['soc_start'].isna().all()
    assert not step_df['soc_end'].isna().all()
    
    # Temperature metrics should be calculated
    assert 'temperature_avg' in step_df.columns
    assert 'temperature_min' in step_df.columns
    assert 'temperature_max' in step_df.columns
    assert not step_df['temperature_avg'].isna().all()
    
    # OCV values should be extracted for rest steps
    assert 'ocv' in step_df.columns
    rest_steps = step_df[step_df['step_type'] == 'rest']
    if not rest_steps.empty:
        assert not rest_steps['ocv'].isna().all()


def test_etl_to_database(test_session, processed_data):
    """Test storing processed ETL data in the database"""
    step_df = processed_data['step_df']
    detail_df = processed_data['detail_df']
    metadata = processed_data['metadata']
    
    # Create experiment
    experiment = Experiment(
        name="ETL Integration Test",
        description="Test for ETL integration",
        battery_type="Li-ion",
        nominal_capacity=processed_data['nominal_capacity'],
        temperature_avg=float(step_df['temperature_avg'].mean()),
        start_date=step_df['start_time'].min(),
        end_date=step_df['end_time'].max(),
        data_meta=metadata['experiment']
    )
    test_session.add(experiment)
    test_session.commit()
    test_session.refresh(experiment)
    
    # Create processed file records
    step_file = ProcessedFile(
        experiment_id=experiment.id,
        filename=metadata['step_file']['filename'],
        file_type="step",
        file_hash=metadata['step_file']['hash'],
        row_count=metadata['step_file']['rows'],
        processed_at=datetime.now(),
        data_meta={"headers": step_df.columns.tolist()}
    )
    
    detail_file = ProcessedFile(
        experiment_id=experiment.id,
        filename=metadata['detail_file']['filename'],
        file_type="detail",
        file_hash=metadata['detail_file']['hash'],
        row_count=metadata['detail_file']['rows'],
        processed_at=datetime.now(),
        data_meta={"headers": detail_df.columns.tolist()}
    )
    
    test_session.add(step_file)
    test_session.add(detail_file)
    test_session.commit()
    
    # Create step records (sample, not all steps)
    steps_to_add = []
    for idx, row in step_df.head(5).iterrows():
        step = Step(
            experiment_id=experiment.id,
            step_number=int(row['step_number']),
            step_type=row['step_type'],
            start_time=row['start_time'],
            end_time=row['end_time'],
            duration=float(row['duration']),
            voltage_start=float(row.get('voltage_start', 0)),
            voltage_end=float(row['voltage_end']),
            current=float(row['current']),
            capacity=float(row['capacity']),
            energy=float(row['energy']),
            temperature_avg=float(row['temperature_avg']),
            temperature_min=float(row.get('temperature_min', row['temperature_avg'])),
            temperature_max=float(row.get('temperature_max', row['temperature_avg'])),
            c_rate=float(row['c_rate']),
            soc_start=float(row['soc_start']),
            soc_end=float(row['soc_end']),
            ocv=float(row['ocv']) if pd.notna(row['ocv']) else None
        )
        steps_to_add.append(step)
    
    test_session.add_all(steps_to_add)
    test_session.commit()
    
    # Create measurements for the first step only (to save time)
    first_step = steps_to_add[0]
    first_step_measurements = detail_df[detail_df['step_number'] == first_step.step_number].head(10)
    
    measurements_to_add = []
    for idx, row in first_step_measurements.iterrows():
        measurement = Measurement(
            step_id=first_step.id,
            timestamp=row['timestamp'],
            voltage=float(row['voltage']),
            current=float(row['current']),
            temperature=float(row['temperature']),
            capacity=float(row['capacity']),
            energy=float(row['energy']),
            soc=float(row['soc'])
        )
        measurements_to_add.append(measurement)
    
    test_session.add_all(measurements_to_add)
    test_session.commit()
    
    # Verify that we can retrieve the data
    db_experiment = test_session.get(Experiment, experiment.id)
    assert db_experiment is not None
    assert db_experiment.name == "ETL Integration Test"
    
    # Verify relationships
    assert len(db_experiment.steps) == len(steps_to_add)
    assert len(db_experiment.processed_files) == 2
    
    # Verify step data
    db_first_step = db_experiment.steps[0]
    assert db_first_step.step_number == first_step.step_number
    assert db_first_step.step_type == first_step.step_type
    
    # Verify measurements
    assert len(db_first_step.measurements) == len(measurements_to_add)
    assert db_first_step.measurements[0].voltage > 0
    
    # Clean up test data
    for step in db_experiment.steps:
        for measurement in step.measurements:
            test_session.delete(measurement)
        test_session.delete(step)
    
    for file in db_experiment.processed_files:
        test_session.delete(file)
    
    test_session.delete(db_experiment)
    test_session.commit()


def test_etl_validation(processed_data):
    """Test data validation on processed ETL data"""
    step_df = processed_data['step_df']
    detail_df = processed_data['detail_df']
    
    # Generate validation report for step data
    step_report = generate_validation_report(step_df)
    
    # Generate validation report for detail data
    detail_report = generate_validation_report(detail_df)
    
    # Check that reports were generated
    assert isinstance(step_report, dict)
    assert isinstance(detail_report, dict)
    
    # Check basic report structure
    for report in [step_report, detail_report]:
        assert 'valid' in report
        assert 'summary' in report
        assert 'validations' in report
        assert 'issues_count' in report
    
    # For valid data, check that specific validations were performed
    if step_report['valid']:
        assert 'soc_range' in step_report['validations']
        assert 'c_rate' in step_report['validations']
        
    if detail_report['valid']:
        assert 'data_continuity' in detail_report['validations']