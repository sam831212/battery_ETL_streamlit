"""
Upload UI components for the Battery ETL Dashboard

This module provides UI components for uploading and processing battery test data files.
"""
import os
import streamlit as st
import pandas as pd
from datetime import datetime
from app.utils.config import UPLOAD_FOLDER
from app.etl import (
    validate_csv_format, 
    parse_step_csv, 
    parse_detail_csv, 
    load_and_preprocess_files
)
from app.etl.extraction import STEP_REQUIRED_HEADERS, DETAIL_REQUIRED_HEADERS
from app.models.database import Experiment, Step, Measurement, ProcessedFile
from app.utils.database import get_session
from sqlmodel import select
import hashlib


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
            
            # Validate file formats
            step_file_path = os.path.join(UPLOAD_FOLDER, step_file.name)
            detail_file_path = os.path.join(UPLOAD_FOLDER, detail_file.name)
            
            # Check if the file formats are valid
            step_valid, step_missing, step_headers = validate_csv_format(
                step_file_path, 
                STEP_REQUIRED_HEADERS
            )
            
            detail_valid, detail_missing, detail_headers = validate_csv_format(
                detail_file_path, 
                DETAIL_REQUIRED_HEADERS
            )
            
            # Show validation results
            validation_col1, validation_col2 = st.columns(2)
            
            with validation_col1:
                if step_valid:
                    st.success("Step.csv format is valid")
                else:
                    st.error(f"Step.csv is missing required headers: {', '.join(step_missing)}")
            
            with validation_col2:
                if detail_valid:
                    st.success("Detail.csv format is valid")
                else:
                    st.error(f"Detail.csv is missing required headers: {', '.join(detail_missing)}")
            
            # Process button
            if st.button("Process Files", type="primary"):
                if not st.session_state.get("experiment_name"):
                    st.error("Please fill in and save the experiment information before processing files.")
                elif not step_valid or not detail_valid:
                    st.error("Please upload valid files with the required headers.")
                else:
                    # Process the files
                    with st.spinner("Processing files..."):
                        try:
                            # Calculate file hashes to check for duplicates
                            step_file_hash = hashlib.md5(step_file.getvalue()).hexdigest()
                            detail_file_hash = hashlib.md5(detail_file.getvalue()).hexdigest()
                            
                            # Check if files have already been processed
                            with get_session() as session:
                                step_file_exists = session.exec(
                                    select(ProcessedFile).where(
                                        ProcessedFile.file_hash == step_file_hash
                                    )
                                ).first()
                                
                                detail_file_exists = session.exec(
                                    select(ProcessedFile).where(
                                        ProcessedFile.file_hash == detail_file_hash
                                    )
                                ).first()
                            
                            if step_file_exists or detail_file_exists:
                                st.warning("One or both files have already been processed. Skipping...")
                            else:
                                # Use ETL functions to process files
                                step_df, detail_df, metadata = load_and_preprocess_files(
                                    step_file_path, detail_file_path
                                )
                                
                                # Create experiment record
                                experiment = Experiment(
                                    name=st.session_state["experiment_name"],
                                    description="",  # Could add a description field to the form
                                    battery_type=st.session_state["battery_type"],
                                    nominal_capacity=st.session_state["nominal_capacity"],
                                    temperature_avg=step_df["temperature_avg"].mean(),
                                    operator=st.session_state["operator"],
                                    start_date=datetime.combine(
                                        st.session_state["experiment_date"], 
                                        datetime.min.time()
                                    ),
                                    end_date=None,  # Will be updated after processing
                                    metadata=metadata["experiment"]
                                )
                                
                                # Save to database
                                with get_session() as session:
                                    # Add experiment
                                    session.add(experiment)
                                    session.commit()
                                    session.refresh(experiment)
                                    
                                    # Create step records
                                    for _, row in step_df.iterrows():
                                        step = Step(
                                            experiment_id=experiment.id,
                                            step_number=row["step_number"],
                                            step_type=row["step_type"],
                                            start_time=row["start_time"],
                                            end_time=row["end_time"],
                                            duration=row["duration"],
                                            voltage_start=row["voltage_start"],
                                            voltage_end=row["voltage_end"],
                                            current=row["current"],
                                            capacity=row["capacity"],
                                            energy=row["energy"],
                                            temperature_avg=row["temperature_avg"],
                                            temperature_min=row["temperature_avg"],  # Will be updated with min/max calculation
                                            temperature_max=row["temperature_avg"],  # Will be updated with min/max calculation
                                            c_rate=abs(row["current"]) / st.session_state["nominal_capacity"],
                                            soc_start=None,  # Will be calculated in a future task
                                            soc_end=None,   # Will be calculated in a future task
                                            ocv=None,       # Will be calculated in a future task
                                            metadata={}
                                        )
                                        session.add(step)
                                    session.commit()
                                    
                                    # Get all steps for the experiment
                                    steps = session.exec(
                                        select(Step).where(Step.experiment_id == experiment.id)
                                    ).all()
                                    
                                    # Create step ID mapping
                                    step_mapping = {step.step_number: step.id for step in steps}
                                    
                                    # Create measurement records (in batches to avoid memory issues)
                                    batch_size = 1000
                                    detail_df_len = len(detail_df)
                                    
                                    for i in range(0, detail_df_len, batch_size):
                                        batch = detail_df.iloc[i:min(i+batch_size, detail_df_len)]
                                        measurements = []
                                        
                                        for _, row in batch.iterrows():
                                            step_id = step_mapping.get(row["step_number"])
                                            if step_id is not None:
                                                measurement = Measurement(
                                                    step_id=step_id,
                                                    timestamp=row["timestamp"],
                                                    voltage=row["voltage"],
                                                    current=row["current"],
                                                    temperature=row["temperature"],
                                                    capacity=row["capacity"],
                                                    energy=row["energy"],
                                                    soc=None  # Will be calculated in a future task
                                                )
                                                measurements.append(measurement)
                                        
                                        # Add batch of measurements
                                        session.add_all(measurements)
                                        session.commit()
                                    
                                    # Record processed files
                                    session.add(ProcessedFile(
                                        experiment_id=experiment.id,
                                        filename=step_file.name,
                                        file_type="step",
                                        file_hash=step_file_hash,
                                        row_count=len(step_df),
                                        metadata=metadata["step_file"]
                                    ))
                                    
                                    session.add(ProcessedFile(
                                        experiment_id=experiment.id,
                                        filename=detail_file.name,
                                        file_type="detail",
                                        file_hash=detail_file_hash,
                                        row_count=len(detail_df),
                                        metadata=metadata["detail_file"]
                                    ))
                                    
                                    session.commit()
                                
                                # Update timestamp for end date
                                with get_session() as session:
                                    experiment = session.get(Experiment, experiment.id)
                                    if experiment:
                                        experiment.end_date = step_df["end_time"].max()
                                        session.add(experiment)
                                        session.commit()
                                
                                st.success(f"Files processed successfully! Experiment ID: {experiment.id}")
                                st.info(f"Processed {len(step_df)} steps and {len(detail_df)} measurements.")
                                
                                # Clear file uploaders
                                st.session_state["step_file"] = None
                                st.session_state["detail_file"] = None
                                st.rerun()
                        
                        except Exception as e:
                            st.error(f"Error processing files: {str(e)}")
                            st.exception(e)
        
        except Exception as e:
            st.error(f"Error processing files: {str(e)}")
    
    # Show help text
    st.markdown("""
    ## Expected File Format (ChromaLex format)
    
    ### Step.csv
    File containing step-level data with the following required columns:
    - Step Index
    - Step Type
    - Start DateTime [s]
    - End DateTime [s]
    - Start Voltage [V]
    - End Voltage [V]
    - Current [A]
    - Capacity [Ah]
    - Energy [Wh]
    - Aux T1 [oC]
    
    ### Detail.csv
    File containing detailed measurement data with the following required columns:
    - Step Index
    - DateTime [s]
    - Voltage [V]
    - Current [A]
    - Aux T1 [oC]
    - Capacity [Ah]
    - Energy [Wh]
    
    For both files, the first row should contain the column headers.
    """)