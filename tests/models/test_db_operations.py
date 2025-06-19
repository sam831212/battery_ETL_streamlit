"""
Tests for database operations and model functionality
"""
import pytest
from datetime import datetime, timedelta
from sqlmodel import SQLModel, create_engine, Session, select

from app.models.database import (
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


@pytest.fixture
def sample_data(db_session):
    """Create a complete sample dataset for testing queries"""
    # Create experiments
    experiments = []
    for i in range(3):
        experiment = Experiment(
            name=f"Test Experiment {i+1}",
            description=f"Description for experiment {i+1}",
            battery_type=["Li-ion", "NMC", "LFP"][i % 3],
            nominal_capacity=3.0 + i * 0.5,
            temperature=25.0 + i,
            operator=f"Operator {i+1}",
            start_date=datetime.utcnow() - timedelta(days=i),
            end_date=datetime.utcnow() if i < 2 else None
        )
        experiments.append(experiment)
    
    db_session.add_all(experiments)
    db_session.commit()
    
    # Create steps for each experiment
    all_steps = []
    step_types = ["charge", "discharge", "rest"]
    
    for i, experiment in enumerate(experiments):
        # Add 3 steps to each experiment
        for j in range(3):
            step = Step(
                experiment_id=experiment.id,
                step_number=j+1,
                step_type=step_types[j % 3],
                duration=3600,
                voltage_start=3.0 + j * 0.2,
                voltage_end=3.0 + (j+1) * 0.2,
                current=1.0 - (0.2 * j),
                capacity=j * 0.5,
                energy=j * 2.0,
                c_rate=0.3 - (0.1 * j),
                soc_start=20.0 + j * 10,
                soc_end=30.0 + j * 10,
                ocv=3.8 if j == 2 else None  # Only set OCV for rest steps
            )
            all_steps.append(step)
    
    db_session.add_all(all_steps)
    db_session.commit()
    
    # Create measurements for each step
    all_measurements = []
    for step in all_steps:
        # Add 5 measurements per step
        for k in range(5):
            measurement = Measurement(
                step_id=step.id,
                timestamp=step.start_time + timedelta(minutes=k*10),
                voltage=step.voltage_start + (step.voltage_end - step.voltage_start) * k / 4,
                current=step.current,
                temperature=step.temperature + (k - 2) * 0.2,
                capacity=step.capacity * k / 4,
                energy=step.energy * k / 4,
                soc=step.soc_start + (step.soc_end - step.soc_start) * k / 4 if step.soc_start is not None else None
            )
            all_measurements.append(measurement)
    
    db_session.add_all(all_measurements)
    
    # Create processed files
    files = []
    for i, experiment in enumerate(experiments):
        for file_type in ["step", "detail"]:
            processed_file = ProcessedFile(
                experiment_id=experiment.id,
                filename=f"test_file_{i}_{file_type}.csv",
                file_type=file_type,
                file_hash=f"hash_{i}_{file_type}",
                row_count=100 + i * 50,
                data_meta={"headers": ["timestamp", "voltage", "current"]}
            )
            files.append(processed_file)
    
    db_session.add_all(files)
    db_session.commit()
    
    return {
        "experiments": experiments,
        "steps": all_steps,
        "measurements": all_measurements,
        "files": files
    }


def test_experiment_querying(db_session, sample_data):
    """Test querying experiment data"""
    # Get all experiments
    experiments = db_session.exec(select(Experiment)).all()
    assert len(experiments) == 3
    
    # Query by name
    experiment = db_session.exec(
        select(Experiment).where(Experiment.name == "Test Experiment 1")
    ).first()
    assert experiment is not None
    assert experiment.name == "Test Experiment 1"
    
    # Query by battery type
    li_ion_experiments = db_session.exec(
        select(Experiment).where(Experiment.battery_type == "Li-ion")
    ).all()
    assert len(li_ion_experiments) > 0
    
    # Query with multiple conditions
    filtered_experiments = db_session.exec(
        select(Experiment).where(
            Experiment.end_date != None,
            Experiment.temperature > 25.0
        )
    ).all()
    assert len(filtered_experiments) > 0


def test_step_querying(db_session, sample_data):
    """Test querying step data"""
    # Get all steps
    steps = db_session.exec(select(Step)).all()
    assert len(steps) == 9  # 3 steps for each of 3 experiments
    
    # Query by step type
    charge_steps = db_session.exec(
        select(Step).where(Step.step_type == "charge")
    ).all()
    assert len(charge_steps) == 3
    
    # Query with join to experiment
    steps_with_experiment = db_session.exec(
        select(Step, Experiment).join(Experiment).where(
            Experiment.name == "Test Experiment 1"
        )
    ).all()
    assert len(steps_with_experiment) == 3
    
    # Query with ordering
    ordered_steps = db_session.exec(
        select(Step).order_by(Step.c_rate.desc())
    ).all()
    assert ordered_steps[0].c_rate >= ordered_steps[-1].c_rate


def test_measurement_querying(db_session, sample_data):
    """Test querying measurement data"""
    # Get all measurements
    measurements = db_session.exec(select(Measurement)).all()
    assert len(measurements) == 45  # 5 measurements for each of 9 steps
    
    # Get measurements for a specific step
    step_1 = db_session.exec(
        select(Step).where(
            Step.experiment_id == sample_data["experiments"][0].id,
            Step.step_number == 1
        )
    ).first()
    
    step_measurements = db_session.exec(
        select(Measurement).where(
            Measurement.step_id == step_1.id
        )
    ).all()
    assert len(step_measurements) == 5
    
    # Query with complex joins
    # Get all measurements for a specific experiment
    experiment_measurements = db_session.exec(
        select(Measurement)
        .join(Step)
        .join(Experiment)
        .where(Experiment.name == "Test Experiment 1")
    ).all()
    assert len(experiment_measurements) == 15  # 5 measurements for each of 3 steps


def test_processed_file_querying(db_session, sample_data):
    """Test querying processed file data"""
    # Get all processed files
    processed_files = db_session.exec(select(ProcessedFile)).all()
    assert len(processed_files) == 6  # 2 files for each of 3 experiments
    
    # Query by file type
    step_files = db_session.exec(
        select(ProcessedFile).where(
            ProcessedFile.file_type == "step"
        )
    ).all()
    assert len(step_files) == 3
    
    # Query with join to experiment
    files_with_experiment = db_session.exec(
        select(ProcessedFile, Experiment.name)
        .join(Experiment)
        .where(Experiment.name.like("%Test%"))
    ).all()
    assert len(files_with_experiment) == 6