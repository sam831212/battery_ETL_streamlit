"""Helper functions for direct database interactions - Refactored Version."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass
from contextlib import contextmanager
import time
import os

import pandas as pd
from sqlmodel import select, func, Session, delete
from app.etl import convert_numpy_types
from app.models import Experiment, Measurement, ProcessedFile, Step
from app.utils.data_helpers import convert_datetime_to_python
from app.utils.database import get_session as get_db_session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# 配置
@dataclass
class ProcessingConfig:
    """處理配置類"""
    default_batch_size: int = 1000
    measurement_internal_batch_size: int = 500  # 新增：用於測量數據內部小批次的大小
    max_retry_attempts: int = 3
    voltage_precision: int = 3
    current_precision: int = 3
    temperature_precision: int = 1
    capacity_precision: int = 3
    energy_precision: int = 3
    soc_precision: int = 1
    default_temperature: float = 25.0

# 全域配置實例
config = ProcessingConfig()

# 設置日誌
logger = logging.getLogger(__name__)

# 定義文件類型常量
FILE_TYPE_STEP = "step"
FILE_TYPE_DETAIL = "detail"

# 自定義異常類別
class DatabaseError(Exception):
    """數據庫操作異常"""
    pass

class ValidationError(Exception):
    """數據驗證異常"""
    pass

class ProcessingError(Exception):
    """數據處理異常"""
    pass

# 修改引擎配置，添加連線池設定  
from app.utils.config import DATABASE_URL

engine = create_engine(
    DATABASE_URL,
    poolclass=StaticPool,
    pool_pre_ping=True,
    pool_recycle=300,
    connect_args={
        "check_same_thread": False,
        "timeout": 30,  # 增加超時時間
        "isolation_level": None  # 自動提交模式
    },
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 輔助函數
def retry_on_failure(max_attempts: int = 3, delay: float = 1.0):
    """重試裝飾器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts - 1:
                        raise DatabaseError(f"操作失敗，已重試 {max_attempts} 次: {str(e)}")
                    logger.warning(f"嘗試 {attempt + 1} 失敗，正在重試: {str(e)}")
                    if delay > 0:
                        time.sleep(delay)
            return None
        return wrapper
    return decorator

@contextmanager
def safe_session():
    """安全的資料庫會話管理"""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        raise
    finally:
        session.close()

def retry_database_operation(operation_func, max_retries=3, retry_delay=0.5):
    """重試資料庫操作的裝飾器函數"""
    for attempt in range(max_retries):
        try:
            return operation_func()
        except Exception as e:
            if "database is locked" in str(e) and attempt < max_retries - 1:
                logger.warning(f"資料庫被鎖定，等待重試 ({attempt + 1}/{max_retries})，錯誤: {str(e)}")
                time.sleep(retry_delay * (attempt + 1))  # 遞增等待時間
                continue
            else:
                raise e
    
    raise DatabaseError("資料庫操作超過最大重試次數")

def validate_required_columns(df: pd.DataFrame, required_columns: List[str]) -> None:
    """驗證必要欄位"""
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise ValidationError(f"缺少必要的列: {missing_columns}")

def safe_get_float_from_dict(d: Dict[str, Any], key: str, default: float = 0.0) -> float:
    """安全地從字典中獲取浮點數值"""
    try:
        v = d.get(key, default)
        return float(v) if v is not None else default
    except (ValueError, TypeError):
        return default

def safe_get_str_from_dict(d: Dict[str, Any], key: str, default: str = "") -> str:
    """安全地從字典中獲取字串"""
    try:
        v = d.get(key, default)
        return str(v) if v is not None else default
    except (ValueError, TypeError):
        return default

def safe_get_optional_float_from_dict(d: Dict[str, Any], key: str) -> Optional[float]:
    """安全地從字典中獲取可選的浮點數值"""
    try:
        v = d.get(key)
        return float(v) if v is not None else None
    except (ValueError, TypeError):
        return None

def round_numeric_value(value: Any, precision: int, default: float = 0.0) -> float:
    """安全地四捨五入數值"""
    try:
        if pd.isna(value):
            return default
        return round(float(value), precision)
    except (ValueError, TypeError):
        return default

def calculate_c_rate(current: float, nominal_capacity: float) -> float:
    """計算 C-rate"""
    try:
        return abs(current) / nominal_capacity if nominal_capacity else 0.0
    except (ValueError, TypeError, ZeroDivisionError):
        return 0.0

