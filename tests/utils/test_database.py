"""
Tests for database utility functions
"""
import pytest
from unittest.mock import patch, MagicMock
from sqlmodel import Session

from app.utils.database import (
    create_db_and_tables,
    get_session,
    init_db,
    test_db_connection
)


def test_get_session():
    """Test that get_session returns a Session object"""
    session = get_session()
    
    # Verify the session is a SQLModel Session
    assert isinstance(session, Session)
    
    # Close the session to avoid resource warnings
    session.close()


@patch('app.utils.database.SQLModel')
def test_create_db_and_tables(mock_sqlmodel):
    """Test create_db_and_tables calls SQLModel.metadata.create_all"""
    # Set up mock
    mock_metadata = MagicMock()
    mock_sqlmodel.metadata = mock_metadata
    
    # Call the function
    create_db_and_tables()
    
    # Verify the function called create_all on the metadata
    mock_metadata.create_all.assert_called_once()


@patch('app.utils.database.SQLModel')
def test_create_db_and_tables_handles_existing_tables(mock_sqlmodel):
    """Test create_db_and_tables handles the case where tables already exist"""
    # Set up mock to raise an exception with a specific message
    mock_metadata = MagicMock()
    mock_sqlmodel.metadata = mock_metadata
    mock_metadata.create_all.side_effect = Exception("Table is already defined")
    
    # Call the function - should not raise an exception
    create_db_and_tables()
    
    # Verify the function called create_all on the metadata
    mock_metadata.create_all.assert_called_once()


@patch('app.utils.database.SQLModel')
def test_create_db_and_tables_raises_unexpected_errors(mock_sqlmodel):
    """Test create_db_and_tables raises unexpected errors"""
    # Set up mock to raise an exception with a message unrelated to existing tables
    mock_metadata = MagicMock()
    mock_sqlmodel.metadata = mock_metadata
    mock_metadata.create_all.side_effect = Exception("Unexpected error")
    
    # Call the function - should raise the exception
    with pytest.raises(Exception) as exc_info:
        create_db_and_tables()
    
    # Verify the exception is the one we set up
    assert "Unexpected error" in str(exc_info.value)


@patch('app.utils.database.create_db_and_tables')
def test_init_db(mock_create_db):
    """Test init_db creates tables and returns True on success"""
    # Call the function
    result = init_db()
    
    # Verify the function called create_db_and_tables
    mock_create_db.assert_called_once()
    
    # Verify the function returned True
    assert result is True


@patch('app.utils.database.create_db_and_tables')
def test_init_db_handles_exceptions(mock_create_db):
    """Test init_db handles exceptions and returns False"""
    # Set up mock to raise an exception
    mock_create_db.side_effect = Exception("Test error")
    
    # Call the function
    result = init_db()
    
    # Verify the function called create_db_and_tables
    mock_create_db.assert_called_once()
    
    # Verify the function returned False
    assert result is False


@patch('app.utils.database.get_session')
def test_test_db_connection_success(mock_get_session):
    """Test test_db_connection returns True on successful connection"""
    # Set up mock session
    mock_session = MagicMock()
    mock_session.__enter__ = MagicMock(return_value=mock_session)
    mock_session.__exit__ = MagicMock(return_value=None)
    mock_get_session.return_value = mock_session
    
    # Call the function
    success, error = test_db_connection()
    
    # Verify the function called session.execute (we don't need to verify the exact argument)
    mock_session.execute.assert_called_once()
    
    # Verify the function returned True and None
    assert success is True
    assert error is None


@patch('app.utils.database.get_session')
def test_test_db_connection_failure(mock_get_session):
    """Test test_db_connection returns False and error message on failure"""
    # Set up mock session to raise an exception
    mock_session = MagicMock()
    mock_session.__enter__ = MagicMock(return_value=mock_session)
    mock_session.__exit__ = MagicMock(return_value=None)
    mock_session.execute.side_effect = Exception("Connection failed")
    mock_get_session.return_value = mock_session
    
    # Call the function
    success, error = test_db_connection()
    
    # Verify the function called session.execute
    mock_session.execute.assert_called_once()
    
    # Verify the function returned False and an error message
    assert success is False
    assert "Database connection error: Connection failed" in error