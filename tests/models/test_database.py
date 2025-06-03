"""
Tests for database models
"""
import pytest
from datetime import datetime
from sqlmodel import SQLModel, create_engine, Session, select

from app.models.database import (
    BaseModel, 
    Experiment, 
    Step, 
    Measurement, 
    ProcessedFile
)


@pytest.fixture
def in_memory_db():
    """Create an in-memory SQLite database for testing"""
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture
def db_session(in_memory_db):
    """Create a new database session for a test"""
    with Session(in_memory_db) as session:
        yield session


def test_base_model_fields():
    """Test BaseModel has required fields"""
    # Verify field types in BaseModel
    from datetime import datetime
    
    # Check if the fields are defined in the model
    # We need to check the __annotations__ attribute since SQLModel fields are defined as annotations
    assert "created_at" in BaseModel.__annotations__
    assert "updated_at" in BaseModel.__annotations__
    
    # Verify that the types are correct
    assert BaseModel.__annotations__["created_at"] == datetime
    assert BaseModel.__annotations__["updated_at"] == datetime
    
    # Create an instance of a model that inherits from BaseModel to test defaults
    model = Experiment(
        name="Test",
        battery_type="Test",
        nominal_capacity=1.0,
        start_date=datetime.utcnow()
    )
    
    # Verify default values are set
    assert model.created_at is not None
    assert model.updated_at is not None
    assert isinstance(model.created_at, datetime)
    assert isinstance(model.updated_at, datetime)


def test_experiment_model(db_session):
    """Test Experiment model creation and field constraints"""    # Create a test experiment
    experiment = Experiment(
        name="Test Experiment",
        description="Test Description",
        battery_type="Li-ion",
        nominal_capacity=3.2,
        temperature=25.0,
        operator="Test Operator",
        start_date=datetime.utcnow()
    )
    
    # Add to database
    db_session.add(experiment)
    db_session.commit()
    db_session.refresh(experiment)
    
    # Verify ID was created
    assert experiment.id is not None
      # Verify fields were saved correctly
    assert experiment.name == "Test Experiment"
    assert experiment.battery_type == "Li-ion"
    assert experiment.nominal_capacity == 3.2
    
    # Verify steps relationship exists
    assert hasattr(experiment, "steps")
    assert experiment.steps == []


def test_step_model(db_session):
    """Test Step model creation and relationship to Experiment"""
    # Create an experiment first
    experiment = Experiment(
        name="Test Experiment",
        battery_type="Li-ion",
        nominal_capacity=3.2,
        start_date=datetime.utcnow()
    )
    db_session.add(experiment)
    db_session.commit()
    
    # Create a step associated with the experiment
    step = Step(
        experiment_id=experiment.id,
        step_number=1,
        step_type="charge",
        start_time=datetime.utcnow(),
        duration=3600,
        voltage_start=3.0,
        voltage_end=4.2,
        current=1.0,
        capacity=3.0,
        energy=12.0,
        temperature=25.0,
        temperature_min=24.0,
        temperature_max=26.0,
        c_rate=0.3
    )
    db_session.add(step)
    db_session.commit()
    db_session.refresh(step)
    
    # Verify ID was created
    assert step.id is not None
    
    # Verify relationship to experiment
    assert step.experiment_id == experiment.id
    assert step.experiment.id == experiment.id
    
    # Verify step appears in experiment's steps
    db_session.refresh(experiment)
    assert len(experiment.steps) == 1
    assert experiment.steps[0].id == step.id