# 主要功能函數
@retry_on_failure(max_attempts=config.max_retry_attempts)
def check_file_already_processed(file_hash: str) -> bool:
    """
    檢查文件是否已經處理過
    
    Args:
        file_hash: 文件的雜湊值
        
    Returns:
        True 如果已處理，False 否則
    """
    if not file_hash:
        return False

    try:
        with safe_session() as session:
            existing_file = session.exec(
                select(ProcessedFile).where(ProcessedFile.file_hash == file_hash)
            ).first()
            return existing_file is not None
    except Exception as e:
        logger.error(f"檢查文件處理狀態時發生錯誤: {str(e)}")
        return False

def save_experiment_to_db(
    experiment_metadata: Dict[str, Any],
    validation_report: Dict[str, Any],
    cell_id: int,
    machine_id: int,
    battery_type: str,
    temperature: float,
    project_id: Optional[int] = None
) -> Experiment:
    """
    創建並保存新的實驗記錄
    
    Args:
        experiment_metadata: 實驗元數據
        validation_report: 驗證報告
        cell_id: 電池單元ID
        machine_id: 機器ID
        battery_type: 電池類型
        temperature: 平均溫度
        
    Returns:
        創建的實驗對象
    """ 
    experiment = Experiment(
        name=experiment_metadata['name'],
        description=experiment_metadata.get('description', ''),
        battery_type=battery_type,
        nominal_capacity=experiment_metadata['nominal_capacity'],
        temperature=temperature,
        operator=experiment_metadata.get('operator', ''),
        start_date=experiment_metadata['start_date'],
        end_date=None,
        validation_status=validation_report['valid'],
        validation_report=validation_report,
        cell_id=cell_id,
        machine_id=machine_id,
        project_id=project_id
    )

    try:
        with safe_session() as session:
            session.add(experiment)
            session.commit()
            session.refresh(experiment)
            return experiment
    except Exception as e:
        raise DatabaseError(f"保存實驗記錄失敗: {str(e)}")

def create_measurement_from_row(
    row: pd.Series, 
    step_mapping: Dict[int, int],
    config: ProcessingConfig
) -> Optional[Measurement]:
    """
    從數據行創建測量對象
    
    Args:
        row: 數據行
        step_mapping: 步驟映射
        config: 處理配置
          Returns:
        測量對象或 None（如果無法創建）
    """
    try:
        step_number = int(row['step_number'])
        if step_number not in step_mapping:
            return None

        step_id = step_mapping[step_number]
        
        # Critical validation: Ensure step_id is not None
        if step_id is None:
            logger.error(f"step_id 為 None: step_number={step_number}, step_mapping={step_mapping}")
            return None
        execution_time = float(row['execution_time'])
        voltage = round_numeric_value(row['voltage'], config.voltage_precision)
        current = round_numeric_value(row['current'], config.current_precision)
        temperature = round_numeric_value(
            row.get('temperature', config.default_temperature), 
            config.temperature_precision, 
            config.default_temperature
        )
        capacity = round_numeric_value(row.get('capacity', 0.0), config.capacity_precision)
        energy = round_numeric_value(row.get('energy', 0.0), config.energy_precision)
        return Measurement(
            step_id=step_id,
            execution_time=execution_time,
            voltage=voltage,
            current=current,
            temperature=temperature,
            capacity=capacity,
            energy=energy
            # 注意：根據業務需求，SOC 數據不存儲到測量表中
        )
    except (ValueError, TypeError) as e:
        logger.warning(f"創建測量對象失敗: {str(e)}")
        return None

def process_measurements_batch(
    batch_df: pd.DataFrame,
    step_mapping: Dict[int, int],
    config: ProcessingConfig,
    progress_callback: Optional[Callable[[str], None]] = None
) -> tuple[List[Measurement], int, int]:
    """
    處理測量數據批次
    
    Args:
        batch_df: 批次數據框
        step_mapping: 步驟映射
        config: 處理配置
        progress_callback: 進度回調函數
        
    Returns:
        (測量列表, 跳過數量, 錯誤數量)
    """
    measurements = []
    skipped_count = 0
    error_count = 0
    
    for row_idx, row in batch_df.iterrows():
        if progress_callback:
            progress_callback(f"處理行 {row_idx}")
            
        measurement = create_measurement_from_row(row, step_mapping, config)
        
        if measurement is None:
            step_number = int(row.get('step_number', -1))
            if step_number not in step_mapping:
                skipped_count += 1
            else:
                error_count += 1
        else:
            measurements.append(measurement)
    
    return measurements, skipped_count, error_count

