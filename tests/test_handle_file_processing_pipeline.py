"""
Tests for the optimized handle_file_processing_pipeline function

This module tests the optimized workflow where only user-selected steps
are processed, ensuring efficient batch processing with pre-built step mappings.
"""
import pytest
import streamlit as st
import pandas as pd
from datetime import datetime, timezone
from sqlmodel import Session

from app.models import Cell, Machine, Experiment, Step, Measurement
from app.models.database import CellChemistry, CellFormFactor
from app.services.file_processing_service import handle_file_processing_pipeline
from app.utils.database import get_session as get_db_session


@pytest.fixture
def mock_session_state(monkeypatch):
    """Mock streamlit session state for testing"""
    class MockSessionState:
        def __init__(self):
            self.data = {}
            
        def __getitem__(self, key):
            return self.data[key]
            
        def __setitem__(self, key, value):
            self.data[key] = value
            
        def __contains__(self, key):
            return key in self.data
            
        def get(self, key, default=None):
            return self.data.get(key, default)
    
    mock_state = MockSessionState()
    monkeypatch.setattr("streamlit.session_state", mock_state)
    return mock_state


@pytest.fixture
def setup_test_data(db_session: Session):
    """Setup test data including cell, machine, and experiment"""
    # Create test cell
    cell = Cell(
        name="Test Cell",
        chemistry=CellChemistry.LFP,
        form_factor=CellFormFactor.PRISMATIC,
        nominal_capacity=20.0
    )
    db_session.add(cell)
    
    # Create test machine
    machine = Machine(
        name="Test Machine",
        model_number="Chroma"
    )
    db_session.add(machine)
    
    db_session.commit()
    db_session.refresh(cell)
    db_session.refresh(machine)
    
    # Create test experiment
    experiment = Experiment(
        name="Test Pipeline Experiment",
        start_date=datetime.now(timezone.utc),
        operator="TestUser",
        cell_id=cell.id,
        machine_id=machine.id,
        nominal_capacity=20.0,
        battery_type="LFP",
        temperature=25.0
    )
    db_session.add(experiment)
    db_session.commit()
    db_session.refresh(experiment)
    
    return {
        'cell': cell,
        'machine': machine,
        'experiment': experiment
    }


def test_handle_file_processing_pipeline_no_selected_steps(
    mock_session_state, 
    setup_test_data,
    db_session: Session
):
    """Test that pipeline returns early when no steps are selected"""
    
    # Setup: No selected steps in session state
    mock_session_state["selected_steps"] = []
    
    # Setup required session state variables
    test_data = setup_test_data
    mock_session_state["experiment_name"] = "Test Pipeline Experiment"
    mock_session_state["experiment_date"] = "2025-01-01"
    mock_session_state["operator"] = "TestUser"
    mock_session_state["description"] = "Test description"
    mock_session_state["nominal_capacity"] = 20.0
    mock_session_state["cell_id"] = test_data['cell'].id
    mock_session_state["machine_id"] = test_data['machine'].id
    
    # Create some test data
    step_df = pd.DataFrame({
        'step_number': [1, 2, 3],
        'step_type': ['charge', 'rest', 'discharge'],
        'current': [1.0, 0.0, -1.0],
        'duration': [3600, 600, 3600]
    })
    detail_df = pd.DataFrame({
        'step_number': [1, 1, 2, 2, 3, 3],
        'voltage': [3.3, 4.0, 4.0, 4.0, 4.0, 3.3],
        'current': [1.0, 1.0, 0.0, 0.0, -1.0, -1.0],
        'temperature': [25.0, 25.1, 25.2, 25.3, 25.4, 25.5]
    })
    
    test_data = setup_test_data
    
    # Execute
    file_data = {
        'step_df': step_df,
        'detail_df': detail_df,
        'step_file_path': 'test_step.csv',
        'detail_file_path': 'test_detail.csv',
        'step_file_hash': 'test_step_hash',
        'detail_file_hash': 'test_detail_hash',
        'step_filename': 'test_step.csv',
        'detail_filename': 'test_detail.csv',
        'is_uploaded_file': False
    }
    
    success = handle_file_processing_pipeline(file_data)
    
    # Verify: Should return False (failure) due to no selected steps
    assert success is False
    
    # Verify: No data should be saved to database
    steps_count = db_session.query(Step).filter(Step.experiment_id == test_data['experiment'].id).count()
    measurements_count = db_session.query(Measurement).join(Step).filter(Step.experiment_id == test_data['experiment'].id).count()
    
    assert steps_count == 0
    assert measurements_count == 0


