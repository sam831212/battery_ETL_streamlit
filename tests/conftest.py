import pytest
from sqlmodel import Session, SQLModel, create_engine
from sqlalchemy.pool import StaticPool
from app.models.database import BaseModel, Cell, Machine, Experiment, Step, Measurement, ProcessedFile

@pytest.fixture(name="db_session")
def db_session_fixture():
    """創建測試用的資料庫 session"""
    # 使用 SQLite 記憶體資料庫進行測試
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False
    )
    
    # 創建所有表格
    SQLModel.metadata.create_all(engine)
    
    # 創建 session
    with Session(engine) as session:
        yield session
        
    # 清理資料庫
    SQLModel.metadata.drop_all(engine)