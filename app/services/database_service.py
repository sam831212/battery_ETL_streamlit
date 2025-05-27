"""Helper functions for direct database interactions."""


from datetime import datetime
from typing import Any, Dict, List

import pandas as pd
from app.etl import convert_numpy_types
from app.models import Experiment, Measurement, ProcessedFile, Step
from app.utils.data_helpers import convert_datetime_to_python
from app.utils.database import get_session as get_db_session


def check_file_already_processed(file_hash: str) -> bool:
    """
    Check if a file with the given hash has already been processed.

    Args:
        file_hash: Hash value of the file

    Returns:
        True if already processed, False otherwise
    """
    if not file_hash:
        return False

    try:
        with get_db_session() as session:
            # Check if any ProcessedFile with this hash exists
            existing_file = session.query(ProcessedFile).filter(
                ProcessedFile.file_hash.__eq__(file_hash)
            ).first()

            return existing_file is not None
    except Exception as e:
        # If database connection fails, reset connection and try again
        try:
            with get_db_session() as session:
                existing_file = session.query(ProcessedFile).filter(
                    ProcessedFile.file_hash == file_hash
                ).first()

                return existing_file is not None
        except Exception as retry_error:
            # Log the error and assume file has not been processed
            print(f"Database error in check_file_already_processed: {str(retry_error)}")
            return False


def save_experiment_to_db(
    experiment_metadata: Dict[str, Any],
    validation_report: Dict[str, Any],
    cell_id: int,
    machine_id: int,
    battery_type: str,
    temperature_avg: float
) -> Experiment:
    """
    Create and save a new experiment record in the database.

    Args:
        experiment_metadata: Metadata about the experiment
        validation_report: Validation report
        cell_id: ID of the cell used in the experiment
        machine_id: ID of the machine used in the experiment
        battery_type: Type of battery used
        temperature_avg: Average temperature

    Returns:
        Created Experiment object
    """
    experiment = Experiment(
        name=experiment_metadata['name'],
        description=experiment_metadata.get('description', ''),
        battery_type=battery_type,
        nominal_capacity=experiment_metadata['nominal_capacity'],
        temperature_avg=temperature_avg,  # Convert numpy.float64 to Python float
        operator=experiment_metadata.get('operator', ''),
        start_date=experiment_metadata['start_date'],
        end_date=None,  # Will be updated after processing
        data_meta=experiment_metadata,
        validation_status=validation_report['valid'],
        validation_report=validation_report,
        cell_id=cell_id,
        machine_id=machine_id
    )

    with get_db_session() as session:
        session.add(experiment)
        session.commit()
        session.refresh(experiment)

    return experiment


def save_measurements_to_db(
    experiment_id: int,
    details_df: pd.DataFrame,
    step_mapping: Dict[int, int],
    nominal_capacity: float,
    batch_size: int = 1000
):
    """保存測量數據到資料庫"""
    print("===== DEBUG: save_measurements_to_db =====")
    print(f"Experiment ID: {experiment_id}")
    print(f"Details DataFrame length: {len(details_df)}")
    print(f"Step mapping: {step_mapping}")

    if details_df.empty:
        print("警告：沒有測量數據需要保存")
        return

    required_columns = ['step_number', 'execution_time', 'voltage', 'current']
    missing_columns = [col for col in required_columns if col not in details_df.columns]
    if missing_columns:
        print(f"警告：缺少必要的列：{missing_columns}")
        return

    if not step_mapping:
        print("警告：步驟映射為空")
        return

    with get_db_session() as session:
        total_saved = 0
        total_errors = 0

        # 將 DataFrame 分成批次處理
        for i in range(0, len(details_df), batch_size):
            batch_df = details_df.iloc[i:i + batch_size]
            measurements = []

            for _, row in batch_df.iterrows():
                try:
                    # 轉換數據類型並四捨五入到適當的小數位數
                    step_number = int(row['step_number'])
                    if step_number not in step_mapping:
                        continue

                    step_id = step_mapping[step_number]
                    execution_time = float(row['execution_time'])
                    voltage = round(float(row['voltage']), 3)  # 保留3位小數
                    current = round(float(row['current']), 3)  # 保留3位小數
                    temperature = round(float(row.get('temperature', 25.0)), 1)  # 保留1位小數
                    capacity = round(float(row.get('capacity', 0.0)), 3)  # 保留3位小數
                    energy = round(float(row.get('energy', 0.0)), 3)  # 保留3位小數
                    soc = round(float(row.get('soc', 0.0)), 1) if pd.notna(row.get('soc')) else None  # 保留1位小數

                    measurement = Measurement(
                        step_id=step_id,
                        execution_time=execution_time,
                        voltage=voltage,
                        current=current,
                        temperature=temperature,
                        capacity=capacity,
                        energy=energy,
                        soc=soc
                    )
                    measurements.append(measurement)

                except (ValueError, TypeError) as e:
                    print(f"警告：數據轉換錯誤 - {str(e)}")
                    total_errors += 1
                    continue

            if measurements:
                try:
                    session.add_all(measurements)
                    session.commit()
                    total_saved += len(measurements)
                    print(f"已保存 {len(measurements)} 個測量數據")
                except Exception as e:
                    print(f"錯誤：保存測量數據時發生錯誤 - {str(e)}")
                    session.rollback()
                    total_errors += len(measurements)

        print(f"總共保存了 {total_saved} 個測量數據，{total_errors} 個錯誤")


