"""
Test script for battery data transformations

This script allows testing and visualizing SOC and C-rate calculations
without dealing with database operations.
"""
import os
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

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

# Define the path to example files
EXAMPLE_FOLDER = "./example_csv_chromaLex"

# Configure the page
st.set_page_config(
    page_title="Battery ETL Transformation Tester",
    page_icon="🔋",
    layout="wide"
)

st.title("🔋 Battery Transformation Tester")
st.subheader("Test SOC and C-rate Calculations Without Database")

st.info("This utility allows you to test the SOC and C-rate calculations without saving anything to the database.")

# Ask for nominal capacity
nominal_capacity = st.number_input(
    "Nominal Capacity (Ah)",
    min_value=0.1,
    value=3.0,
    help="Nominal capacity of the battery in Amp-hours"
)

# Load example files
st.subheader("Select Example Files")

# Find example files in the folder
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
        
        base_name, selected_step_file, selected_detail_file = example_pairs[selected_pair]
        
        st.info(f"Selected files: {selected_step_file} and {selected_detail_file}")
        
        # Process button
        if st.button("Process Files", type="primary"):
            with st.spinner("Processing files..."):
                try:
                    step_file_path = os.path.join(EXAMPLE_FOLDER, selected_step_file)
                    detail_file_path = os.path.join(EXAMPLE_FOLDER, selected_detail_file)
                    
                    # Validate files
                    step_valid, step_missing, _ = validate_csv_format(step_file_path, STEP_REQUIRED_HEADERS)
                    detail_valid, detail_missing, _ = validate_csv_format(detail_file_path, DETAIL_REQUIRED_HEADERS)
                    
                    if not step_valid:
                        st.error(f"Step.csv is missing required headers: {', '.join(step_missing)}")
                    elif not detail_valid:
                        st.error(f"Detail.csv is missing required headers: {', '.join(detail_missing)}")
                    else:
                        # Process files without database operations
                        # First parse the files
                        step_df = parse_step_csv(step_file_path)
                        detail_df = parse_detail_csv(detail_file_path)
                        
                        # Display original data
                        st.subheader("Original Data")
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write("Step Data Preview (first 5 rows)")
                            st.dataframe(step_df.head())
                        
                        with col2:
                            st.write("Detail Data Preview (first 5 rows)")
                            st.dataframe(detail_df.head())
                        
                        # Process without transformation first
                        st.subheader("Basic Processing")
                        
                        # Show step counts and types
                        st.write(f"Total steps: {step_df['step_number'].nunique()}")
                        
                        # Count step types
                        step_types = step_df['step_type'].value_counts().reset_index()
                        step_types.columns = ['Step Type', 'Count']
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write("Step Types")
                            st.dataframe(step_types)
                        
                        with col2:
                            # Create a pie chart of step types
                            fig = px.pie(step_types, values='Count', names='Step Type', 
                                        title='Distribution of Step Types')
                            st.plotly_chart(fig)
                        
                        # Now apply transformations directly
                        st.subheader("Apply Transformations")
                        
                        try:
                            # Disable transformation in load_and_preprocess to avoid the error
                            # and apply transformations manually with error handling for each step
                            
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
                            
                            st.write("C-rate Statistics:")
                            st.write(c_rate_stats)
                            
                            # Add C-rate visualization
                            fig = px.line(detail_df.sort_values('timestamp').head(1000), 
                                        x='timestamp', y='c_rate', 
                                        title='C-rate over Time (first 1000 points)')
                            st.plotly_chart(fig)
                            
                            # Try to calculate SOC with error handling
                            st.write("### SOC Calculation")
                            
                            try:
                                # First select discharge steps
                                discharge_steps = step_df[step_df['step_type'] == 'discharge']
                                
                                if len(discharge_steps) == 0:
                                    st.warning("No discharge steps found in the data. SOC calculation requires discharge steps.")
                                else:
                                    st.success(f"Found {len(discharge_steps)} discharge steps.")
                                    
                                    # Check for total_capacity column
                                    if 'total_capacity' not in step_df.columns:
                                        st.error("No 'total_capacity' column found. The '總電壓(Ah)' column might be missing in the Step.csv file.")
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
                                        
                                        st.dataframe(steps_with_soc[soc_cols])
                                        
                                        # Plot SOC vs total_capacity for all steps with SOC values
                                        steps_with_soc_values = steps_with_soc.dropna(subset=['soc_end'])
                                        
                                        if not steps_with_soc_values.empty:
                                            fig = px.scatter(steps_with_soc_values, x='total_capacity', y='soc_end', 
                                                          title='SOC vs Total Capacity',
                                                          labels={'total_capacity': 'Total Capacity (Ah)', 'soc_end': 'SOC (%)'},
                                                         hover_data=['step_number', 'original_step_type'])
                                            st.plotly_chart(fig)
                                            
                                            # Plot SOC vs voltage
                                            fig = px.scatter(steps_with_soc_values, x='voltage_end', y='soc_end',
                                                          title='SOC vs Voltage',
                                                          labels={'voltage_end': 'Voltage (V)', 'soc_end': 'SOC (%)'},
                                                         hover_data=['step_number', 'original_step_type', 'total_capacity'])
                                            st.plotly_chart(fig)
                                            
                                            # Success message
                                            st.success("Successfully calculated SOC for this dataset!")
                                        else:
                                            st.warning("No steps have SOC values calculated. Check if the reference step has valid total_capacity data.")
                            
                            except Exception as e:
                                st.error(f"Error calculating SOC: {str(e)}")
                                st.warning("You can still review the C-rate calculations above.")
                                
                                # Show the step data to help diagnose the issue
                                with st.expander("Debug: View Step Data"):
                                    st.dataframe(step_df)
                        
                        except Exception as e:
                            st.error(f"Error applying transformations: {str(e)}")
                
                except Exception as e:
                    st.error(f"Error processing files: {str(e)}")
                    st.exception(e)
    else:
        st.warning("No matching step and detail file pairs found.")