def test_handle_file_processing_pipeline_with_selected_steps(
    mock_session_state,
    setup_test_data,
    db_session: Session
):
    """Test optimized pipeline with user-selected steps"""
    
    # Setup required session state variables first
    test_data = setup_test_data
    mock_session_state["experiment_name"] = "Test Pipeline Experiment"
    mock_session_state["experiment_date"] = "2025-01-01"
    mock_session_state["operator"] = "TestUser"
    mock_session_state["description"] = "Test description"
    mock_session_state["nominal_capacity"] = 20.0
    mock_session_state["cell_id"] = test_data['cell'].id
    mock_session_state["machine_id"] = test_data['machine'].id
    
    # Setup: Selected steps in session state (only step 1 and 3)
    mock_session_state["selected_steps"] = [
        {
            'step_number': 1,
            'step_type': 'charge',
            'current': 1.0,
            'duration': 3600
        },
        {
            'step_number': 3,
            'step_type': 'discharge',
            'current': -1.0,
            'duration': 3600
        }
    ]
    
    # Create test data with 3 steps, but only 1 and 3 should be processed
    step_df = pd.DataFrame({
        'step_number': [1, 2, 3],
        'step_type': ['charge', 'rest', 'discharge'],
        'current': [1.0, 0.0, -1.0],
        'duration': [3600, 600, 3600],
        'voltage_start': [3.3, 4.0, 4.0],
        'voltage_end': [4.0, 4.0, 3.3],
        'capacity': [2.0, 2.0, 0.0],
        'energy': [7.0, 7.0, 0.0],
        'temperature': [25.0, 25.5, 26.0],
        'start_time': [
            datetime(2025, 1, 1, 10, 0, 0),
            datetime(2025, 1, 1, 11, 0, 0),
            datetime(2025, 1, 1, 12, 0, 0)
        ],
        'end_time': [
            datetime(2025, 1, 1, 11, 0, 0),
            datetime(2025, 1, 1, 11, 10, 0),
            datetime(2025, 1, 1, 13, 0, 0)
        ]
    })
    
    detail_df = pd.DataFrame({
        'step_number': [1, 1, 2, 2, 3, 3],
        'voltage': [3.3, 4.0, 4.0, 4.0, 4.0, 3.3],
        'current': [1.0, 1.0, 0.0, 0.0, -1.0, -1.0],
        'temperature': [25.0, 25.1, 25.2, 25.3, 25.4, 25.5],
        'capacity': [0.5, 1.0, 1.0, 1.0, 0.5, 0.0],
        'energy': [1.5, 3.0, 3.0, 3.0, 1.5, 0.0],
        'execution_time': [1800, 3600, 300, 600, 1800, 3600]
    })
    
    test_data = setup_test_data
    
    # Execute
    file_data = {
        'step_df': step_df,
        'detail_df': detail_df,
        'step_file_path': 'test_step.csv',
        'detail_file_path': 'test_detail.csv',
        'step_file_hash': 'test_step_hash',
        'detail_file_hash': 'test_detail_hash',
        'step_filename': 'test_step.csv',
        'detail_filename': 'test_detail.csv',
        'is_uploaded_file': False
    }
    
    success = handle_file_processing_pipeline(file_data)
    
    # Verify: Should return True (success)
    assert success is True
    
    # Verify: Only selected steps (1 and 3) should be saved, not step 2
    saved_steps = db_session.query(Step).filter(Step.experiment_id == test_data['experiment'].id).all()
    assert len(saved_steps) == 2
    
    saved_step_numbers = [step.step_number for step in saved_steps]
    assert 1 in saved_step_numbers
    assert 3 in saved_step_numbers
    assert 2 not in saved_step_numbers  # Step 2 should not be saved since it wasn't selected
    
    # Verify: All saved steps should have valid IDs (not None)
    for step in saved_steps:
        assert step.id is not None
    
    # Verify: Only measurements for selected steps should be saved
    saved_measurements = db_session.query(Measurement).join(Step).filter(
        Step.experiment_id == test_data['experiment'].id
    ).all()
    
    # Should have 4 measurements total (2 for step 1, 2 for step 3)
    assert len(saved_measurements) == 4
    
    # Verify: All measurements should have valid step_ids
    for measurement in saved_measurements:
        assert measurement.step_id is not None
        
    # Verify: Measurements should only belong to steps 1 and 3
    measurement_step_numbers = []
    for measurement in saved_measurements:
        step = db_session.get(Step, measurement.step_id)
        measurement_step_numbers.append(step.step_number)
    
    assert all(step_num in [1, 3] for step_num in measurement_step_numbers)
    assert 2 not in measurement_step_numbers  # No measurements for unselected step 2


