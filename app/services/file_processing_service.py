"""Core logic for file data extraction and the main processing pipeline. While it contains Streamlit calls for user feedback (e.g., st.spinner), separating it clarifies the workflow."""

import logging
import pandas as pd
import os
from datetime import datetime
from typing import Any, BinaryIO, Dict, Union
import streamlit as st

from app.etl import convert_numpy_types, load_and_preprocess_files
from app.models import Cell
from app.services.database_service import check_file_already_processed, save_experiment_to_db,save_measurements_to_db_with_session, save_processed_files_to_db, update_experiment_end_date
from app.services.validation_service import generate_validation_results
from app.ui.components.meta_data_page.data_display_ui import display_validation_summary
from app.services.database_service import save_steps_to_db
from app.utils.database import get_session as get_db_session
from app.utils.temp_files import calculate_file_hash, calculate_file_hash_from_memory, create_session_temp_file

# 設置詳細日誌記錄
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def get_file_data_and_metadata(
    step_source: Union[str, BinaryIO],
    detail_source: Union[str, BinaryIO],
    is_example_file: bool = False
) -> Dict[str, Any]:
    """
    Get file data and metadata depending on source type.

    This helper function handles the differences between example files (paths)
    and uploaded files (UploadedFile objects).

    Args:
        step_source: Either a file path (for example files) or an UploadedFile object
        detail_source: Either a file path (for example files) or an UploadedFile object
        is_example_file: Whether the source is an example file

    Returns:
        Dictionary containing:
        - step_df: DataFrame with step data
        - detail_df: DataFrame with detail data
        - step_file_path: Path to step file (temp file for uploads)
        - detail_file_path: Path to detail file (temp file for uploads)
        - step_file_hash: Hash of step file
        - detail_file_hash: Hash of detail file
        - step_filename: Original filename of step file
        - detail_filename: Original filename of detail file
        - is_uploaded_file: Whether temp files were created for upload
    """
    result = {}

    # Flag indicating if these are uploaded files (need temp files)
    result['is_uploaded_file'] = not is_example_file

    if is_example_file:
        # Example files: step_source and detail_source are file paths
        step_file_path = step_source
        detail_file_path = detail_source

        # Calculate file hashes
        step_file_hash = calculate_file_hash(step_file_path)
        detail_file_hash = calculate_file_hash(detail_file_path)

        # Get filenames from paths
        step_filename = os.path.basename(step_file_path)
        detail_filename = os.path.basename(detail_file_path)

        # Read DataFrames
        step_df = pd.read_csv(step_file_path)
        detail_df = pd.read_csv(detail_file_path)

    else:
        # Uploaded files: step_source and detail_source are UploadedFile objects
        step_file = step_source
        detail_file = detail_source

        # Calculate hashes from memory
        step_file_hash = calculate_file_hash_from_memory(step_file.getbuffer())
        detail_file_hash = calculate_file_hash_from_memory(detail_file.getbuffer())

        # Create temporary files for processing
        step_file_path = create_session_temp_file(
            step_file,
            file_key=f"step_{step_file_hash}",
            suffix=".csv"
        )

        detail_file_path = create_session_temp_file(
            detail_file,
            file_key=f"detail_{detail_file_hash}",
            suffix=".csv"
        )

        # Get original filenames
        step_filename = step_file.name
        detail_filename = detail_file.name

        # Read DataFrames
        step_df = pd.read_csv(step_file)
        detail_df = pd.read_csv(detail_file)

    # Store all the results
    result['step_df'] = step_df
    result['detail_df'] = detail_df
    result['step_file_path'] = step_file_path
    result['detail_file_path'] = detail_file_path
    result['step_file_hash'] = step_file_hash
    result['detail_file_hash'] = detail_file_hash
    result['step_filename'] = step_filename
    result['detail_filename'] = detail_filename

    return result


