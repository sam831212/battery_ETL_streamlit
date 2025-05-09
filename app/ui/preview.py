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
    detect_temperature_anomalies
)
from app.visualization import (
    plot_capacity_vs_voltage,
    plot_voltage_vs_time,
    plot_current_vs_time,
    plot_temperature_vs_time,
    plot_combined_voltage_current
)
from app.utils.temp_files import temp_file_from_upload, calculate_file_hash_from_memory, create_session_temp_file

# Define the path to example files
EXAMPLE_FOLDER = "./example_csv_chromaLex"


def display_data_statistics(step_df: pd.DataFrame, detail_df: pd.DataFrame):
    """
    Display basic statistics about the data files.
    
    Args:
        step_df: DataFrame containing step data
        detail_df: DataFrame containing detail data
    """
    st.subheader("Data Statistics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Steps", step_df['step_number'].nunique())
    
    with col2:
        st.metric("Step Records", len(step_df))
    
    with col3:
        st.metric("Detail Records", len(detail_df))
    
    with col4:
        step_types = step_df['step_type'].value_counts()
        common_step = step_types.index[0] if not step_types.empty else "N/A"
        st.metric("Primary Step Type", common_step)
    
    # Display step type distribution
    step_type_counts = step_df['step_type'].value_counts().reset_index()
    step_type_counts.columns = ['Step Type', 'Count']
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.write("Step Types")
        st.dataframe(step_type_counts, use_container_width=True)
    
    with col2:
        fig = px.pie(
            step_type_counts, 
            values='Count', 
            names='Step Type', 
            title='Distribution of Step Types',
            color='Step Type',
            color_discrete_sequence=px.colors.qualitative.Bold
        )
        fig.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig, use_container_width=True)


def display_data_tables(step_df: pd.DataFrame, detail_df: pd.DataFrame):
    """
    Display data tables with tabs for different tables.
    
    Args:
        step_df: DataFrame containing step data
        detail_df: DataFrame containing detail data
    """
    st.subheader("Data Tables")
    
    # Create tabs for different data tables
    table_tabs = st.tabs([
        "Step Data", 
        "Detail Data", 
        "Statistics"
    ])
    
    # Tab 1: Step Data
    with table_tabs[0]:
        st.write("### Step Data Preview")
        
        # Add column filter
        all_step_columns = step_df.columns.tolist()
        default_step_columns = ['step_number', 'step_type', 'original_step_type', 
                               'capacity', 'current', 'voltage_start', 'voltage_end']
        
        # Ensure default columns exist in the data
        default_step_columns = [col for col in default_step_columns if col in all_step_columns]
        
        selected_step_columns = st.multiselect(
            "Select columns to display:",
            options=all_step_columns,
            default=default_step_columns
        )
        
        if selected_step_columns:
            st.dataframe(
                step_df[selected_step_columns],
                use_container_width=True,
                height=300
            )
        else:
            st.info("Please select at least one column to display.")
    
    # Tab 2: Detail Data
    with table_tabs[1]:
        st.write("### Detail Data Preview")
        
        # Add column filter
        all_detail_columns = detail_df.columns.tolist()
        default_detail_columns = ['step_number', 'current', 'voltage', 
                                 'capacity', 'temperature', 'timestamp']
        
        # Ensure default columns exist in the data
        default_detail_columns = [col for col in default_detail_columns if col in all_detail_columns]
        
        selected_detail_columns = st.multiselect(
            "Select columns to display:",
            options=all_detail_columns,
            default=default_detail_columns
        )
        
        if selected_detail_columns:
            # For large datasets, show only a sample
            if len(detail_df) > 10000:
                st.info(f"Showing a sample of {10000} records out of {len(detail_df)} total records.")
                display_df = detail_df.sample(10000) if len(detail_df) > 10000 else detail_df
            else:
                display_df = detail_df
                
            st.dataframe(
                display_df[selected_detail_columns],
                use_container_width=True,
                height=300
            )
        else:
            st.info("Please select at least one column to display.")
    
    # Tab 3: Statistics
    with table_tabs[2]:
        st.write("### Data Statistics")
        
        stats_tabs = st.tabs([
            "Step Statistics", 
            "Detail Statistics"
        ])
        
        with stats_tabs[0]:
            st.write("#### Step Data Statistics")
            
            # For numeric columns only
            numeric_cols = step_df.select_dtypes(include=['number']).columns.tolist()
            if numeric_cols:
                stats_df = step_df[numeric_cols].describe().T
                st.dataframe(stats_df, use_container_width=True)
            else:
                st.info("No numeric columns found in step data.")
        
        with stats_tabs[1]:
            st.write("#### Detail Data Statistics")
            
            # For numeric columns only
            numeric_cols = detail_df.select_dtypes(include=['number']).columns.tolist()
            if numeric_cols:
                # For large datasets, calculate stats on a sample
                if len(detail_df) > 50000:
                    st.info(f"Calculating statistics on a sample of 50,000 records due to large dataset size.")
                    stats_df = detail_df[numeric_cols].sample(50000).describe().T
                else:
                    stats_df = detail_df[numeric_cols].describe().T
                st.dataframe(stats_df, use_container_width=True)
            else:
                st.info("No numeric columns found in detail data.")