def test_measurement_model(db_session):
    """Test Measurement model creation and relationship to Step"""
    # Create an experiment
    experiment = Experiment(
        name="Test Experiment",
        battery_type="Li-ion",
        nominal_capacity=3.2,
        start_date=datetime.utcnow()
    )
    db_session.add(experiment)
    db_session.commit()
    
    # Create a step
    step = Step(
        experiment_id=experiment.id,
        step_number=1,
        step_type="charge",
        start_time=datetime.utcnow(),
        duration=3600,
        voltage_start=3.0,
        voltage_end=4.2,
        current=1.0,
        capacity=3.0,
        energy=12.0,
        temperature=25.0,
        temperature_min=24.0,
        temperature_max=26.0,
        c_rate=0.3
    )
    db_session.add(step)
    db_session.commit()
    
    # Create measurements associated with the step
    measurements = []
    for i in range(5):
        measurement = Measurement(
            step_id=step.id,
            timestamp=datetime.utcnow(),
            voltage=3.2 + i * 0.1,
            current=1.0,
            temperature=25.0,
            capacity=i * 0.5,
            energy=i * 2.0
        )
        measurements.append(measurement)
    
    db_session.add_all(measurements)
    db_session.commit()
    
    # Verify relationships
    db_session.refresh(step)
    assert len(step.measurements) == 5
    
    # Verify measurement data
    assert step.measurements[0].step_id == step.id
    assert step.measurements[0].voltage == 3.2
    assert step.measurements[4].voltage == 3.6


def test_processed_file_model(db_session):
    """Test ProcessedFile model creation and relationship to Experiment"""
    # Create an experiment
    experiment = Experiment(
        name="Test Experiment",
        battery_type="Li-ion",
        nominal_capacity=3.2,
        start_date=datetime.utcnow()
    )
    db_session.add(experiment)
    db_session.commit()
    
    # Create a processed file record
    processed_file = ProcessedFile(
        experiment_id=experiment.id,
        filename="test_file.csv",
        file_type="step",
        file_hash="abcdef123456",
        row_count=100,
        data_meta={"headers": ["timestamp", "voltage"]}
    )
    db_session.add(processed_file)
    db_session.commit()
    db_session.refresh(processed_file)
    
    # Verify ID was created
    assert processed_file.id is not None
    
    # Verify fields were saved correctly
    assert processed_file.filename == "test_file.csv"
    assert processed_file.file_type == "step"
    assert processed_file.file_hash == "abcdef123456"
    assert processed_file.row_count == 100
    
    # Verify relationship to experiment
    assert processed_file.experiment_id == experiment.id
    assert processed_file.experiment.id == experiment.id


def test_model_relationships(db_session):
    """Test relationships between models"""
    # Create an experiment
    experiment = Experiment(
        name="Relationship Test",
        battery_type="Li-ion",
        nominal_capacity=3.2,
        start_date=datetime.utcnow()
    )
    db_session.add(experiment)
    db_session.commit()
    
    # Create two steps
    steps = []
    for i in range(2):
        step = Step(
            experiment_id=experiment.id,
            step_number=i+1,
            step_type="charge" if i == 0 else "discharge",
            start_time=datetime.utcnow(),
            duration=3600,
            voltage_start=3.0,
            voltage_end=4.2,
            current=1.0,
            capacity=3.0,
            energy=12.0,
            temperature=25.0,
            temperature_min=24.0,
            temperature_max=26.0,
            c_rate=0.3
        )
        steps.append(step)
    
    db_session.add_all(steps)
    db_session.commit()
    
    # Create measurements for each step
    for step in steps:
        for i in range(3):
            measurement = Measurement(
                step_id=step.id,
                timestamp=datetime.utcnow(),
                voltage=3.2 + i * 0.1,
                current=1.0,
                temperature=25.0,
                capacity=i * 0.5,
                energy=i * 2.0
            )
            db_session.add(measurement)
    
    # Create a processed file
    processed_file = ProcessedFile(
        experiment_id=experiment.id,
        filename="relationship_test.csv",
        file_type="step",
        file_hash="rel123456",
        row_count=100
    )
    db_session.add(processed_file)
    db_session.commit()
    
    # Verify experiment has steps
    db_session.refresh(experiment)
    assert len(experiment.steps) == 2
    
    # Verify steps have measurements
    for step in experiment.steps:
        assert len(step.measurements) == 3
    
    # Verify cascade retrieval
    # Get step by id and check parent experiment
    step_1 = db_session.exec(select(Step).where(Step.step_number == 1)).first()
    assert step_1 is not None
    assert step_1.experiment_id == experiment.id
    assert step_1.experiment.name == "Relationship Test"
    
    # Get measurement and check parent step
    measurement_1 = db_session.exec(select(Measurement)).first()
    assert measurement_1 is not None
    assert measurement_1.step is not None
    assert measurement_1.step.experiment_id == experiment.id