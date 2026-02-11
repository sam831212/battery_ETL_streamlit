import pytest
import pandas as pd
from datetime import datetime, timedelta, UTC
from app.models.database import Experiment, Step, Measurement, Cell, Machine
from app.models.enums import CellChemistry
from sqlmodel import Session, select

def save_steps_to_db(
    session: Session,
    experiment_id: int,
    steps_df: pd.DataFrame,
    nominal_capacity: float
) -> list[Step]:
    """儲存 step 資料到資料庫"""
    steps = []
    for _, row in steps_df.iterrows():
        step = Step(
            experiment_id=experiment_id,
            step_number=int(row['step_number']),
            step_type=row['step_type'],
            start_time=row['start_time'],
            end_time=row['end_time'],
            duration=float(row['duration']),
            voltage_start=float(row['voltage_start']),
            voltage_end=float(row['voltage_end']),
            current=float(row['current']),
            capacity=float(row['capacity']),
            energy=float(row['energy']),
            temperature=float(row['temperature']),
            c_rate=float(row['c_rate']),
            soc_start=float(row['soc_start']) if pd.notna(row['soc_start']) else None,
            soc_end=float(row['soc_end']) if pd.notna(row['soc_end']) else None,
            data_meta=row.get('data_meta', {})
        )
        session.add(step)
        steps.append(step)
    session.commit()
    return steps

def save_measurements_to_db(
    session: Session,
    experiment_id: int,
    details_df: pd.DataFrame,
    step_mapping: dict[int, int],
    nominal_capacity: float,
    batch_size: int = 1000
):
    """儲存 measurement 資料到資料庫"""
    detail_df_len = len(details_df)
    
    for i in range(0, detail_df_len, batch_size):
        batch = details_df.iloc[i:min(i+batch_size, detail_df_len)]
        measurements = []
        
        for _, row in batch.iterrows():
            step_number = int(row['step_number'])
            step_id = step_mapping.get(step_number)
            
            if step_id is not None:
                measurement = Measurement(
                    step_id=step_id,
                    execution_time=float(row['execution_time']),
                    voltage=float(row['voltage']),
                    current=float(row['current']),
                    temperature=float(row['temperature']),
                    capacity=float(row['capacity']),
                    energy=float(row['energy']),
                    soc=float(row['soc']) if pd.notna(row['soc']) else None
                )
                measurements.append(measurement)
        
        session.add_all(measurements)
        session.commit()

@pytest.fixture
def sample_data():
    """創建測試用的範例資料"""
    # 創建 step 資料
    step_data = {
        'step_number': [1, 2, 3],
        'step_type': ['charge', 'discharge', 'rest'],
        'start_time': [pd.Timestamp('2023-01-01 00:00:00')]*3,
        'end_time': [pd.Timestamp('2023-01-01 01:00:00')]*3,
        'duration': [3600, 3600, 3600],
        'voltage_start': [3.0, 3.2, 3.1],
        'voltage_end': [3.2, 3.1, 3.0],
        'current': [1.0, -1.0, 0.0],
        'capacity': [1.0, -1.0, 0.0],
        'energy': [3.2, 3.1, 0.0],
        'temperature': [25.0, 25.0, 25.0],
        'c_rate': [0.5, 0.5, 0.0],
        'soc_start': [0.0, 50.0, 100.0],
        'soc_end': [50.0, 100.0, 100.0],
        'data_meta': [{}, {}, {}]
    }
    step_df = pd.DataFrame(step_data)

    # 創建 detail 資料
    detail_data = {
        'step_number': [1, 1, 1, 2, 2, 2, 3, 3, 3],
        'execution_time': [0.0, 300.0, 600.0] * 3,
        'voltage': [3.0, 3.6, 4.2, 4.2, 3.6, 3.0, 4.0, 4.0, 4.0],
        'current': [1.0, 1.0, 1.0, -1.0, -1.0, -1.0, 0.0, 0.0, 0.0],
        'temperature': [25.0] * 9,
        'capacity': [0.0, 0.5, 1.0, 0.0, 1.8, 3.6, 0.0, 0.0, 0.0],
        'energy': [0.0, 1.8, 3.6, 0.0, 1.8, 3.6, 0.0, 0.0, 0.0]
    }
    detail_df = pd.DataFrame(detail_data)

    return step_df, detail_df

