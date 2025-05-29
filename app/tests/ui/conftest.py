import pytest
from unittest.mock import MagicMock

@pytest.fixture
def mock_db_session():
    """Fixture for a mock database session."""
    session = MagicMock()
    # Default behavior: make session.exec().all() and session.exec().one_or_none() return empty lists/None
    # to avoid StopIteration or AttributeErrors in tests not focused on specific data.
    # Specific tests will override these.
    session.exec.return_value.all.return_value = []
    session.exec.return_value.one_or_none.return_value = None
    session.get.return_value = None # For session.get(Experiment, id)
    return session