def display_visualizations(step_df: pd.DataFrame, detail_df: pd.DataFrame):
    """
    Display visualizations with tabs for different plot types.
    
    Args:
        step_df: DataFrame containing step data
        detail_df: DataFrame containing detail data
    """
    st.subheader("Data Visualization")
    
    # Create tabs for different visualization types
    viz_tabs = st.tabs([
        "Voltage-Time", 
        "Current-Time",
        "Temperature-Time",
        "Combined Plots"
    ])
    
    # Tab 1: Voltage vs Time
    with viz_tabs[0]:
        st.write("### Voltage vs Time")
        
        try:
            # Use detail data for time series plots
            # Limit to 10,000 points for performance
            if len(detail_df) > 10000:
                st.info(f"Showing plot with 10,000 sample points out of {len(detail_df)} total points for performance.")
                plot_data = detail_df.sample(10000)
            else:
                plot_data = detail_df
                
            vt_fig = plot_voltage_vs_time(
                plot_data,
                voltage_col='voltage',
                time_col='timestamp',
                step_type_col='step_type',
                step_number_col='step_number',
                highlight_anomalies=True,
                title='Voltage vs Time by Step Type'
            )
            st.plotly_chart(vt_fig, use_container_width=True)
        except Exception as e:
            st.error(f"Error generating Voltage vs Time plot: {str(e)}")
            st.info("This plot requires 'voltage', 'timestamp', and 'step_type' columns in the detail data.")
    
    # Tab 2: Current vs Time
    with viz_tabs[1]:
        st.write("### Current vs Time")
        
        try:
            # Use detail data for time series plots
            # Limit to 10,000 points for performance
            if len(detail_df) > 10000:
                plot_data = detail_df.sample(10000)
            else:
                plot_data = detail_df
                
            ct_fig = plot_current_vs_time(
                plot_data,
                current_col='current',
                time_col='timestamp',
                step_type_col='step_type',
                step_number_col='step_number',
                highlight_anomalies=True,
                title='Current vs Time by Step Type'
            )
            st.plotly_chart(ct_fig, use_container_width=True)
        except Exception as e:
            st.error(f"Error generating Current vs Time plot: {str(e)}")
            st.info("This plot requires 'current', 'timestamp', and 'step_type' columns in the detail data.")
    
    # Tab 3: Temperature vs Time
    with viz_tabs[2]:
        st.write("### Temperature vs Time")
        
        try:
            # Use detail data for time series plots
            # Limit to 10,000 points for performance
            if len(detail_df) > 10000:
                plot_data = detail_df.sample(10000)
            else:
                plot_data = detail_df
                
            temp_fig = plot_temperature_vs_time(
                plot_data,
                temperature_col='temperature',
                time_col='timestamp',
                step_type_col='step_type',
                step_number_col='step_number',
                highlight_anomalies=True,
                title='Temperature vs Time by Step Type'
            )
            st.plotly_chart(temp_fig, use_container_width=True)
        except Exception as e:
            st.error(f"Error generating Temperature vs Time plot: {str(e)}")
            st.info("This plot requires 'temperature', 'timestamp', and 'step_type' columns in the detail data.")
    
    # Tab 4: Combined Plots
    with viz_tabs[3]:
        st.write("### Combined Voltage, Current, and Temperature")
        
        try:
            # Use detail data for time series plots
            # Limit to 10,000 points for performance
            if len(detail_df) > 10000:
                plot_data = detail_df.sample(10000)
            else:
                plot_data = detail_df
                
            combined_fig = plot_combined_voltage_current(
                plot_data,
                voltage_col='voltage',
                current_col='current',
                temperature_col='temperature',
                time_col='timestamp',
                step_type_col='step_type',
                step_number_col='step_number',
                include_temperature=True,
                highlight_anomalies=True,
                title='Voltage, Current, and Temperature vs Time'
            )
            st.plotly_chart(combined_fig, use_container_width=True)
        except Exception as e:
            st.error(f"Error generating Combined plot: {str(e)}")
            st.info("This plot requires 'voltage', 'current', 'temperature', 'timestamp', and 'step_type' columns in the detail data.")