def test_data_storage_flow(db_session, sample_data):
    """測試完整的資料儲存流程"""
    step_df, detail_df = sample_data

    # 1. 創建 Cell 和 Machine
    cell = Cell(
        name="Test Cell",
        chemistry=CellChemistry.NMC,
        nominal_capacity=3.2
    )
    machine = Machine(
        name="Test Machine",
        description="Test Machine Description"
    )
    db_session.add_all([cell, machine])
    db_session.commit()

    # 2. 創建 Experiment
    experiment = Experiment(
        name="Test Experiment",
        description="Test Description",
        battery_type="NMC",
        nominal_capacity=3.2,
        temperature=25.0,
        operator="Test Operator",
        start_date=datetime.now(),
        cell_id=cell.id,
        machine_id=machine.id
    )
    db_session.add(experiment)
    db_session.commit()

    # 3. 儲存 Steps
    steps = save_steps_to_db(
        session=db_session,
        experiment_id=int(experiment.id),
        steps_df=step_df,
        nominal_capacity=3.2
    )

    # 驗證 Steps 是否正確儲存
    assert len(steps) == 3
    for step in steps:
        assert step.experiment_id == experiment.id
        assert step.step_number in [1, 2, 3]

    # 4. 創建 step mapping
    step_mapping = {step.step_number: int(step.id) for step in steps}

    # 5. 儲存 Measurements
    save_measurements_to_db(
        session=db_session,
        experiment_id=experiment.id,
        details_df=detail_df,
        step_mapping=step_mapping,
        nominal_capacity=3.2
    )

    # 6. 驗證資料是否正確儲存
    # 檢查 Experiment
    db_experiment = db_session.get(Experiment, experiment.id)
    assert db_experiment is not None
    assert len(db_experiment.steps) == 3

    # 檢查 Steps
    for step in db_experiment.steps:
        assert step.experiment_id == experiment.id
        # 檢查每個 step 的 measurements
        measurements = db_session.exec(
            select(Measurement).where(Measurement.step_id == step.id)
        ).all()
        assert len(measurements) == 3  # 每個 step 應該有 3 個 measurements

        # 驗證 measurement 資料
        for measurement in measurements:
            assert measurement.step_id == step.id
            assert measurement.voltage > 0
            assert measurement.current is not None
            assert measurement.temperature > 0
            assert measurement.capacity >= 0
            assert measurement.energy >= 0

    # 7. 清理測試資料
    for step in db_experiment.steps:
        for measurement in step.measurements:
            db_session.delete(measurement)
        db_session.delete(step)
    db_session.delete(db_experiment)
    db_session.delete(cell)
    db_session.delete(machine)
    db_session.commit()

def test_measurement_data_validation(db_session, sample_data):
    """測試 measurement 資料的驗證"""
    step_df, detail_df = sample_data

    # 創建基本的實驗資料
    experiment = Experiment(
        name="Validation Test",
        battery_type="NMC",
        nominal_capacity=3.2,
        start_date=datetime.now()
    )
    db_session.add(experiment)
    db_session.commit()

    # 儲存 steps
    steps = save_steps_to_db(
        session=db_session,
        experiment_id=experiment.id,
        steps_df=step_df,
        nominal_capacity=3.2
    )

    # 創建 step mapping
    step_mapping = {step.step_number: step.id for step in steps}

    # 測試無效的 step_number
    invalid_detail_df = detail_df.copy()
    invalid_detail_df.loc[0, 'step_number'] = 999  # 不存在的 step_number

    # 儲存 measurements
    save_measurements_to_db(
        session=db_session,
        experiment_id=experiment.id,
        details_df=invalid_detail_df,
        step_mapping=step_mapping,
        nominal_capacity=3.2
    )

    # 驗證只有有效的 measurements 被儲存
    total_measurements = 0
    for step in steps:
        measurements = db_session.exec(
            select(Measurement).where(Measurement.step_id == step.id)
        ).all()
        total_measurements += len(measurements)
    
    # 原始資料有 9 個 measurements，但因為一個無效的 step_number，所以應該只有 8 個被儲存
    assert total_measurements == 8

    # 清理測試資料
    for step in steps:
        for measurement in step.measurements:
            db_session.delete(measurement)
        db_session.delete(step)
    db_session.delete(experiment)
    db_session.commit()