def save_measurements_batch(
    session: Session,
    measurements: List[Measurement],
    batch_num: int
) -> None:
    """
    保存測量數據批次到資料庫
    
    Args:
        session: 資料庫會話
        measurements: 測量列表
        batch_num: 批次編號
    """
    if not measurements:
        logger.info(f"批次 {batch_num}: 沒有數據需要保存")
        return
    
    try:
        # 分小批次處理，避免一次性插入太多數據
        small_batch_size = config.measurement_internal_batch_size # 使用配置值
        for i in range(0, len(measurements), small_batch_size):
            small_batch = measurements[i:i + small_batch_size]
            session.add_all(small_batch)
            session.flush()  # 立即寫入這個小批次
            
            # 每個小批次後短暫等待
            if i + small_batch_size < len(measurements):
                time.sleep(0.01)
        
        logger.info(f"批次 {batch_num}: 成功準備保存 {len(measurements)} 個測量數據")
    except Exception as e:
        session.rollback()
        raise ProcessingError(f"批次 {batch_num} 保存失敗: {str(e)}")


def save_measurements_to_db(
    experiment_id: int,
    details_df: pd.DataFrame,
    step_mapping: Dict[int, int],
    nominal_capacity: float,
    batch_size: Optional[int] = None,
    progress_callback: Optional[Callable[[str], None]] = None
) -> None:
    """
    保存測量數據到資料庫
    
    Args:
        experiment_id: 實驗ID
        details_df: 詳細數據框
        step_mapping: 步驟映射
        nominal_capacity: 標稱容量
        batch_size: 批次大小
        progress_callback: 進度回調函數
    """
    if details_df.empty:
        logger.warning("沒有測量數據需要保存")
        return

    batch_size = batch_size or config.default_batch_size
    
    # 驗證必要欄位
    required_columns = ['step_number', 'execution_time', 'voltage', 'current']
    validate_required_columns(details_df, required_columns)
    
    if not step_mapping:
        raise ValidationError("步驟映射為空")

    logger.info(f"開始處理 {len(details_df)} 行數據，批次大小: {batch_size}")
    total_saved_measurements = 0
    total_error_rows = 0
    total_skipped_rows = 0

    for batch_num, i in enumerate(range(0, len(details_df), batch_size), 1):
        batch_df = details_df.iloc[i:i + batch_size]
        
        if progress_callback:
            progress_callback(f"處理批次 {batch_num}/{(len(details_df) - 1) // batch_size + 1}")
        
        # Define the operation for a single batch, to be wrapped by retry logic
        def process_and_save_one_batch():
            # This function processes one batch_df and saves it in a new session.
            # It returns (num_saved, num_skipped, num_errors) for this batch.
            
            _measurements, _skipped, _errors = process_measurements_batch(
                batch_df, step_mapping, config, progress_callback
            )
            
            _saved_this_batch = 0
            if _measurements:
                # Each batch gets its own session and transaction
                with safe_session() as session: # Correctly use safe_session for commit/rollback
                    save_measurements_batch(session, _measurements, batch_num)
                    # commit is handled by safe_session
                _saved_this_batch = len(_measurements)
            
            return _saved_this_batch, _skipped, _errors

        try:
            # Apply retry logic to the processing and saving of this single batch
            saved_count, skipped_count, error_count = retry_database_operation(process_and_save_one_batch)
            
            total_saved_measurements += saved_count
            total_skipped_rows += skipped_count
            total_error_rows += error_count
            
        except Exception as e:
            # If a batch fails even after retries, log it and re-raise to stop further processing.
            logger.error(f"批次 {batch_num} 永久失敗，即使重試後: {str(e)}")
            # Wrap the original exception to preserve its details
            raise DatabaseError(f"保存測量數據時，批次 {batch_num} 永久失敗: {str(e)}") from e

    # 最終統計
    logger.info("保存完成統計:")
    logger.info(f"成功保存: {total_saved_measurements} 個測量數據")
    logger.info(f"跳過行數: {total_skipped_rows} (原因: step_number不匹配或創建測量對象時內部錯誤)")
    logger.info(f"錯誤行數: {total_error_rows} (原因: 創建測量對象時數據驗證/轉換失敗)")
    if not details_df.empty: # Check if details_df was empty to avoid division by zero
        success_rate = (total_saved_measurements / len(details_df) * 100) if len(details_df) > 0 else 0.0
        logger.info(f"成功率: {success_rate:.1f}%")
    else:
        logger.info("沒有數據進行處理，成功率不適用。")

