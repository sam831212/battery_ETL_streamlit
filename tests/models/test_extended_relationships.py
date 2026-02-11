"""
Tests for relationships between Cell, Machine, and Experiment models
"""
import pytest
from datetime import datetime
from sqlmodel import SQLModel, create_engine, Session, select

from app.models.database import (
    BaseModel, 
    Experiment,
    Step,
    Cell,
    Machine,
    SavedView
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


def test_experiment_with_cell_and_machine(db_session):
    """Test relationships between Experiment, Cell, and Machine"""
    # Create Cell
    cell = Cell(
        chemistry="LFP",
        capacity=3.2,
        form="PRISMATIC"
    )
    db_session.add(cell)
    
    # Create Machine
    machine = Machine(
        name="Test Machine",
        description="Battery testing equipment",
        model_number="BT-2000"
    )
    db_session.add(machine)
    db_session.commit()
    
    # Create Experiment with references to Cell and Machine
    experiment = Experiment(
        name="Relationship Test",
        battery_type="LFP",
        nominal_capacity=3.2,
        start_date=datetime.utcnow(),
        cell_id=cell.id,
        machine_id=machine.id
    )
    db_session.add(experiment)
    db_session.commit()
    db_session.refresh(experiment)
    
    # Verify relationships
    assert experiment.cell_id == cell.id
    assert experiment.cell.chemistry == "LFP"
    assert experiment.machine_id == machine.id
    assert experiment.machine.name == "Test Machine"
    
    # Verify bidirectional relationships (if implemented)
    db_session.refresh(cell)
    db_session.refresh(machine)
    if hasattr(cell, 'experiments'):
        assert len(cell.experiments) == 1
        assert cell.experiments[0].id == experiment.id
    
    if hasattr(machine, 'experiments'):
        assert len(machine.experiments) == 1
        assert machine.experiments[0].id == experiment.id