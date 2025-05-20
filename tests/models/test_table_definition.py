"""
Tests for table definition and model registration
"""
import pytest
from sqlmodel import SQLModel, create_engine
from sqlalchemy import MetaData
from app.models.database import (
    Cell, Machine, Experiment, Step, Measurement, 
    ProcessedFile, SavedView
)


def test_table_redefinition():
    """Test that tables can be redefined without errors"""
    # 創建一個新的 MetaData 實例
    metadata = MetaData()
    
    # 第一次定義表
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    
    # 清除所有表定義
    SQLModel.metadata.clear()
    
    # 重新導入模型
    from app.models.database import (
        Cell, Machine, Experiment, Step, Measurement, 
        ProcessedFile, SavedView
    )
    
    # 第二次定義表
    SQLModel.metadata.create_all(engine)
    
    # 如果沒有拋出異常，測試通過
    assert True


def test_model_relationships():
    """Test that model relationships are properly defined"""
    # 創建一個新的 MetaData 實例
    metadata = MetaData()
    
    # 創建引擎
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    
    # 檢查 Cell 模型的關係
    assert hasattr(Cell, 'experiments')
    assert Cell.experiments.property.back_populates == 'cell'
    
    # 檢查 Machine 模型的關係
    assert hasattr(Machine, 'experiments')
    assert Machine.experiments.property.back_populates == 'machine'
    
    # 檢查 Experiment 模型的關係
    assert hasattr(Experiment, 'cell')
    assert hasattr(Experiment, 'machine')
    assert hasattr(Experiment, 'steps')
    assert Experiment.cell.property.back_populates == 'experiments'
    assert Experiment.machine.property.back_populates == 'experiments'
    assert Experiment.steps.property.back_populates == 'experiment'
    
    # 檢查 Step 模型的關係
    assert hasattr(Step, 'experiment')
    assert hasattr(Step, 'measurements')
    assert Step.experiment.property.back_populates == 'steps'
    assert Step.measurements.property.back_populates == 'step'
    
    # 檢查 Measurement 模型的關係
    assert hasattr(Measurement, 'step')
    assert Measurement.step.property.back_populates == 'measurements'


def test_table_metadata():
    """Test that table metadata is properly set"""
    # 檢查所有表的元數據
    models = [
        Cell, Machine, Experiment, Step, 
        Measurement, ProcessedFile, SavedView
    ]
    
    for model in models:
        assert hasattr(model, '__table_args__')
        assert model.__table_args__ == {'extend_existing': True} 