"""Core logic for file data extraction and the main processing pipeline. While it contains Streamlit calls for user feedback (e.g., st.spinner), separating it clarifies the workflow."""


from app.etl import convert_numpy_types, load_and_preprocess_files
from app.models import Cell
from app.services.database_service import check_file_already_processed, save_experiment_to_db, save_measurements_to_db, save_processed_files_to_db, update_experiment_end_date
from app.services.validation_service import generate_validation_results
from app.ui.componenets.data_display_ui import display_validation_summary
from app.services.database_service import save_steps_to_db
from app.utils.database import get_session as get_db_session
import streamlit as st
from datetime import datetime
from app.utils.temp_files import calculate_file_hash, calculate_file_hash_from_memory, create_session_temp_file


import pandas as pd


import os
from typing import Any, BinaryIO, Dict


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
    Handle the complete file processing pipeline.

    This function handles the entire workflow from validation to ETL to database
    saving and UI feedback, regardless of file source.

    Args:
        file_data: Dictionary with file data and metadata from get_file_data_and_metadata

    Returns:
        True if processing was successful, False otherwise
    """
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

        # Apply ETL processing
        # For all files, we now use the load_and_preprocess_files function for consistent processing
        step_df, detail_df, metadata = load_and_preprocess_files(
            step_file_path,
            detail_file_path,
            nominal_capacity=st.session_state["nominal_capacity"]
        )

        # 添加調試信息
        print(f"===== DEBUG: handle_file_processing_pipeline =====")
        print(f"Step DataFrame shape: {step_df.shape}")
        print(f"Detail DataFrame shape: {detail_df.shape}")
        print(f"Step DataFrame columns: {step_df.columns.tolist()}")
        print(f"Detail DataFrame columns: {detail_df.columns.tolist()}")

        # 檢查detail_df是否包含必要的列
        required_columns = ["step_number", "execution_time", "voltage", "current"]
        missing_columns = [col for col in required_columns if col not in detail_df.columns]
        if missing_columns:
            print(f"WARNING: Detail DataFrame is missing required columns: {missing_columns}")
            # 嘗試將工步列映射為step_number
            if "工步" in detail_df.columns and "step_number" not in detail_df.columns:
                print("Mapping '工步' column to 'step_number'")
                detail_df["step_number"] = detail_df["工步"]
            # 嘗試將工步執行時間列映射為execution_time
            if "工步執行時間(秒)" in detail_df.columns and "execution_time" not in detail_df.columns:
                print("Mapping '工步執行時間(秒)' column to 'execution_time'")
                detail_df["execution_time"] = detail_df["工步執行時間(秒)"]
            # 嘗試將電壓列映射為voltage
            if "電壓(V)" in detail_df.columns and "voltage" not in detail_df.columns:
                print("Mapping '電壓(V)' column to 'voltage'")
                detail_df["voltage"] = detail_df["電壓(V)"]
            # 嘗試將電流列映射為current
            if "電流(A)" in detail_df.columns and "current" not in detail_df.columns:
                print("Mapping '電流(A)' column to 'current'")
                detail_df["current"] = detail_df["電流(A)"]

        # 檢查detail_df的前幾行
        if not detail_df.empty:
            print(f"First row of detail_df: {detail_df.iloc[0].to_dict()}")

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
        converted_step_report = convert_numpy_types(step_validation_report)

        # Store experiment data in the database
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
                battery_type=battery_type,
                temperature_avg=temperature_avg
            )

            # Save steps to database
            steps = save_steps_to_db(
                experiment_id=experiment.id,
                steps_df=step_df,
                nominal_capacity=st.session_state["nominal_capacity"]
            )

            # Create a mapping from step number to step ID
            step_mapping = {step.step_number: step.id for step in steps}

            # 檢查detail_df是否包含必要的列
            required_columns = ["step_number", "execution_time", "voltage", "current"]
            missing_columns = [col for col in required_columns if col not in detail_df.columns]

            # 如果缺少必要的列，嘗試進行映射
            if missing_columns:
                print(f"WARNING: Missing required columns before saving measurements: {missing_columns}")

                # 嘗試從中文列名映射
                chinese_to_english = {
                    "工步": "step_number",
                    "工步執行時間(秒)": "execution_time",
                    "電壓(V)": "voltage",
                    "電流(A)": "current",
                    "Aux T1": "temperature",
                    "電量(Ah)": "capacity",
                    "能量(Wh)": "energy"
                }

                for chinese, english in chinese_to_english.items():
                    if english in missing_columns and chinese in detail_df.columns:
                        print(f"Mapping '{chinese}' to '{english}'")
                        detail_df[english] = detail_df[chinese]

            # 確保step_number列是整數類型
            if "step_number" in detail_df.columns:
                try:
                    detail_df["step_number"] = detail_df["step_number"].astype(int)
                except Exception as e:
                    print(f"Error converting step_number to int: {str(e)}")
                    # 嘗試清理數據
                    try:
                        detail_df["step_number"] = pd.to_numeric(detail_df["step_number"], errors="coerce")
                        detail_df["step_number"] = detail_df["step_number"].fillna(1).astype(int)
                    except Exception as e2:
                        print(f"Failed to clean step_number: {str(e2)}")

            # 檢查detail_df中的step_number是否在step_mapping中
            if "step_number" in detail_df.columns:
                step_numbers_in_details = set(detail_df["step_number"].unique())
                step_numbers_in_mapping = set(step_mapping.keys())
                missing_step_numbers = step_numbers_in_details - step_numbers_in_mapping

                if missing_step_numbers:
                    print(f"Warning: Some step numbers in detail data are not in step mapping: {missing_step_numbers}")

            # 檢查detail_df中的step_number是否與step_mapping中的鍵匹配
            if 'step_number' in detail_df.columns:
                # 檢查detail_df中的step_number類型
                if detail_df['step_number'].dtype != int:
                    # 嘗試轉換為整數
                    try:
                        detail_df['step_number'] = detail_df['step_number'].astype(int)
                        print("步驟編號已轉換為整數類型")
                    except Exception as e:
                        print(f"無法將步驟編號轉換為整數: {str(e)}")

                # 檢查是否有匹配的步驟編號
                unique_step_numbers = set(detail_df['step_number'].unique())
                matching_steps = unique_step_numbers.intersection(set(step_mapping.keys()))

                if len(matching_steps) == 0:
                    print(f"警告: 詳細數據中的步驟編號 {unique_step_numbers} 與步驟映射 {set(step_mapping.keys())} 不匹配")

                    # 嘗試找到最接近的映射
                    step_numbers_list = sorted(list(step_mapping.keys()))
                    if len(step_numbers_list) > 0 and len(unique_step_numbers) > 0:
                        print("嘗試創建新的步驟映射...")

                        # 創建一個新的映射，將detail_df中的步驟編號映射到最接近的step_mapping中的步驟編號
                        new_mapping = {}
                        sorted_unique_steps = sorted(list(unique_step_numbers))

                        if len(sorted_unique_steps) <= len(step_numbers_list):
                            # 如果detail_df中的步驟數量小於或等於step_mapping中的步驟數量，直接按順序映射
                            for i, step_num in enumerate(sorted_unique_steps):
                                if i < len(step_numbers_list):
                                    new_mapping[step_num] = step_mapping[step_numbers_list[i]]
                                    print(f"映射步驟 {step_num} 到 {step_numbers_list[i]} (ID: {step_mapping[step_numbers_list[i]]})")
                        else:
                            # 如果detail_df中的步驟數量大於step_mapping中的步驟數量，則循環使用step_mapping中的步驟
                            for i, step_num in enumerate(sorted_unique_steps):
                                idx = i % len(step_numbers_list)
                                new_mapping[step_num] = step_mapping[step_numbers_list[idx]]
                                print(f"映射步驟 {step_num} 到 {step_numbers_list[idx]} (ID: {step_mapping[step_numbers_list[idx]]})")

                        # 使用新的映射
                        step_mapping = new_mapping

            # Save measurements to database
            save_measurements_to_db(
                experiment_id=experiment.id,
                details_df=detail_df,
                step_mapping=step_mapping,
                nominal_capacity=st.session_state["nominal_capacity"]
            )

            # Save processed file records
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

        st.success(f"Files processed successfully! Experiment ID: {experiment.id}")
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