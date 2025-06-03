"""
Integration tests for the Battery ETL Dashboard

These tests verify that database models and connections work with 
a real test database environment.
"""
import os
import pytest
from sqlalchemy import text
from sqlmodel import SQLModel, create_engine, Session, select
from datetime import datetime, timedelta

from app.models.database import (
    Experiment, 
    Step, 
    Measurement, 
    ProcessedFile
)
from app.utils.database import get_session


# Test database URL - use an environment variable or default to SQLite in-memory
TEST_DB_URL = os.environ.get("TEST_DATABASE_URL", "sqlite:///:memory:")


@pytest.fixture(scope="module")
def test_engine():
    """Create a test database engine for integration tests"""
    # Create engine
    engine = create_engine(TEST_DB_URL, echo=False)
    
    # Create tables
    SQLModel.metadata.create_all(engine)
    
    yield engine
    
    # Clean up (if needed)
    if TEST_DB_URL == "sqlite:///:memory:":
        # Only needed for in-memory database
        SQLModel.metadata.drop_all(engine)


@pytest.fixture
def test_session(test_engine):
    """Create a database session for tests"""
    with Session(test_engine) as session:
        yield session
        # Roll back any changes from the test
        session.rollback()


@pytest.fixture
def sample_experiment(test_session):
    """Create a sample experiment for testing"""
    experiment = Experiment(
        name="Integration Test Experiment",
        description="Test for integration testing",
        battery_type="Li-ion",
        nominal_capacity=3.2,
        temperature=25.0,
        operator="Test Operator",
        start_date=datetime.utcnow() - timedelta(days=1),
        end_date=datetime.utcnow(),
        data_meta={"source": "integration_test"}
    )
    test_session.add(experiment)
    test_session.commit()
    test_session.refresh(experiment)
    
    return experiment


@pytest.fixture
def sample_data(test_session, sample_experiment):
    """Create complete sample data structure for testing"""
    # Create steps
    step_types = ["charge", "discharge", "rest"]
    steps = []
    
    for i in range(3):
        step = Step(
            experiment_id=sample_experiment.id,
            step_number=i+1,
            step_type=step_types[i],
            start_time=sample_experiment.start_date + timedelta(hours=i),
            end_time=sample_experiment.start_date + timedelta(hours=i+1),
            duration=3600,
            voltage_start=3.0 + i * 0.2,
            voltage_end=3.0 + (i+1) * 0.2,
            current=1.0 if i != 2 else 0.0,  # 0 current for rest
            capacity=i * 0.5,
            energy=i * 2.0,
            temperature=25.0,
            c_rate=0.3 if i != 2 else 0.0,  # 0 C-rate for rest
            soc_start=20.0 + i * 10,
            soc_end=30.0 + i * 10,
            ocv=None if i != 2 else 3.8  # OCV only for rest
        )
        steps.append(step)
    
    test_session.add_all(steps)
    test_session.commit()
    
    # Create measurements for each step
    for step in steps:
        for j in range(10):
            measurement = Measurement(
                step_id=step.id,
                timestamp=step.start_time + timedelta(minutes=j*6),
                voltage=step.voltage_start + (step.voltage_end - step.voltage_start) * j / 9,
                current=step.current,
                temperature=25.0 + j * 0.1,
                capacity=step.capacity * j / 9,
                energy=step.energy * j / 9,
                soc=step.soc_start + (step.soc_end - step.soc_start) * j / 9
            )
            test_session.add(measurement)
    
    # Create processed file record
    processed_file = ProcessedFile(
        experiment_id=sample_experiment.id,
        filename="integration_test.csv",
        file_type="step",
        file_hash="integration123",
        row_count=30,
        data_meta={"headers": ["step", "timestamp", "voltage", "current"]}
    )
    test_session.add(processed_file)
    test_session.commit()
    
    return {
        "experiment": sample_experiment,
        "steps": steps,
        "processed_file": processed_file
    }


def test_database_connection(test_engine):
    """Test that we can connect to the database"""
    # Just execute a simple query to verify connection
    with Session(test_engine) as session:
        result = session.execute(text("SELECT 1")).first()
        assert result[0] == 1


def test_experiment_crud(test_session):
    """Test Create, Read, Update, Delete operations for Experiment model"""
    # Create
    experiment = Experiment(
        name="CRUD Test",
        battery_type="NMC",
        nominal_capacity=2.5,
        start_date=datetime.utcnow()
    )
    test_session.add(experiment)
    test_session.commit()
    test_session.refresh(experiment)
    
    # Read
    retrieved = test_session.get(Experiment, experiment.id)
    assert retrieved is not None
    assert retrieved.name == "CRUD Test"
    assert retrieved.battery_type == "NMC"
    
    # Update
    retrieved.description = "Updated description"
    retrieved.operator = "CRUD Tester"
    test_session.commit()
    test_session.refresh(retrieved)
    
    assert retrieved.description == "Updated description"
    assert retrieved.operator == "CRUD Tester"
    
    # Delete
    test_session.delete(retrieved)
    test_session.commit()
    
    deleted = test_session.get(Experiment, experiment.id)
    assert deleted is None


def test_relationships(sample_data):
    """Test relationships between models with sample data"""
    experiment = sample_data["experiment"]
    steps = sample_data["steps"]
    
    # Test experiment to steps relationship
    assert len(experiment.steps) == 3
    
    # Test step to experiment relationship
    for step in steps:
        assert step.experiment.id == experiment.id
    
    # Test step to measurements relationship
    for step in steps:
        assert len(step.measurements) == 10
        
        # Check that measurements have the correct step_id
        for measurement in step.measurements:
            assert measurement.step_id == step.id


def test_query_experiments(test_session):
    """Test querying experiments"""
    # Create a new experiment first for this test
    experiment = Experiment(
        name="Query Test Experiment",
        description="For testing queries only",
        battery_type="NMC",
        nominal_capacity=3.0,
        start_date=datetime.utcnow()
    )
    test_session.add(experiment)
    test_session.commit()
    
    # Get all experiments
    experiments = test_session.exec(select(Experiment)).all()
    assert len(experiments) >= 1
    
    # Find specific experiment
    queried_experiment = test_session.exec(
        select(Experiment).where(Experiment.name == "Query Test Experiment")
    ).first()
    
    assert queried_experiment is not None
    assert queried_experiment.id == experiment.id
    
    # Create step for join testing
    step = Step(
        experiment_id=experiment.id,
        step_number=1,
        step_type="test",
        start_time=datetime.utcnow(),
        duration=100,
        voltage_start=3.0,
        voltage_end=4.0,
        current=1.0,
        capacity=2.0,
        energy=8.0,
        temperature=25.0,
        c_rate=0.5
    )
    test_session.add(step)
    test_session.commit()
    
    # Test querying with joins
    steps_with_experiment = test_session.exec(
        select(Step, Experiment.name)
        .join(Experiment)
        .where(Experiment.id == experiment.id)
    ).all()
    
    assert len(steps_with_experiment) >= 1
    for step, exp_name in steps_with_experiment:
        assert step.experiment.name == "Query Test Experiment"
        
    # Clean up
    # First delete all steps associated with the experiment
    for step_obj in test_session.exec(select(Step).where(Step.experiment_id == experiment.id)).all():
        test_session.delete(step_obj)
    
    # Then delete the experiment
    test_session.delete(experiment)
    test_session.commit()