def test_handle_file_processing_pipeline_step_mapping_validation(
    mock_session_state,
    setup_test_data,
    db_session: Session
):
    """Test that step mapping validation works correctly"""
    
    # Setup required session state variables first
    test_data = setup_test_data
    mock_session_state["experiment_name"] = "Test Pipeline Experiment"
    mock_session_state["experiment_date"] = "2025-01-01"
    mock_session_state["operator"] = "TestUser"
    mock_session_state["description"] = "Test description"
    mock_session_state["nominal_capacity"] = 20.0
    mock_session_state["cell_id"] = test_data['cell'].id
    mock_session_state["machine_id"] = test_data['machine'].id
    
    # Setup: Selected step that exists in step_df
    mock_session_state["selected_steps"] = [
        {
            'step_number': 1,
            'step_type': 'charge'
        }
    ]
    
    # Create step_df with the selected step
    step_df = pd.DataFrame({
        'step_number': [1],
        'step_type': ['charge'],
        'current': [1.0],
        'duration': [3600],
        'voltage_start': [3.3],
        'voltage_end': [4.0],
        'capacity': [2.0],
        'energy': [7.0],
        'temperature': [25.0],
        'start_time': [datetime(2025, 1, 1, 10, 0, 0)],
        'end_time': [datetime(2025, 1, 1, 11, 0, 0)]
    })
    
    # Create detail_df with measurements for the selected step
    detail_df = pd.DataFrame({
        'step_number': [1, 1],
        'voltage': [3.3, 4.0],
        'current': [1.0, 1.0],
        'temperature': [25.0, 25.1],
        'capacity': [0.5, 1.0],
        'energy': [1.5, 3.0],
        'execution_time': [1800, 3600]
    })
    
    test_data = setup_test_data
    
    # Execute
    file_data = {
        'step_df': step_df,
        'detail_df': detail_df,
        'step_file_path': 'test_step.csv',
        'detail_file_path': 'test_detail.csv',
        'step_file_hash': 'test_step_hash',
        'detail_file_hash': 'test_detail_hash',
        'step_filename': 'test_step.csv',
        'detail_filename': 'test_detail.csv',
        'is_uploaded_file': False
    }
    
    success = handle_file_processing_pipeline(file_data)
    
    # Verify: Should succeed
    assert success is True
    
    # Verify: Step mapping should be complete and valid
    saved_steps = db_session.query(Step).filter(Step.experiment_id == test_data['experiment'].id).all()
    assert len(saved_steps) == 1
    assert saved_steps[0].step_number == 1
    assert saved_steps[0].id is not None
    
    # Verify: Measurements should be correctly linked
    saved_measurements = db_session.query(Measurement).filter(Measurement.step_id == saved_steps[0].id).all()
    assert len(saved_measurements) == 2
    
    for measurement in saved_measurements:
        assert measurement.step_id == saved_steps[0].id


