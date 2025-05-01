"""
Upload UI components for the Battery ETL Dashboard

This module provides UI components for uploading and processing battery test data files.
"""
import os
import streamlit as st
import pandas as pd
from datetime import datetime
from app.utils.config import UPLOAD_FOLDER


def render_upload_page():
    """Render the upload page UI
    
    This function displays the upload UI components for Step.csv and Detail.csv files,
    processes the uploaded files, and provides feedback to the user.
    """
    st.header("Upload Battery Test Files")
    
    # Create experiment info form
    with st.form(key="experiment_info"):
        st.subheader("Experiment Information")
        
        col1, col2 = st.columns(2)
        
        with col1:
            experiment_name = st.text_input(
                "Experiment Name*",
                help="A unique name for this battery test experiment",
                value=st.session_state.get("experiment_name", ""),
            )
            
            battery_type = st.text_input(
                "Battery Type*",
                help="Type or model of the battery being tested",
                value=st.session_state.get("battery_type", ""),
            )
            
            nominal_capacity = st.number_input(
                "Nominal Capacity (Ah)*",
                min_value=0.0,
                help="Nominal capacity of the battery in Amp-hours",
                value=st.session_state.get("nominal_capacity", 0.0),
            )
        
        with col2:
            experiment_date = st.date_input(
                "Experiment Date*",
                help="Date when the experiment was conducted",
                value=st.session_state.get("experiment_date", datetime.now().date()),
            )
            
            operator = st.text_input(
                "Operator",
                help="Name of the person who conducted the experiment",
                value=st.session_state.get("operator", ""),
            )
        
        st.markdown("*Required fields")
        
        # Save experiment info to session state
        submit_experiment = st.form_submit_button("Save Experiment Info", type="primary")
    
    if submit_experiment:
        if not experiment_name or not battery_type or nominal_capacity <= 0:
            st.error("Please fill in all required fields with valid values.")
        else:
            # Save experiment info to session state
            st.session_state["experiment_name"] = experiment_name
            st.session_state["battery_type"] = battery_type
            st.session_state["nominal_capacity"] = nominal_capacity
            st.session_state["experiment_date"] = experiment_date
            st.session_state["operator"] = operator
            
            st.success("Experiment information saved. Now upload data files.")
    
    # File upload section
    st.subheader("Upload Data Files")
    
    # Create upload columns
    col1, col2 = st.columns(2)
    
    with col1:
        step_file = st.file_uploader(
            "Upload Step.csv",
            type=["csv"],
            help="CSV file containing step-level data",
            key="step_file",
        )
    
    with col2:
        detail_file = st.file_uploader(
            "Upload Detail.csv",
            type=["csv"],
            help="CSV file containing detailed measurement data",
            key="detail_file",
        )
    
    # Process files when both are uploaded
    if step_file and detail_file:
        st.info("Both files uploaded. Processing...")
        
        # Create upload directory if it doesn't exist
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        
        # Save files to upload directory
        with open(os.path.join(UPLOAD_FOLDER, step_file.name), "wb") as f:
            f.write(step_file.getbuffer())
        
        with open(os.path.join(UPLOAD_FOLDER, detail_file.name), "wb") as f:
            f.write(detail_file.getbuffer())
        
        # Read files into DataFrames
        try:
            step_df = pd.read_csv(step_file)
            detail_df = pd.read_csv(detail_file)
            
            # Display file statistics
            st.subheader("File Statistics")
            
            stats_col1, stats_col2 = st.columns(2)
            
            with stats_col1:
                st.metric("Step.csv Rows", len(step_df))
                st.metric("Step.csv Columns", len(step_df.columns))
                st.write("Step.csv Column Headers:")
                st.code(", ".join(step_df.columns))
            
            with stats_col2:
                st.metric("Detail.csv Rows", len(detail_df))
                st.metric("Detail.csv Columns", len(detail_df.columns))
                st.write("Detail.csv Column Headers:")
                st.code(", ".join(detail_df.columns))
            
            # Display data preview
            with st.expander("Step.csv Preview"):
                st.dataframe(step_df.head(5))
            
            with st.expander("Detail.csv Preview"):
                st.dataframe(detail_df.head(5))
            
            # Process button
            if st.button("Process Files", type="primary"):
                if not st.session_state.get("experiment_name"):
                    st.error("Please fill in and save the experiment information before processing files.")
                else:
                    # In a future implementation, this would call the ETL processing logic
                    st.success("Files uploaded successfully! Ready for ETL processing.")
                    st.info("ETL processing will be implemented in future tasks.")
        
        except Exception as e:
            st.error(f"Error processing files: {str(e)}")
    
    # Show help text
    st.markdown("""
    ## Expected File Format
    
    ### Step.csv
    File containing step-level data with the following required columns:
    - Step Number
    - Step Type (Charge, Discharge, Rest)
    - Start Time
    - End Time
    - Voltage (V)
    - Current (A)
    - Capacity (Ah)
    - Energy (Wh)
    - Temperature (°C)
    
    ### Detail.csv
    File containing detailed measurement data with the following required columns:
    - Step Number
    - Time
    - Voltage (V)
    - Current (A)
    - Temperature (°C)
    - Capacity (Ah)
    - Energy (Wh)
    
    For both files, the first row should contain the column headers.
    """)