"""
Tests for Cell and Machine models
"""
import pytest
from datetime import datetime
from sqlmodel import SQLModel, create_engine, Session, select

from app.models.database import (
    BaseModel, 
    Experiment,
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


def test_cell_model_creation(db_session):
    """Test creating a Cell model and verifying its fields"""
    cell = Cell(
        chemistry="NMC",
        capacity=3.2,
        form="cylindrical"
    )
    db_session.add(cell)
    db_session.commit()
    db_session.refresh(cell)
    
    # Verify ID was created and fields were saved
    assert cell.id is not None
    assert cell.chemistry == "NMC"
    assert cell.capacity == 3.2
    assert cell.form == "cylindrical"
    assert cell.created_at is not None


def test_cell_model_constraints(db_session):
    """Test field constraints on Cell model"""
    # Test required fields - chemistry should be required
    with pytest.raises(Exception):
        invalid_cell = Cell(capacity=3.0, form="cylindrical")  # Missing chemistry
        db_session.add(invalid_cell)
        db_session.commit()


def test_machine_model_creation(db_session):
    """Test creating a Machine model and verifying its fields"""
    machine = Machine(
        name="Test Machine",
        description="Battery testing equipment",
        model_number="TM-456"
    )
    db_session.add(machine)
    db_session.commit()
    db_session.refresh(machine)
    
    # Verify ID was created and fields were saved
    assert machine.id is not None
    assert machine.name == "Test Machine"
    assert machine.description == "Battery testing equipment"
    assert machine.model_number == "TM-456"
    assert machine.created_at is not None


def test_machine_model_constraints(db_session):
    """Test field constraints on Machine model"""
    # Test required fields - name should be required
    with pytest.raises(Exception):
        invalid_machine = Machine(description="Missing name")  # Missing name
        db_session.add(invalid_machine)
        db_session.commit()


def test_savedview_model_creation(db_session):
    """Test creating a SavedView model and verifying its fields"""
    view = SavedView(
        name="Test View",
        description="Dashboard configuration for test battery",
        view_config={"charts": ["voltage", "current"], "timespan": "1h"}
    )
    db_session.add(view)
    db_session.commit()
    db_session.refresh(view)
    
    # Verify ID was created and fields were saved
    assert view.id is not None
    assert view.name == "Test View"
    assert view.description == "Dashboard configuration for test battery"
    assert view.view_config == {"charts": ["voltage", "current"], "timespan": "1h"}
    assert view.created_at is not None


def test_savedview_model_constraints(db_session):
    """Test field constraints on SavedView model"""
    # Test required fields - name should be required
    with pytest.raises(Exception):
        invalid_view = SavedView(view_config={"charts": ["voltage"]})  # Missing name
        db_session.add(invalid_view)
        db_session.commit()