def display_data_validation(step_df: pd.DataFrame, detail_df: pd.DataFrame):
    """
    Display data validation results and anomaly detection.
    
    Args:
        step_df: DataFrame containing step data
        detail_df: DataFrame containing detail data
    """
    st.subheader("Data Validation")
    
    with st.spinner("Running data validation and anomaly detection..."):
        try:
            # Generate validation reports
            step_validation = generate_validation_report(step_df)
            detail_validation = generate_validation_report(detail_df)
            
            # Display validation summary
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("#### Step Data Validation")
                step_summary = step_validation['summary']
                
                st.metric("Total Issues", step_summary['total_issues'])
                st.metric("Critical Issues", step_summary['critical_issues'])
                
                # Display validation issues
                if step_summary['total_issues'] > 0:
                    with st.expander("View Step Validation Issues"):
                        for severity in ['critical', 'warning', 'info']:
                            issues = step_validation['issues_by_severity'][severity]
                            if issues:
                                st.write(f"**{severity.capitalize()} Issues:**")
                                for issue in issues:
                                    st.write(f"- {issue}")
            
            with col2:
                st.write("#### Detail Data Validation")
                detail_summary = detail_validation['summary']
                
                st.metric("Total Issues", detail_summary['total_issues'])
                st.metric("Critical Issues", detail_summary['critical_issues'])
                
                # Display validation issues
                if detail_summary['total_issues'] > 0:
                    with st.expander("View Detail Validation Issues"):
                        for severity in ['critical', 'warning', 'info']:
                            issues = detail_validation['issues_by_severity'][severity]
                            if issues:
                                st.write(f"**{severity.capitalize()} Issues:**")
                                for issue in issues:
                                    st.write(f"- {issue}")
            
            # Display overall validation status
            overall_valid = step_validation['valid'] and detail_validation['valid']
            if overall_valid:
                st.success("Overall data validation passed!")
            else:
                st.warning("Data validation found issues that may need addressing.")
        
        except Exception as e:
            st.error(f"Error during data validation: {str(e)}")


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
                    st.success(f"Found {len(discharge_steps)} discharge steps.")
                    
                    # Check for total_capacity column
                    if 'total_capacity' not in step_df.columns:
                        st.error("No 'total_capacity' column found. The '總電壓(Ah)' column might be missing in the Step.csv file.")
                        return step_df, detail_df
                    else:
                        # Find the 2nd discharge step as reference by default
                        discharge_steps_sorted = discharge_steps.sort_values('step_number')
                        
                        if len(discharge_steps) >= 2:
                            reference_step_idx = discharge_steps_sorted.index[1]  # 2nd discharge step
                            reference_step = discharge_steps.loc[reference_step_idx]
                            st.write(f"Using the 2nd discharge step (step {reference_step['step_number']}) as reference. Voltage: {reference_step['voltage_end']}V")
                        else:
                            reference_step_idx = discharge_steps_sorted.index[0]  # 1st discharge step if only one exists
                            reference_step = discharge_steps.loc[reference_step_idx]
                            st.write(f"Using the only discharge step (step {reference_step['step_number']}) as reference. Voltage: {reference_step['voltage_end']}V")
                        
                        # Create a reference step selector
                        discharge_steps_dict = {
                            f"Step {row['step_number']} ({row['original_step_type']})": idx 
                            for idx, row in discharge_steps.iterrows()
                        }
                        
                        selected_reference = st.selectbox(
                            "Select reference discharge step for 0% SOC:",
                            options=list(discharge_steps_dict.keys()),
                            index=list(discharge_steps_dict.keys()).index(f"Step {reference_step['step_number']} ({reference_step['original_step_type']})") 
                                if f"Step {reference_step['step_number']} ({reference_step['original_step_type']})" in discharge_steps_dict.keys() else 0
                        )
                        
                        selected_reference_idx = discharge_steps_dict[selected_reference]
                        
                        # Try SOC calculation with explicit reference
                        steps_with_soc, details_with_soc = calculate_soc(
                            step_df.copy(), 
                            detail_df.copy(),
                            full_discharge_step_idx=selected_reference_idx
                        )
                        
                        # Display SOC results
                        st.write("Steps with SOC calculated:")
                        
                        # Show selected columns with SOC
                        soc_cols = ['step_number', 'original_step_type', 'step_type', 'capacity', 'total_capacity', 
                                   'voltage_end', 'soc_start', 'soc_end']
                        
                        # Ensure columns exist in the data
                        soc_cols = [col for col in soc_cols if col in steps_with_soc.columns]
                        
                        st.dataframe(steps_with_soc[soc_cols], use_container_width=True)
                        
                        # Plot SOC vs voltage
                        steps_with_soc_values = steps_with_soc.dropna(subset=['soc_end'])
                        
                        if not steps_with_soc_values.empty:
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                fig = px.scatter(
                                    steps_with_soc_values, 
                                    x='voltage_end', 
                                    y='soc_end',
                                    title='SOC vs Voltage',
                                    labels={'voltage_end': 'Voltage (V)', 'soc_end': 'SOC (%)'},
                                    hover_data=['step_number', 'original_step_type', 'total_capacity'],
                                    color='step_type'
                                )
                                st.plotly_chart(fig, use_container_width=True)
                            
                            with col2:
                                if 'total_capacity' in steps_with_soc_values.columns:
                                    fig = px.scatter(
                                        steps_with_soc_values, 
                                        x='total_capacity', 
                                        y='soc_end', 
                                        title='SOC vs Total Capacity',
                                        labels={'total_capacity': 'Total Capacity (Ah)', 'soc_end': 'SOC (%)'},
                                        hover_data=['step_number', 'original_step_type'],
                                        color='step_type'
                                    )
                                    st.plotly_chart(fig, use_container_width=True)
                            
                            # Success message
                            st.success("Successfully calculated SOC for this dataset!")
                            
                            return steps_with_soc, details_with_soc
                        else:
                            st.warning("No valid SOC values calculated. Check the reference step selection.")
                            return step_df, detail_df
            
            except Exception as e:
                st.error(f"Error calculating SOC: {str(e)}")
                st.error("Check if the reference step has valid capacity data.")
                return step_df, detail_df
                
        except Exception as e:
            st.error(f"Error applying transformations: {str(e)}")
            return step_df, detail_df