def save_processed_files_to_db(
    experiment_id: int,
    step_filename: str,
    detail_filename: str,
    step_file_hash: str,
    detail_file_hash: str,
    step_df_len: int,
    detail_df_len: int,
    step_metadata: Dict[str, Any],
    detail_metadata: Dict[str, Any]
):
    """
    Save processed file records to the database.

    Args:
        experiment_id: ID of the experiment
        step_filename: Filename of the step file
        detail_filename: Filename of the detail file
        step_file_hash: Hash of the step file
        detail_file_hash: Hash of the detail file
        step_df_len: Number of rows in step DataFrame
        detail_df_len: Number of rows in detail DataFrame
        step_metadata: Metadata about the step file
        detail_metadata: Metadata about the detail file
    """
    with get_db_session() as session:
        session.add(ProcessedFile(
            experiment_id=experiment_id,
            filename=step_filename,
            file_type="step",
            file_hash=step_file_hash,
            row_count=step_df_len,
            data_meta=step_metadata
        ))

        session.add(ProcessedFile(
            experiment_id=experiment_id,
            filename=detail_filename,
            file_type="detail",
            file_hash=detail_file_hash,
            row_count=detail_df_len,
            data_meta=detail_metadata
        ))

        session.commit()


def update_experiment_end_date(experiment_id: int, end_time: datetime):
    """
    Update the end date of an experiment.

    Args:
        experiment_id: ID of the experiment
        end_time: End time to set
    """
    with get_db_session() as session:
        experiment = session.get(Experiment, experiment_id)
        if experiment:
            experiment.end_date = end_time
            session.add(experiment)
            session.commit()


def save_steps_to_db(
    experiment_id: int,
    steps_df: pd.DataFrame,
    nominal_capacity: float,
    session=None
) -> List[Step]:
    """
    Save step data to the database.
    
    Args:
        experiment_id: ID of the experiment
        steps_df: DataFrame containing step data
        nominal_capacity: Nominal capacity value for c_rate calculation
        session: Optional SQLAlchemy session object. If provided, this session will be used
                 instead of creating a new one. This helps maintain object attachment to session.
    
    Returns:
        List of Step objects that were added to the database
    """
    steps = []
    
    # 決定是否使用提供的 session 或創建新的 session
    own_session = session is None
    if own_session:
        session = next(get_db_session())
    
    try:
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

        session.commit()
        
        # 如果是我們創建的會話，需要做清理工作
        # 如果是外部傳入的會話，不要修改其狀態（不要 expunge 對象）
        if own_session:
            # 如果使用自己的會話，則需要分離對象以避免 DetachedInstanceError
            for step in steps:
                session.expunge(step)
                
    except Exception as e:
        print(f"保存步驟數據時發生錯誤: {e}")
        # 只有在使用自己的會話時才做回滾，外部會話的控制權應留給調用者
        if own_session:
            session.rollback()
        raise
    finally:
        # 只有在使用自己的會話時才關閉它，外部會話應由調用者負責關閉
        if own_session:
            session.close()
            
    return steps