"""
Enhanced database service with session management fix for Step data storage.
This addresses the DetachedInstanceError by providing better session management.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from sqlmodel import Session

import pandas as pd
from app.etl import convert_numpy_types
from app.models import Experiment, Measurement, ProcessedFile, Step
from app.utils.data_helpers import convert_datetime_to_python
from app.utils.database import get_session as get_db_session


def save_steps_to_db_with_session(
    session: Session,
    experiment_id: int,
    steps_df: pd.DataFrame,
    nominal_capacity: float
) -> List[Step]:
    """
    Save step data to the database using an external session.
    This prevents DetachedInstanceError by using the caller's session.
    
    Args:
        session: Database session to use
        experiment_id: ID of the experiment
        steps_df: DataFrame containing step data
        nominal_capacity: Nominal capacity of the battery
    
    Returns:
        List of created Step objects that are still attached to the session
    """
    steps = []
    
    for _, row in steps_df.iterrows():
        row_dict = convert_numpy_types(row.to_dict())

        try:
            step_number = int(row_dict.get("step_number"))
            step_type = row_dict.get("step_type")
        except Exception as e:
            print(f"步驟資料缺少必要欄位: {e}")
            continue

        start_time = convert_datetime_to_python(row_dict.get("start_time"))
        end_time = convert_datetime_to_python(row_dict.get("end_time"))

        try:
            c_rate = abs(row_dict.get("current", 0.0)) / nominal_capacity if nominal_capacity else 0.0
        except Exception as e:
            print(f"c_rate 計算錯誤: {e}")
            c_rate = 0.0

        step = Step(
            experiment_id=experiment_id,
            step_number=step_number,
            step_type=step_type,
            start_time=start_time,
            end_time=end_time,
            duration=row_dict.get("duration", 0.0),
            voltage_start=row_dict.get("voltage_start", 0.0),
            voltage_end=row_dict.get("voltage_end", 0.0),
            current=row_dict.get("current", 0.0),
            capacity=row_dict.get("capacity", 0.0),
            energy=row_dict.get("energy", 0.0),
            temperature_avg=row_dict.get("temperature_avg", 25.0),
            temperature_min=row_dict.get("temperature_min", 25.0),
            temperature_max=row_dict.get("temperature_max", 25.0),
            c_rate=c_rate,
            soc_start=row_dict.get("soc_start"),
            soc_end=row_dict.get("soc_end"),
            ocv=row_dict.get("ocv"),
            data_meta=row_dict
        )

        session.add(step)
        steps.append(step)

    # Flush to get IDs but don't commit yet - let the caller manage transactions
    session.flush()
    
    return steps


def save_steps_to_db_v2(
    experiment_id: int,
    steps_df: pd.DataFrame,
    nominal_capacity: float
) -> List[int]:
    """
    Save step data to the database and return step IDs instead of objects.
    This prevents DetachedInstanceError by returning IDs that can be used to query objects later.
    
    Args:
        experiment_id: ID of the experiment
        steps_df: DataFrame containing step data
        nominal_capacity: Nominal capacity of the battery
    
    Returns:
        List of step IDs that were created
    """
    step_ids = []
    
    with get_db_session() as session:
        for _, row in steps_df.iterrows():
            row_dict = convert_numpy_types(row.to_dict())

            try:
                step_number = int(row_dict.get("step_number"))
                step_type = row_dict.get("step_type")
            except Exception as e:
                print(f"步驟資料缺少必要欄位: {e}")
                continue

            start_time = convert_datetime_to_python(row_dict.get("start_time"))
            end_time = convert_datetime_to_python(row_dict.get("end_time"))

            try:
                c_rate = abs(row_dict.get("current", 0.0)) / nominal_capacity if nominal_capacity else 0.0
            except Exception as e:
                print(f"c_rate 計算錯誤: {e}")
                c_rate = 0.0

            step = Step(
                experiment_id=experiment_id,
                step_number=step_number,
                step_type=step_type,
                start_time=start_time,
                end_time=end_time,
                duration=row_dict.get("duration", 0.0),
                voltage_start=row_dict.get("voltage_start", 0.0),
                voltage_end=row_dict.get("voltage_end", 0.0),
                current=row_dict.get("current", 0.0),
                capacity=row_dict.get("capacity", 0.0),
                energy=row_dict.get("energy", 0.0),
                temperature_avg=row_dict.get("temperature_avg", 25.0),
                temperature_min=row_dict.get("temperature_min", 25.0),
                temperature_max=row_dict.get("temperature_max", 25.0),
                c_rate=c_rate,
                soc_start=row_dict.get("soc_start"),
                soc_end=row_dict.get("soc_end"),
                ocv=row_dict.get("ocv"),
                data_meta=row_dict
            )

            session.add(step)
            session.flush()  # Flush to get the ID
            step_ids.append(step.id)

        session.commit()

    return step_ids


def get_steps_by_ids(step_ids: List[int]) -> List[Step]:
    """
    Retrieve Step objects by their IDs.
    
    Args:
        step_ids: List of step IDs to retrieve
        
    Returns:
        List of Step objects
    """
    if not step_ids:
        return []
        
    with get_db_session() as session:
        steps = session.query(Step).filter(Step.id.in_(step_ids)).all()
        # Detach objects from the session so they can be used outside
        for step in steps:
            session.expunge(step)
        return steps


def save_experiment_and_steps_transaction(
    experiment_metadata: Dict[str, Any],
    validation_report: Dict[str, Any],
    cell_id: int,
    machine_id: int,
    battery_type: str,
    temperature_avg: float,
    steps_df: pd.DataFrame,
    nominal_capacity: float
) -> tuple[Experiment, List[Step]]:
    """
    Save experiment and steps in a single transaction.
    This ensures consistency and prevents session detachment issues.
    
    Args:
        experiment_metadata: Metadata about the experiment
        validation_report: Validation report
        cell_id: ID of the cell used in the experiment
        machine_id: ID of the machine used in the experiment
        battery_type: Type of battery used
        temperature_avg: Average temperature
        steps_df: DataFrame containing step data
        nominal_capacity: Nominal capacity of the battery
    
    Returns:
        Tuple of (Experiment, List[Step]) objects
    """
    with get_db_session() as session:
        # Create experiment
        experiment = Experiment(
            name=experiment_metadata['name'],
            description=experiment_metadata.get('description', ''),
            battery_type=battery_type,
            nominal_capacity=nominal_capacity,
            temperature_avg=temperature_avg,
            operator=experiment_metadata.get('operator', ''),
            start_date=experiment_metadata['start_date'],
            end_date=None,
            data_meta=experiment_metadata,
            validation_status=validation_report['valid'],
            validation_report=validation_report,
            cell_id=cell_id,
            machine_id=machine_id
        )
        
        session.add(experiment)
        session.flush()  # Get experiment ID
        
        # Create steps using the same session
        steps = save_steps_to_db_with_session(
            session=session,
            experiment_id=experiment.id,
            steps_df=steps_df,
            nominal_capacity=nominal_capacity
        )
        
        # Commit all changes
        session.commit()
        
        # Detach objects from session so they can be used outside
        session.expunge(experiment)
        for step in steps:
            session.expunge(step)
            
        return experiment, steps