def handle_file_processing_pipeline(file_data: Dict[str, Any]) -> bool:
    """
處理完整的文件處理流程。

此函數處理從驗證到 ETL 再到資料庫保存和 UI 回饋的整個工作流程，無論文件來源為何。
**優化流程**: 只處理用戶在 step selection 中選擇的步驟，預先建立完整的 step_number:step_id 對應表。

參數：
file_data：包含來自 get_file_data_and_metadata 的檔案資料和元資料的字典

返回：
如果處理成功，則傳回 True，否則傳回 False
    """
    print("===== DEBUG: Entering optimized handle_file_processing_pipeline =====")
    
    # Check if we have user-selected steps from step selection UI
    if "selected_steps" not in st.session_state or not st.session_state["selected_steps"]:
        st.error("No steps selected. Please use the Step Selection interface to choose steps first.")
        return False
    
    try:
        # Extract data from input dictionary
        step_df = file_data['step_df']
        detail_df = file_data['detail_df']
        step_file_path = file_data['step_file_path']
        detail_file_path = file_data['detail_file_path']
        step_file_hash = file_data['step_file_hash']
        detail_file_hash = file_data['detail_file_hash']
        step_filename = file_data['step_filename']
        detail_filename = file_data['detail_filename']
        is_uploaded_file = file_data['is_uploaded_file']
        is_example_file = not is_uploaded_file

        # Check if files have already been processed
        if check_file_already_processed(step_file_hash) or check_file_already_processed(detail_file_hash):
            st.warning("One or both files have already been processed. Skipping...")
            return False

        # Get selected step numbers from user selection
        selected_step_numbers = [step["step_number"] for step in st.session_state["selected_steps"]]
        print(f"===== 處理用戶選擇的步驟: {selected_step_numbers} =====")

        # 只有在實際檔案上傳或範例檔案時才執行 ETL，否則直接用傳入的 DataFrame（for test）
        if is_uploaded_file or is_example_file:
            print("開始 ETL 處理流程")
            step_df, detail_df, metadata = load_and_preprocess_files(
                step_file_path,
                detail_file_path,
                nominal_capacity=st.session_state["nominal_capacity"]
            )
        else:
            print("跳過 ETL，直接使用傳入的 DataFrame（for test）")
            metadata = {}

        # 清理 step_df 和 detail_df 的欄位名稱，去除前後空格
        if not step_df.empty:
            step_df.columns = step_df.columns.str.strip()
            print(f"清理後的 Step DataFrame 欄位: {step_df.columns.tolist()}")
        if not detail_df.empty:
            detail_df.columns = detail_df.columns.str.strip()
            print(f"清理後的 Detail DataFrame 欄位: {detail_df.columns.tolist()}")

        # **優化重點**: 只保留用戶選擇的步驟數據
        print(f"===== 過濾用戶選擇的步驟數據 =====")
        original_step_count = len(step_df)
        original_detail_count = len(detail_df)
        
        # 過濾 step_df 只保留用戶選擇的步驟
        if 'step_number' in step_df.columns:
            step_df = step_df[step_df['step_number'].isin(selected_step_numbers)].copy()
        print(f"Step DataFrame: 原始 {original_step_count} 行 -> 選擇後 {len(step_df)} 行")
        
        # 過濾 detail_df 只保留用戶選擇的步驟
        if 'step_number' in detail_df.columns:
            detail_df = detail_df[detail_df['step_number'].isin(selected_step_numbers)].copy()
        elif '工步' in detail_df.columns:
            # 如果使用中文列名，映射後再過濾
            detail_df = detail_df[detail_df['工步'].isin(selected_step_numbers)].copy()
        print(f"Detail DataFrame: 原始 {original_detail_count} 行 -> 選擇後 {len(detail_df)} 行")

        # 檢查是否有數據剩餘
        if step_df.empty:
            st.error(f"No step data found for selected steps: {selected_step_numbers}")
            return False
        if detail_df.empty:
            st.error(f"No measurement data found for selected steps: {selected_step_numbers}")
            return False

        # 詳細記錄過濾後的 DataFrame 信息
        print("===== 過濾後的 DataFrame 分析 =====")
        print(f"Step DataFrame: shape={step_df.shape}, columns={step_df.columns.tolist()}")
        print(f"Detail DataFrame: shape={detail_df.shape}, columns={detail_df.columns.tolist()}")
        
        if not detail_df.empty:
            # 檢查 step_number 分布
            if 'step_number' in detail_df.columns:
                step_counts = detail_df['step_number'].value_counts().sort_index()
                print(f"過濾後 Detail DataFrame step_number 分布: {step_counts.to_dict()}")
            elif '工步' in detail_df.columns:
                step_counts = detail_df['工步'].value_counts().sort_index()
                print(f"過濾後 Detail DataFrame 工步 分布: {step_counts.to_dict()}")

        # 檢查detail_df是否包含必要的列
        required_columns = ["step_number", "execution_time", "voltage", "current"]
        missing_columns = [col for col in required_columns if col not in detail_df.columns]
        
        print(f"檢查必要列: required={required_columns}, missing={missing_columns}")
        
        if missing_columns:
            print(f"Detail DataFrame 缺少必要列: {missing_columns}")
            # 中文到英文列名映射
            column_mapping = {
                "工步": "step_number",
                "工步執行時間(秒)": "execution_time", 
                "電壓(V)": "voltage",
                "電流(A)": "current",
                "Aux T1": "temperature",
                "電量(Ah)": "capacity",
                "能量(Wh)": "energy"
            }
            
            mapped_columns = []
            for chinese, english in column_mapping.items():
                if english in missing_columns and chinese in detail_df.columns:
                    print(f"Mapping '{chinese}' column to '{english}'")
                    detail_df[english] = detail_df[chinese]
                    mapped_columns.append(f"{chinese}->{english}")
            
            if mapped_columns:
                print(f"成功映射的列: {mapped_columns}")
            else:
                print("沒有找到可映射的中文列名")

        # 檢查detail_df的前幾行
        if not detail_df.empty:
            first_row = detail_df.iloc[0].to_dict()
            print(f"Detail DataFrame 第一行數據: {first_row}")
            print(f"First row of detail_df: {first_row}")

        # Generate validation reports
        validation_status, step_validation_report, detail_validation_report = generate_validation_results(
            step_df, detail_df
        )

        # Combine validation results
        combined_validation_report = {
            'valid': validation_status,
            'step_validation': step_validation_report,
            'detail_validation': detail_validation_report,
            'timestamp': datetime.utcnow().isoformat()
        }

        # Display validation summary
        display_validation_summary(
            validation_status,
            step_validation_report,
            detail_validation_report
        )

        # Get battery type from cell
        with get_db_session() as cell_session:
            cell = cell_session.get(Cell, st.session_state["cell_id"])
            battery_type = cell.chemistry.value if cell else "Unknown"

        # Calculate average temperature
        if 'T' in detail_df.columns:
            temperature_avg = detail_df['T'].mean()
        else:
            temperature_avg = 25.0  # Default temperature

        # Convert problematic numpy types to native Python types for JSON serialization
        converted_step_report = convert_numpy_types(step_validation_report)        # Store experiment data in the database
        with get_db_session() as session:
            # Create new experiment
            experiment = save_experiment_to_db(
                experiment_metadata={
                    'name': st.session_state["experiment_name"],
                    'start_date': st.session_state["experiment_date"],
                    'operator': st.session_state["operator"],
                    'description': st.session_state["description"],
                    'nominal_capacity': st.session_state["nominal_capacity"],
                    'validation_report': converted_step_report
                },
                validation_report=converted_step_report,
                cell_id=st.session_state["cell_id"],
                machine_id=st.session_state["machine_id"],
                battery_type=battery_type,                temperature_avg=temperature_avg
            )
            
            print(f"===== 優化流程：預先建立 step_number:step_id 對應表 =====")
            print(f"實驗 ID: {experiment.id}")
            print(f"需要處理的步驟: {selected_step_numbers}")
            
            # 驗證實驗 ID 的有效性
            if experiment.id is None:
                st.error("錯誤：實驗保存失敗，未能獲得有效的實驗 ID")
                return False
            
            # **優化重點 1**: 先分析所有需要的 step_number，建立/查詢所有 step，取得完整對應表
            print(f"開始保存選擇的步驟數據到資料庫")
            steps = save_steps_to_db(
                experiment_id=experiment.id,
                steps_df=step_df,  # 此時 step_df 已經只包含用戶選擇的步驟
                nominal_capacity=st.session_state["nominal_capacity"],
                session=session  # 使用同一個會話
            )
            print(f"成功保存 {len(steps)} 個用戶選擇的步驟到資料庫")
            
            # 立即提交步驟數據以確保獲得有效的 step IDs
            session.commit()
            print(f"已提交步驟數據到資料庫，確保 step IDs 有效")            # **優化重點 2**: 預先建立完整的 step_number:step_id 對應表（只針對用戶選擇的步驟）
            step_mapping = {step.step_number: step.id for step in steps if step.id is not None}
            print(f"建立用戶選擇步驟的映射表: {step_mapping}")# 驗證映射表完整性：確保所有用戶選擇的 step_number 都有對應的 step_id
            missing_mappings = set(selected_step_numbers) - set(step_mapping.keys())
            if missing_mappings:
                st.error(f"Error: Missing step mappings for step numbers: {missing_mappings}")
                return False
            
            # 驗證沒有 None 值的 step_id
            invalid_mappings = {k: v for k, v in step_mapping.items() if v is None}
            if invalid_mappings:
                st.error(f"Error: Invalid step IDs (None) for step numbers: {list(invalid_mappings.keys())}")
                return False
            
            print(f"✓ 映射表驗證通過：所有用戶選擇的步驟都有對應的 step_id")

            # 確保 detail_df 包含必要的列並進行數據清理
            print("===== 準備測量數據 =====")
            required_columns = ["step_number", "execution_time", "voltage", "current"]
            missing_columns = [col for col in required_columns if col not in detail_df.columns]
            
            if missing_columns:
                print(f"Detail DataFrame 缺少必要列，嘗試進行列名映射: {missing_columns}")
                # 中文到英文列名映射
                chinese_to_english = {
                    "工步": "step_number",
                    "工步執行時間(秒)": "execution_time",
                    "電壓(V)": "voltage",
                    "電流(A)": "current",
                    "Aux T1": "temperature",
                    "電量(Ah)": "capacity",
                    "能量(Wh)": "energy"
                }

                mapped_count = 0
                for chinese, english in chinese_to_english.items():
                    if english in missing_columns and chinese in detail_df.columns:
                        print(f"映射 '{chinese}' 到 '{english}'")
                        detail_df[english] = detail_df[chinese]
                        mapped_count += 1
                
                print(f"成功映射 {mapped_count} 個列名")

            # 確保 step_number 列是整數類型
            if "step_number" in detail_df.columns:
                try:
                    original_dtype = detail_df["step_number"].dtype
                    detail_df["step_number"] = detail_df["step_number"].astype(int)
                    print(f"step_number 列類型從 {original_dtype} 轉換為 int")
                except Exception as e:
                    print(f"step_number 轉換為整數失敗: {str(e)}")
                    return False

            # **優化重點 3**: 驗證所有測量數據都有對應的 step_id（因為已經預先過濾，這應該 100% 匹配）
            detail_step_numbers = set(detail_df["step_number"].unique())
            mapped_step_numbers = set(step_mapping.keys())
            unmatched_steps = detail_step_numbers - mapped_step_numbers
            
            if unmatched_steps:
                st.error(f"Error: Detail data contains steps not in mapping: {unmatched_steps}")
                return False
            
            print(f"✓ 測量數據驗證通過：所有測量數據都有對應的 step_id")
            print(f"測量數據中的步驟: {sorted(detail_step_numbers)}")
            print(f"映射表中的步驟: {sorted(mapped_step_numbers)}")

            # 記錄最終保存狀態
            print("===== 準備批量保存測量數據 =====")
            print(f"Detail DataFrame 形狀: {detail_df.shape}")
            print(f"將要使用的步驟映射: {step_mapping}")
            print(f"標稱容量: {st.session_state['nominal_capacity']}")
            
            # 統計將要保存的測量數據
            measurements_per_step = detail_df.groupby('step_number').size().to_dict()
            print(f"每個步驟的測量數據量: {measurements_per_step}")
            total_measurements = len(detail_df)
            print(f"總測量數據量: {total_measurements}")

            # **優化重點 4**: 使用 save_measurements_to_db_with_session 在同一會話中保存
            try:
                save_measurements_to_db_with_session(
                    session=session,
                    experiment_id=experiment.id,
                    details_df=detail_df,
                    step_mapping=step_mapping,  # 使用預先建立的完整映射表
                    nominal_capacity=st.session_state["nominal_capacity"]
                )
                print("✓ 優化的測量數據保存完成")
            except Exception as e:
                st.error(f"Error saving measurements: {str(e)}")
                return False            # Save processed file records
            if experiment.id is not None:
                save_processed_files_to_db(
                    experiment_id=experiment.id,
                    step_filename=step_filename,
                    detail_filename=detail_filename,
                    step_file_hash=step_file_hash,
                    detail_file_hash=detail_file_hash,
                    step_df_len=len(step_df),
                    detail_df_len=len(detail_df),
                    step_metadata=metadata.get('step_file', {}),
                    detail_metadata=metadata.get('detail_file', {})
                )

                # Update experiment end date based on the last measurement
                if 'DateTime' in detail_df.columns and not detail_df.empty:
                    try:
                        last_datetime = pd.to_datetime(detail_df['DateTime'].iloc[-1])
                        update_experiment_end_date(experiment.id, last_datetime)
                    except (ValueError, TypeError) as e:
                        st.warning(f"Could not parse end date: {e}")

        if experiment.id is not None:
            st.success(f"Files processed successfully! Experiment ID: {experiment.id}")
        else:
            st.error("Failed to get experiment ID")
        return True

    except Exception as e:
        st.error(f"Error processing files: {str(e)}")
        st.exception(e)
        return False

    finally:
        # Clean up temporary files if they were created for uploads
        if is_uploaded_file:
            try:
                if os.path.exists(step_file_path):
                    os.remove(step_file_path)
                if os.path.exists(detail_file_path):
                    os.remove(detail_file_path)
            except Exception as e:
                st.warning(f"Could not remove temporary files: {str(e)}")