def create_file_upload_area() -> Tuple[Optional[str], Optional[str]]:
    """
    Create file upload area for step and detail files.
    
    Returns:
        Tuple containing:
        - Path to Step.csv file (or None)
        - Path to Detail.csv file (or None)
    """
    st.header("Upload Data Files")
    
    # Option to use example files
    use_example_files = st.checkbox("Use example files from example_csv_chromaLex folder", key="use_example_files")
    
    step_file_path = None
    detail_file_path = None
    
    if use_example_files:
        # Display list of available example files
        example_step_files = [f for f in os.listdir(EXAMPLE_FOLDER) if f.endswith("_Step.csv")]
        example_detail_files = [f for f in os.listdir(EXAMPLE_FOLDER) if f.endswith("_Detail.csv")]
        
        if not example_step_files or not example_detail_files:
            st.error("No example files found in the example_csv_chromaLex folder.")
        else:
            st.success(f"Found {len(example_step_files)} step files and {len(example_detail_files)} detail files.")
            
            # Automatically match related step and detail files
            example_pairs = []
            for step_file in example_step_files:
                base_name = step_file.replace("_Step.csv", "")
                detail_file = f"{base_name}_Detail.csv"
                if detail_file in example_detail_files:
                    example_pairs.append((base_name, step_file, detail_file))
            
            if example_pairs:
                selected_pair = st.selectbox(
                    "Select example file pair:",
                    options=range(len(example_pairs)),
                    format_func=lambda i: example_pairs[i][0]
                )
                
                _, selected_step_file, selected_detail_file = example_pairs[selected_pair]
                
                st.info(f"Selected files: {selected_step_file} and {selected_detail_file}")
                
                # Set the file paths
                step_file_path = os.path.join(EXAMPLE_FOLDER, selected_step_file)
                detail_file_path = os.path.join(EXAMPLE_FOLDER, selected_detail_file)
            else:
                st.warning("No matching step and detail file pairs found.")
    else:
        # Regular file upload
        col1, col2 = st.columns(2)
        
        with col1:
            step_file = st.file_uploader(
                "Upload Step.csv",
                type=["csv"],
                help="CSV file containing step-level data",
                key="step_file",
            )
            
            if step_file:
                # Store the file name in session state so we can access it later
                st.session_state["step_file_name"] = step_file.name
                # Calculate hash from memory for duplicate detection
                st.session_state["step_file_hash"] = calculate_file_hash_from_memory(step_file.getbuffer())
                # Store the file in memory
                st.session_state["step_file_content"] = step_file
                # Use a session-persistent temporary file
                step_file_path = create_session_temp_file(
                    step_file, 
                    file_key=f"step_{st.session_state['step_file_hash']}", 
                    suffix=".csv"
                )
        
        with col2:
            detail_file = st.file_uploader(
                "Upload Detail.csv",
                type=["csv"],
                help="CSV file containing detailed measurement data",
                key="detail_file",
            )
            
            if detail_file:
                # Store the file name in session state so we can access it later
                st.session_state["detail_file_name"] = detail_file.name
                # Calculate hash from memory for duplicate detection
                st.session_state["detail_file_hash"] = calculate_file_hash_from_memory(detail_file.getbuffer())
                # Store the file in memory
                st.session_state["detail_file_content"] = detail_file
                # Use a session-persistent temporary file
                detail_file_path = create_session_temp_file(
                    detail_file,
                    file_key=f"detail_{st.session_state['detail_file_hash']}",
                    suffix=".csv"
                )
    
    return step_file_path, detail_file_path


