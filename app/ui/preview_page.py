"""
Data Preview UI components for the Battery ETL Dashboard

This module provides UI components for previewing and analyzing battery test data
before proceeding to step selection and database loading.
"""
import os
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Tuple, Dict, Any, List, Optional

from app.etl.extraction import (
    load_and_preprocess_files,
    parse_step_csv,
    parse_detail_csv,
    validate_csv_format,
    STEP_REQUIRED_HEADERS,
    DETAIL_REQUIRED_HEADERS
)
from app.etl.transformation import (
    calculate_c_rate,
    calculate_soc,
    transform_data
)
from app.etl.validation import (
    generate_validation_report,
    generate_summary_table,
    detect_voltage_anomalies,
    detect_capacity_anomalies,   
)
from app.ui.components.preview_page.data_display_ui import display_data_statistics
from app.ui.components.preview_page.data_display_ui import display_data_tables
from app.ui.components.preview_page.data_display_ui import display_visualizations
from app.visualization import (
    plot_capacity_vs_voltage
)
from app.utils.temp_files import temp_file_from_upload, calculate_file_hash_from_memory, create_session_temp_file

# Define the path to example files
EXAMPLE_FOLDER = "./example_csv_chromaLex"


def apply_transformations(step_df: pd.DataFrame, detail_df: pd.DataFrame, nominal_capacity: float) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Apply transformations to the data and display the results.
    
    Args:
        step_df: DataFrame containing step data
        detail_df: DataFrame containing detail data
        nominal_capacity: Nominal capacity of the battery in Ah
        
    Returns:
        Tuple containing:
        - Transformed step DataFrame
        - Transformed detail DataFrame
    """
    st.subheader("資料轉換")
    
    with st.spinner("正在套用資料轉換..."):
        try:
            # Import the transform_data function
            from app.etl.transformation import transform_data
            
            # Apply complete ETL transformations (includes C-rate, SOC, and pre_test_rest_time)
            st.write("### 套用 ETL 資料轉換")
            
            # Use the complete transform_data function which includes all transformations
            step_df_transformed, detail_df_transformed = transform_data(step_df, detail_df, nominal_capacity)
            # Display C-rate summary
            st.write("### C-rate 計算結果")
            c_rate_stats = {
                'Min C-rate': step_df_transformed['c_rate'].min(),
                'Max C-rate': step_df_transformed['c_rate'].max(),
                'Average C-rate': step_df_transformed['c_rate'].mean()
            }
            
            c_rate_col1, c_rate_col2, c_rate_col3 = st.columns(3)
            with c_rate_col1:
                st.metric("最小 C-rate", f"{c_rate_stats['Min C-rate']:.2f}C")
            with c_rate_col2:
                st.metric("最大 C-rate", f"{c_rate_stats['Max C-rate']:.2f}C")
            with c_rate_col3:
                st.metric("平均 C-rate", f"{c_rate_stats['Average C-rate']:.2f}C")
            
            # Check if pre_test_rest_time was calculated
            if 'pre_test_rest_time' in step_df_transformed.columns:
                st.write("### 前測靜置時間計算結果")
                non_null_count = step_df_transformed['pre_test_rest_time'].notna().sum()
                st.success(f"已成功計算 {non_null_count}/{len(step_df_transformed)} 筆步驟的前測靜置時間")
                if non_null_count > 0:
                    st.info(f"前測靜置時間範圍：{step_df_transformed['pre_test_rest_time'].min():.1f}s - {step_df_transformed['pre_test_rest_time'].max():.1f}s")
            
            # Display SOC calculation results
            st.write("### SOC 計算結果")
            if 'soc_end' in step_df_transformed.columns:
                soc_values = step_df_transformed['soc_end'].dropna()
                if not soc_values.empty:
                    st.success(f"已成功計算 {len(soc_values)} 筆步驟的 SOC")
                    st.info(f"SOC 範圍：{soc_values.min():.1f}% - {soc_values.max():.1f}%")
                else:
                    st.warning("SOC 計算未產生有效數值。")
            else:
                st.warning("未執行 SOC 計算。")
            
            # Return the transformed data
            return step_df_transformed, detail_df_transformed
                
        except Exception as e:
            st.error(f"資料轉換時發生錯誤。詳細資訊：{str(e)}")
            return step_df, detail_df


def create_file_upload_area() -> Tuple[Optional[str], Optional[str]]:
    """
    Create file upload area for step and detail files.
    Also sets session state for 'uploaded_file_names' or 'selected_example_pair'.
    
    Returns:
        Tuple containing:
        - Path to Step.csv file (or None)
        - Path to Detail.csv file (or None)
    """
    st.header("上傳資料檔案")
    
    use_example_files_checked = st.checkbox(
        "使用範例檔案（來自 example_csv_chromaLex 資料夾）", 
        key="use_example_files",
        help="勾選此選項可快速使用內建範例 CSV 檔案進行展示。"
    )
    
    step_file_path = None
    detail_file_path = None
    
    if use_example_files_checked:
        # Clear uploaded file states if switching to example files
        if 'uploaded_file_names' in st.session_state:
            del st.session_state['uploaded_file_names']
        for key_to_clear in ['step_file_content', 'detail_file_content', 'step_file_name', 'detail_file_name', 'step_file_hash', 'detail_file_hash']:
            if key_to_clear in st.session_state:
                del st.session_state[key_to_clear]

        example_step_files = [f for f in os.listdir(EXAMPLE_FOLDER) if f.endswith("_Step.csv")]
        example_detail_files = [f for f in os.listdir(EXAMPLE_FOLDER) if f.endswith("_Detail.csv")]
        
        if not example_step_files or not example_detail_files:
            st.error(f"在 '{EXAMPLE_FOLDER}' 資料夾中找不到範例 CSV 檔案。")
            if 'selected_example_pair' in st.session_state: # Clear if previously set and now no examples
                del st.session_state['selected_example_pair']
        else:
            st.success(f"已找到 {len(example_step_files)} 個範例 Step 檔案與 {len(example_detail_files)} 個範例 Detail 檔案。")
            example_pairs = []
            for step_f_name in example_step_files: # Renamed variable
                base_name = step_f_name.replace("_Step.csv", "")
                detail_f_name = f"{base_name}_Detail.csv" # Renamed variable
                if detail_f_name in example_detail_files:
                    example_pairs.append((base_name, step_f_name, detail_f_name))
            
            if example_pairs:
                selected_pair_index = st.selectbox(
                    "選擇範例檔案組：",
                    options=range(len(example_pairs)),
                    format_func=lambda i: example_pairs[i][0],
                    key="example_pair_selector_widget",
                    help="從範例中選擇一組 Step 與 Detail CSV 檔案。"
                )
                
                base_name, selected_step_file, selected_detail_file = example_pairs[selected_pair_index]
                st.info(f"使用範例檔案：**{selected_step_file}** 與 **{selected_detail_file}**")
                
                step_file_path = os.path.join(EXAMPLE_FOLDER, selected_step_file)
                detail_file_path = os.path.join(EXAMPLE_FOLDER, selected_detail_file)
                # SET SESSION STATE for example files
                st.session_state['selected_example_pair'] = (base_name, step_file_path, detail_file_path)
            else:
                st.warning("找不到對應的 Step 與 Detail 檔案組。")
                if 'selected_example_pair' in st.session_state: # Clear if no pairs found
                    del st.session_state['selected_example_pair']
    else: # Regular file upload
        # Clear example file state if switching to upload
        if 'selected_example_pair' in st.session_state:
            del st.session_state['selected_example_pair']

        col1, col2 = st.columns(2)
        
        with col1:
            step_file_widget_output = st.file_uploader(
                "上傳 Step.csv", type=["csv"], help="包含步驟層級資料的 CSV 檔案", key="step_file"
            )
            if step_file_widget_output:
                st.session_state["step_file_content"] = step_file_widget_output
                st.session_state["step_file_name"] = step_file_widget_output.name
                st.session_state["step_file_hash"] = calculate_file_hash_from_memory(step_file_widget_output.getbuffer())
                step_file_path = create_session_temp_file(
                    step_file_widget_output, 
                    file_key=f"step_{st.session_state['step_file_hash']}", 
                    suffix=".csv"
                )
            else: # File removed or not uploaded
                for key_to_clear in ["step_file_content", "step_file_name", "step_file_hash"]:
                    if key_to_clear in st.session_state:
                        del st.session_state[key_to_clear]
        
        with col2:
            detail_file_widget_output = st.file_uploader(
                "上傳 Detail.csv", type=["csv"], help="包含詳細量測資料的 CSV 檔案", key="detail_file"
            )
            if detail_file_widget_output:
                st.session_state["detail_file_content"] = detail_file_widget_output
                st.session_state["detail_file_name"] = detail_file_widget_output.name
                st.session_state["detail_file_hash"] = calculate_file_hash_from_memory(detail_file_widget_output.getbuffer())
                detail_file_path = create_session_temp_file(
                    detail_file_widget_output,
                    file_key=f"detail_{st.session_state['detail_file_hash']}",
                    suffix=".csv"
                )
            else: # File removed or not uploaded
                for key_to_clear in ["detail_file_content", "detail_file_name", "detail_file_hash"]:
                    if key_to_clear in st.session_state:
                        del st.session_state[key_to_clear]

        # SET SESSION STATE for uploaded files if both are present
        s_content = st.session_state.get("step_file_content")
        d_content = st.session_state.get("detail_file_content")

        if s_content and d_content:
            st.session_state['uploaded_file_names'] = (s_content.name, d_content.name)
        else:
            # If one or both files are missing (cleared above or never uploaded), clear the pair name
            if 'uploaded_file_names' in st.session_state:
                del st.session_state['uploaded_file_names']
                 

    return step_file_path, detail_file_path


def render_preview_page():
    """
    Render the data preview page UI.
    
    This function displays the UI for uploading and previewing battery test data files,
    including basic analysis, visualizations, and data validation.
    """
    st.title("🔋 電池資料預覽")
    st.subheader("上傳並分析您的資料後再進行處理")
    reload_col, continue_col = st.columns([1, 3])
    with reload_col:
        if st.button("🔄 重載預覽頁", key="reload_preview_page_btn"):
            # 清除 session_state 中相關資料
            for k in [
                'steps_df', 'details_df',
                'steps_df_transformed', 'details_df_transformed',
                'step_file_name', 'detail_file_name',
                'step_file_hash', 'detail_file_hash',
                'step_file_content', 'detail_file_content',
                'selected_reference_step', 'reference_step_selector'
            ]:
                if k in st.session_state:
                    del st.session_state[k]
            st.rerun()  
    # Create UI for nominal capacity input
    nominal_capacity = st.number_input(
        "額定容量 (Ah)",
        min_value=0.01,
        value=3.0,
        step=0.1,
        format="%.2f",
        help="請輸入電池的額定容量（安培小時, Ah），此數值將用於 C-rate 計算。"
    )

    # --- 新增：如果 session_state 已有處理過的資料，直接顯示 preview ---
    if (
        'steps_df_transformed' in st.session_state and
        'details_df_transformed' in st.session_state and
        st.session_state['steps_df_transformed'] is not None and
        st.session_state['details_df_transformed'] is not None
    ):
        step_df = st.session_state['steps_df_transformed']
        detail_df = st.session_state['details_df_transformed']
        st.success("檔案載入成功，可進行資料處理。")
        display_data_statistics(step_df, detail_df)
        display_data_tables(step_df, detail_df)
        display_visualizations(step_df, detail_df)
        st.success("資料預覽完成！您現在可以進入步驟選擇。")
        if st.button("進入步驟選擇", type="primary", key="continue_to_step_selection_btn"):
            st.session_state['current_page'] = "Step Selection"
            st.rerun()
        # Navigation help
        with st.expander("如何使用本頁面"):
            st.write("""
            1. 輸入您的電池額定容量
            2. 上傳 Step.csv 與 Detail.csv 檔案，或選擇範例檔案
            3. 點擊「處理檔案」以分析與視覺化資料
            4. 檢查資料表、圖表與驗證結果
            5. 確認無誤後，點擊「進入步驟選擇」進行下一步
            """)
        return
    # --- 原本流程 ---
    # Handle file uploads
    step_file_path, detail_file_path = create_file_upload_area()
    
    # Check if we have valid files
    if step_file_path and detail_file_path:
        st.success("檔案載入成功，可進行資料處理。")
        
        # Process button
        if st.button("處理檔案", type="primary"):
            with st.spinner("檔案處理中..."):
                try:
                    # Validate files first
                    step_valid, step_missing, _ = validate_csv_format(step_file_path, STEP_REQUIRED_HEADERS)
                    detail_valid, detail_missing, _ = validate_csv_format(detail_file_path, DETAIL_REQUIRED_HEADERS)
                    
                    if not step_valid:
                        st.error(f"Step.csv 缺少必要欄位：{', '.join(step_missing)}")
                    elif not detail_valid:
                        st.error(f"Detail.csv 缺少必要欄位：{', '.join(detail_missing)}")
                    else:
                        # Process the files
                        step_df = parse_step_csv(step_file_path)
                        detail_df = parse_detail_csv(detail_file_path)
                        
                        # Store the raw data in session state
                        st.session_state['steps_df'] = step_df
                        st.session_state['details_df'] = detail_df
                        
                        # Display statistics section
                        display_data_statistics(step_df, detail_df)
                        
                        # Apply transformations (this will display C-Rate and SOC Calculation sections)
                        steps_df_transformed, details_df_transformed = apply_transformations(
                            step_df, detail_df, nominal_capacity
                        )
                        
                        # Store transformed data in session state
                        st.session_state['steps_df_transformed'] = steps_df_transformed
                        st.session_state['details_df_transformed'] = details_df_transformed
                        
                        # Display data tables section (now using transformed data)
                        display_data_tables(steps_df_transformed, details_df_transformed)
                        
                        # Display visualization section
                        display_visualizations(steps_df_transformed, details_df_transformed)
                        
                        
                        # Provide a button to continue to step selection
                        st.success("資料預覽與初步轉換已完成！")
                        st.info("請檢查下方資料，若正確即可進入步驟選擇，挑選欲進一步分析與匯入資料庫的步驟。")
                        with continue_col:
                            if st.button("進入步驟選擇", type="primary", key="continue_to_step_selection_btn"):
                                st.session_state['current_page'] = "Step Selection"
                                st.rerun()
                                                
                except Exception as e:
                    st.error(f"檔案處理時發生錯誤，請確認格式正確。詳細資訊：{str(e)}")
    
    # Navigation help
    with st.expander("如何使用本頁面"):
        st.write("""
        1. 輸入您的電池額定容量
        2. 上傳 Step.csv 與 Detail.csv 檔案，或選擇範例檔案
        3. 點擊「處理檔案」以分析與視覺化資料
        4. 檢查資料表、圖表與驗證結果
        5. 確認無誤後，點擊「進入步驟選擇」進行下一步
        """)


if __name__ == "__main__":
    # For testing purposes
    render_preview_page()