def save_steps_to_db(
    experiment_id: int,
    steps_df: pd.DataFrame,
    nominal_capacity: float,
    session: Optional[Session] = None
) -> List[Step]:
    """
    保存步驟數據到資料庫
    
    Args:
        experiment_id: 實驗ID
        steps_df: 步驟數據框
        nominal_capacity: 標稱容量
        session: 可選的資料庫會話
        
    Returns:
        保存的步驟對象列表
    """
    if experiment_id is None:
        raise ValueError("experiment_id 不能為 None")
    
    steps = []
    own_session = session is None
    
    if own_session:
        session_context = safe_session()
        session = session_context.__enter__()
    
    try:
        for _, row in steps_df.iterrows():
            row_dict = convert_numpy_types(row.to_dict())
            
            step_number = safe_get_float_from_dict(row_dict, "step_number", 0.0)
            step_type = safe_get_str_from_dict(row_dict, "step_type", "unknown")
            duration = safe_get_float_from_dict(row_dict, "duration", 0.0)
            voltage_start = safe_get_float_from_dict(row_dict, "voltage_start", 0.0)
            voltage_end = safe_get_float_from_dict(row_dict, "voltage_end", 0.0)
            current = safe_get_float_from_dict(row_dict, "current", 0.0)
            capacity = safe_get_float_from_dict(row_dict, "capacity", 0.0)
            energy = safe_get_float_from_dict(row_dict, "energy", 0.0)
            temperature_start = safe_get_float_from_dict(row_dict, "temperature_start", config.default_temperature)
            temperature_end = safe_get_float_from_dict(row_dict, "temperature_end", config.default_temperature)
            soc_start = safe_get_optional_float_from_dict(row_dict, "soc_start")
            soc_end = safe_get_optional_float_from_dict(row_dict, "soc_end")
            start_time = row_dict.get('start_time', None) # 保持原樣，因為它處理 datetime
            end_time = row_dict.get('end_time', None) # 保持原樣，因為它處理 datetime
            c_rate = safe_get_float_from_dict(row_dict, "c_rate", 0.0)
            pre_test_rest_time = safe_get_optional_float_from_dict(row_dict, "pre_test_rest_time")
            
            # 注意：如果 start_time 或 end_time 為 None，則默認為當前時間 (datetime.now())。
            # 這意味著如果源數據中缺少這些時間，將記錄處理時間而非實際事件時間。
            # 如果需要實際事件時間且不應為 None，則應在此處添加驗證或修改 Step 模型以允許 None。
            step = Step(
                experiment_id=experiment_id,
                step_number=int(step_number),
                step_type=step_type,
                start_time=start_time if start_time is not None else datetime.now(),
                end_time=end_time if end_time is not None else datetime.now(),
                duration=duration,
                voltage_start=voltage_start,
                voltage_end=voltage_end,
                current=current,
                capacity=capacity,
                energy=energy,
                temperature_start=temperature_start,
                temperature_end=temperature_end,                c_rate=c_rate,
                soc_start=soc_start,
                soc_end=soc_end,
                pre_test_rest_time=pre_test_rest_time,
                data_meta=row_dict if isinstance(row_dict, dict) else {}
            )

            session.add(step)
            steps.append(step)

        # 獲取自動生成的 ID
        session.flush()
        
        for step in steps:
            session.refresh(step)
        
        # 驗證所有步驟都有有效的 ID
        invalid_steps = [step for step in steps if step.id is None]
        if invalid_steps:
            raise DatabaseError(f"無法獲取 {len(invalid_steps)} 個步驟的有效 ID")
        
        if own_session:
            session.commit()
            for step in steps:
                session.expunge(step)
                
    except Exception as e:
        logger.error(f"保存步驟數據時發生錯誤: {e}")
        if own_session:
            session.rollback()
        raise DatabaseError(f"保存步驟數據失敗: {str(e)}")
    finally:
        if own_session:
            session_context.__exit__(None, None, None)
            
    return steps

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
) -> None:
    """
    保存已處理文件記錄到資料庫
    
    Args:
        experiment_id: 實驗ID
        step_filename: 步驟文件名
        detail_filename: 詳細文件名
        step_file_hash: 步驟文件雜湊
        detail_file_hash: 詳細文件雜湊
        step_df_len: 步驟數據框行數
        detail_df_len: 詳細數據框行數
        step_metadata: 步驟文件元數據
        detail_metadata: 詳細文件元數據
    """
    try:
        with safe_session() as session:
            session.add(ProcessedFile(
                experiment_id=experiment_id,
                filename=step_filename,
                file_type=FILE_TYPE_STEP,  # 使用常量
                file_hash=step_file_hash,
                row_count=step_df_len,
                data_meta=step_metadata
            ))

            session.add(ProcessedFile(
                experiment_id=experiment_id,
                filename=detail_filename,
                file_type=FILE_TYPE_DETAIL,  # 使用常量
                file_hash=detail_file_hash,
                row_count=detail_df_len,
                data_meta=detail_metadata
            ))

            session.commit()
    except Exception as e:
        raise DatabaseError(f"保存已處理文件記錄失敗: {str(e)}")

