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
    st.subheader("Data Transformations")
    
    with st.spinner("Applying transformations..."):
        try:
            # First calculate C-rates
            st.write("### C-rate Calculation")
            
            # Apply C-rate calculation
            step_df['c_rate'] = step_df['current'].apply(
                lambda current: calculate_c_rate(current, nominal_capacity)
            )
            detail_df['c_rate'] = detail_df['current'].apply(
                lambda current: calculate_c_rate(current, nominal_capacity)
            )
            
            # Display C-rate summary
            c_rate_stats = {
                'Min C-rate': step_df['c_rate'].min(),
                'Max C-rate': step_df['c_rate'].max(),
                'Average C-rate': step_df['c_rate'].mean()
            }
            
            c_rate_col1, c_rate_col2, c_rate_col3 = st.columns(3)
            with c_rate_col1:
                st.metric("Min C-rate", f"{c_rate_stats['Min C-rate']:.2f}C")
            with c_rate_col2:
                st.metric("Max C-rate", f"{c_rate_stats['Max C-rate']:.2f}C")
            with c_rate_col3:
                st.metric("Avg C-rate", f"{c_rate_stats['Average C-rate']:.2f}C")
            
            # Try to calculate SOC with error handling
            st.write("### SOC Calculation")
            
            try:
                # First select discharge steps
                discharge_steps = step_df[step_df['step_type'] == 'discharge']
                
                if len(discharge_steps) == 0:
                    st.warning("No discharge steps found in the data. SOC calculation requires discharge steps.")
                    return step_df, detail_df
                else:
                    st.success(f"Found {len(discharge_steps)} discharge steps available for SOC reference.")
                    
                    # Check for total_capacity column
                    if 'total_capacity' not in step_df.columns:
                        st.error("No 'total_capacity' column found. The '總電壓(Ah)' column might be missing or misnamed in the Step.csv file.")
                        return step_df, detail_df
                    else:
                        # Find the 2nd discharge step as reference by default
                        discharge_steps_sorted = discharge_steps.sort_values('step_number')
                        
                        if len(discharge_steps_sorted) >= 2:
                            reference_step_idx = discharge_steps_sorted.index[1]  # 2nd discharge step
                            reference_step = discharge_steps_sorted.loc[reference_step_idx]
                            default_reference = f"Step {reference_step['step_number']} ({reference_step['original_step_type']})"
                        elif not discharge_steps_sorted.empty: # Handles if only one discharge step exists
                            reference_step_idx = discharge_steps_sorted.index[0]  # 1st discharge step
                            reference_step = discharge_steps_sorted.loc[reference_step_idx]
                            default_reference = f"Step {reference_step['step_number']} ({reference_step['original_step_type']})"
                        else: # Should not happen due to earlier check, but as a fallback
                            st.warning("Could not determine a default reference step for SOC calculation.")
                            return step_df, detail_df

                        # Create a reference step selector
                        discharge_steps_dict = {
                            f"Step {row['step_number']} ({row['original_step_type']})": idx 
                            for idx, row in discharge_steps_sorted.iterrows() # Use sorted steps
                        }
                        
                        # Initialize session state for reference step if not exists
                        if 'selected_reference_step' not in st.session_state or st.session_state.selected_reference_step not in discharge_steps_dict:
                            st.session_state.selected_reference_step = default_reference
                        
                        # Define callback function for selectbox
                        def on_reference_step_change():
                            st.session_state.selected_reference_step = st.session_state.reference_step_selector # key of selectbox
                        
                        # Create selectbox with callback
                        selected_reference_label = st.selectbox(
                            "Select reference discharge step for 0% SOC:",
                            options=list(discharge_steps_dict.keys()),
                            index=list(discharge_steps_dict.keys()).index(st.session_state.selected_reference_step),
                            key="reference_step_selector", # This key is used by the callback
                            on_change=on_reference_step_change,
                            help="Choose a discharge step that represents a fully discharged state (0% SOC). This is crucial for accurate SOC calculation."
                        )
                        
                        selected_reference_idx = discharge_steps_dict[selected_reference_label]
                        
                        # Try SOC calculation with explicit reference
                        steps_with_soc, details_with_soc = calculate_soc(
                            step_df.copy(), 
                            detail_df.copy(),
                            full_discharge_step_idx=selected_reference_idx
                        )
                        
                        # Check if SOC calculation was successful
                        steps_with_soc_values = steps_with_soc.dropna(subset=['soc_end'])
                        
                        if not steps_with_soc_values.empty:
                            # Success message
                            st.success("Successfully calculated SOC for this dataset!")
                            
                            return steps_with_soc, details_with_soc
                        else:
                            st.warning("SOC calculation did not produce valid values. Please check the selected reference step and its data.")
                            return step_df, detail_df
            
            except Exception as e:
                st.error(f"An error occurred during SOC calculation. Please check your data and reference step. Details: {str(e)}")
                st.info("Ensure the selected reference step has valid capacity data and is appropriate for defining 0% SOC.")
                return step_df, detail_df
                
        except Exception as e:
            st.error(f"An error occurred during data transformation. Details: {str(e)}")
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
    st.header("Upload Data Files")
    
    # Using the key "use_example_files" as in the original file for the checkbox state
    use_example_files_checked = st.checkbox(
        "Use example files from example_csv_chromaLex folder", 
        key="use_example_files", # Original key
        help="Check this box to use pre-packaged example CSV files for a quick demonstration."
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
            st.error(f"No example CSV files found in the '{EXAMPLE_FOLDER}' directory.")
            if 'selected_example_pair' in st.session_state: # Clear if previously set and now no examples
                del st.session_state['selected_example_pair']
        else:
            st.success(f"Found {len(example_step_files)} example step files and {len(example_detail_files)} example detail files.")
            example_pairs = []
            for step_f_name in example_step_files: # Renamed variable
                base_name = step_f_name.replace("_Step.csv", "")
                detail_f_name = f"{base_name}_Detail.csv" # Renamed variable
                if detail_f_name in example_detail_files:
                    example_pairs.append((base_name, step_f_name, detail_f_name))
            
            if example_pairs:
                selected_pair_index = st.selectbox(
                    "Select example file pair:",
                    options=range(len(example_pairs)),
                    format_func=lambda i: example_pairs[i][0],
                    key="example_pair_selector_widget", # Added a key for stability
                    help="Choose a pair of Step and Detail CSV files from the examples."
                )
                
                base_name, selected_step_file, selected_detail_file = example_pairs[selected_pair_index]
                st.info(f"Using example files: **{selected_step_file}** and **{selected_detail_file}**")
                
                step_file_path = os.path.join(EXAMPLE_FOLDER, selected_step_file)
                detail_file_path = os.path.join(EXAMPLE_FOLDER, selected_detail_file)
                # SET SESSION STATE for example files
                st.session_state['selected_example_pair'] = (base_name, step_file_path, detail_file_path)
            else:
                st.warning("No matching step and detail file pairs found.")
                if 'selected_example_pair' in st.session_state: # Clear if no pairs found
                    del st.session_state['selected_example_pair']
    else: # Regular file upload
        # Clear example file state if switching to upload
        if 'selected_example_pair' in st.session_state:
            del st.session_state['selected_example_pair']

        col1, col2 = st.columns(2)
        
        # Logic based on original file's way of handling file uploaders and session state
        with col1:
            step_file_widget_output = st.file_uploader(
                "Upload Step.csv", type=["csv"], help="CSV file containing step-level data", key="step_file"
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
                "Upload Detail.csv", type=["csv"], help="CSV file containing detailed measurement data", key="detail_file"
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
    st.title("🔋 Battery Data Preview")
    st.subheader("Upload and analyze your data before processing")
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
            st.rerun()  # 修正：新版 Streamlit 用 st.rerun() 取代 st.experimental_rerun()
    # Create UI for nominal capacity input
    nominal_capacity = st.number_input(
        "Nominal Capacity (Ah)",
        min_value=0.01, # Allow smaller capacities
        value=3.0,
        step=0.1,
        format="%.2f",
        help="Enter the battery's nominal capacity in Amp-hours (Ah) as specified by the manufacturer. This is used for C-rate calculations."
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
        st.success("Files loaded successfully. Ready to process data.")
        display_data_statistics(step_df, detail_df)
        display_data_tables(step_df, detail_df)
        display_visualizations(step_df, detail_df)
        st.success("Data preview complete! You can now proceed to Step Selection to choose which steps to include.")
        if st.button("Continue to Step Selection", type="primary", key="continue_to_step_selection_btn"):
            st.session_state['current_page'] = "Step Selection"
            st.rerun()
        # Navigation help
        with st.expander("How to use this page"):
            st.write("""
            1. Enter the nominal capacity of your battery
            2. Either upload your Step.csv and Detail.csv files or select example files
            3. Click 'Process Files' to analyze and visualize your data
            4. Review the data tables, visualizations, and validation results
            5. When ready, click 'Continue to Step Selection' to proceed to the next step
            """)
        return
    # --- 原本流程 ---
    # Handle file uploads
    step_file_path, detail_file_path = create_file_upload_area()
    
    # Check if we have valid files
    if step_file_path and detail_file_path:
        st.success("Files loaded successfully. Ready to process data.")
        
        # Process button
        if st.button("Process Files", type="primary"):
            with st.spinner("Processing files..."):
                try:
                    # Validate files first
                    step_valid, step_missing, _ = validate_csv_format(step_file_path, STEP_REQUIRED_HEADERS)
                    detail_valid, detail_missing, _ = validate_csv_format(detail_file_path, DETAIL_REQUIRED_HEADERS)
                    
                    if not step_valid:
                        st.error(f"Step.csv is missing required headers: {', '.join(step_missing)}")
                    elif not detail_valid:
                        st.error(f"Detail.csv is missing required headers: {', '.join(detail_missing)}")
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
                        st.success("Data preview and initial transformations are complete!")
                        st.info("Review the data below. If everything looks correct, proceed to Step Selection to choose the specific steps for further analysis and database loading.")
                        with continue_col:
                            if st.button("Continue to Step Selection", type="primary", key="continue_to_step_selection_btn"):
                                st.session_state['current_page'] = "Step Selection"
                                st.rerun()
                                                
                except Exception as e:
                    st.error(f"An error occurred while processing the files. Please ensure they are correctly formatted. Details: {str(e)}")
    
    # Navigation help
    with st.expander("How to use this page"):
        st.write("""
        1. Enter the nominal capacity of your battery
        2. Either upload your Step.csv and Detail.csv files or select example files
        3. Click 'Process Files' to analyze and visualize your data
        4. Review the data tables, visualizations, and validation results
        5. When ready, click 'Continue to Step Selection' to proceed to the next step
        """)


if __name__ == "__main__":
    # For testing purposes
    render_preview_page()