def render_preview_page():
    """
    Render the data preview page UI.
    
    This function displays the UI for uploading and previewing battery test data files,
    including basic analysis, visualizations, and data validation.
    """
    st.title("🔋 Battery Data Preview")
    st.subheader("Upload and analyze your data before processing")
    
    # Create UI for nominal capacity input
    nominal_capacity = st.number_input(
        "Nominal Capacity (Ah)",
        min_value=0.1,
        value=3.0,
        help="Nominal capacity of the battery in Amp-hours"
    )
    
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
                        
                        # Display data tables section
                        display_data_tables(step_df, detail_df)
                        
                        # Apply transformations
                        steps_df_transformed, details_df_transformed = apply_transformations(
                            step_df, detail_df, nominal_capacity
                        )
                        
                        # Store transformed data in session state
                        st.session_state['steps_df_transformed'] = steps_df_transformed
                        st.session_state['details_df_transformed'] = details_df_transformed
                        
                        # Display visualization section
                        display_visualizations(steps_df_transformed, details_df_transformed)
                        
                        # Display data validation section
                        display_data_validation(steps_df_transformed, details_df_transformed)
                        
                        # Provide a button to continue to step selection
                        st.success("Data preview complete! You can now proceed to Step Selection to choose which steps to include.")
                        
                        if st.button("Continue to Step Selection", type="primary", key="continue_to_step_selection_btn"):
                            st.session_state['current_page'] = "Step Selection"
                            st.rerun()
                        
                except Exception as e:
                    st.error(f"Error processing files: {str(e)}")
    
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