def update_experiment_end_date(experiment_id: int, end_time: datetime) -> None:
    """
    更新實驗的結束日期
    
    Args:
        experiment_id: 實驗ID
        end_time: 結束時間
    """
    try:
        with safe_session() as session:
            experiment = session.get(Experiment, experiment_id)
            if experiment:
                experiment.end_date = end_time
                session.add(experiment)
                session.commit()
            else:
                raise ValidationError(f"找不到 ID 為 {experiment_id} 的實驗")
    except Exception as e:
        raise DatabaseError(f"更新實驗結束日期失敗: {str(e)}")

def delete_experiment_and_related(experiment_id: int) -> None:
    """
    [測試用 - 空操作] 刪除指定實驗及其相關的 step 和 measurement。
    Args:
        experiment_id: 要刪除的實驗 ID
    Raises:
        DatabaseError: 刪除過程中發生錯誤
    """
    logger.info(f"🔍 DEBUG (NO-OP): 請求刪除實驗 ID: {experiment_id}")

    # 模擬檢查實驗是否存在
    # try:
    #     with safe_session() as session:
    #         experiment = session.get(Experiment, experiment_id)
    #         if not experiment:
    #             logger.warning(f"🔍 DEBUG (NO-OP): 實驗 ID {experiment_id} 若實際執行則找不到")
    #             # raise DatabaseError(f"實驗 ID {experiment_id} 不存在") # 在空操作中不拋出
    #         else:
    #             logger.info(f"🔍 DEBUG (NO-OP): 若實際執行，將刪除實驗: {experiment.name}")
    # except Exception as e:
    #     logger.error(f"🔍 DEBUG (NO-OP): 模擬檢查實驗時發生錯誤: {e}")

    logger.info(f"🔍 DEBUG (NO-OP): 模擬查找相關的 steps for experiment_id: {experiment_id}")
    # step_ids = [] # 模擬
    logger.info(f"🔍 DEBUG (NO-OP): 模擬找到 0 個 steps")

    # measurement_count = 0 # 模擬
    logger.info(f"🔍 DEBUG (NO-OP): 模擬找到 0 個 measurements 需要刪除")

    logger.info("🔍 DEBUG (NO-OP): 模擬分批刪除 measurements (實際未執行)")
    # deleted_count = 0
    # logger.info(f"🔍 DEBUG (NO-OP): 模擬已刪除 {deleted_count}/{measurement_count} 個 measurements")

    logger.info("🔍 DEBUG (NO-OP): 模擬刪除 steps (實際未執行)")
    # logger.info(f"🔍 DEBUG (NO-OP): 模擬準備刪除 0 個 steps")

    logger.info("🔍 DEBUG (NO-OP): 模擬刪除 ProcessedFile 記錄 (實際未執行)")
    # logger.info(f"🔍 DEBUG (NO-OP): 模擬準備刪除 0 個 ProcessedFile 記錄")
            
    logger.info("🔍 DEBUG (NO-OP): 模擬刪除 experiment (實際未執行)")
    # logger.info(f"🔍 DEBUG (NO-OP): 模擬準備刪除 experiment")
            
    logger.info("🔍 DEBUG (NO-OP): 模擬提交事務 (實際未執行)")
    logger.info(f"🔍 DEBUG (NO-OP): 實驗 ID {experiment_id} 的刪除操作已記錄 (未實際執行資料庫操作)")