def test_handle_file_processing_pipeline_efficiency(
    mock_session_state,
    setup_test_data,
    db_session: Session
):
    """Test that the optimized pipeline is efficient (processes only selected steps)"""
    
    # Setup required session state variables first
    test_data = setup_test_data
    mock_session_state["experiment_name"] = "Test Pipeline Experiment"
    mock_session_state["experiment_date"] = "2025-01-01"
    mock_session_state["operator"] = "TestUser"
    mock_session_state["description"] = "Test description"
    mock_session_state["nominal_capacity"] = 20.0
    mock_session_state["cell_id"] = test_data['cell'].id
    mock_session_state["machine_id"] = test_data['machine'].id
    
    # Setup: Select only 2 out of 5 steps
    mock_session_state["selected_steps"] = [
        {'step_number': 2, 'step_type': 'charge'},
        {'step_number': 4, 'step_type': 'discharge'}
    ]
    
    # Create data with 5 steps total
    step_df = pd.DataFrame({
        'step_number': [1, 2, 3, 4, 5],
        'step_type': ['rest', 'charge', 'rest', 'discharge', 'rest'],
        'current': [0.0, 1.0, 0.0, -1.0, 0.0],
        'duration': [600, 3600, 600, 3600, 600],
        'voltage_start': [3.3, 3.3, 4.0, 4.0, 3.3],
        'voltage_end': [3.3, 4.0, 4.0, 3.3, 3.3],
        'capacity': [0.0, 2.0, 2.0, 0.0, 0.0],
        'energy': [0.0, 7.0, 7.0, 0.0, 0.0],
        'temperature': [25.0, 25.1, 25.2, 25.3, 25.4],
        'start_time': [
            datetime(2025, 1, 1, 10, 0, 0),
            datetime(2025, 1, 1, 10, 10, 0),
            datetime(2025, 1, 1, 11, 10, 0),
            datetime(2025, 1, 1, 11, 20, 0),
            datetime(2025, 1, 1, 12, 20, 0)
        ],
        'end_time': [
            datetime(2025, 1, 1, 10, 10, 0),
            datetime(2025, 1, 1, 11, 10, 0),
            datetime(2025, 1, 1, 11, 20, 0),
            datetime(2025, 1, 1, 12, 20, 0),
            datetime(2025, 1, 1, 12, 30, 0)
        ]
    })
    
    # Create detail data for all steps
    detail_data = []
    for step_num in [1, 2, 3, 4, 5]:
        for i in range(3):  # 3 measurements per step
            detail_data.append({
                'step_number': step_num,
                'voltage': 3.5 + step_num * 0.1,
                'current': step_num * 0.5,
                'temperature': 25.0 + step_num * 0.1,
                'capacity': step_num * 0.5,
                'energy': step_num * 1.0,
                'execution_time': i * 1000 + step_num * 100
            })
    
    detail_df = pd.DataFrame(detail_data)
    
    test_data = setup_test_data
    
    # Execute
    file_data = {
        'step_df': step_df,
        'detail_df': detail_df,
        'step_file_path': 'test_step.csv',
        'detail_file_path': 'test_detail.csv',
        'step_file_hash': 'test_step_hash',
        'detail_file_hash': 'test_detail_hash',
        'step_filename': 'test_step.csv',
        'detail_filename': 'test_detail.csv',
        'is_uploaded_file': False
    }
    
    success = handle_file_processing_pipeline(file_data)
    
    # Verify: Should succeed
    assert success is True
    
    # Verify: Only 2 steps should be saved (the selected ones: 2 and 4)
    saved_steps = db_session.query(Step).filter(Step.experiment_id == test_data['experiment'].id).all()
    assert len(saved_steps) == 2
    
    saved_step_numbers = [step.step_number for step in saved_steps]
    assert set(saved_step_numbers) == {2, 4}
    
    # Verify: Only measurements for selected steps should be saved (6 total: 3 for each of 2 steps)
    saved_measurements = db_session.query(Measurement).join(Step).filter(
        Step.experiment_id == test_data['experiment'].id
    ).all()
    assert len(saved_measurements) == 6
    
    # Verify: All measurements belong to the selected steps
    measurement_step_numbers = set()
    for measurement in saved_measurements:
        step = db_session.get(Step, measurement.step_id)
        measurement_step_numbers.add(step.step_number)
    
    assert measurement_step_numbers == {2, 4}
