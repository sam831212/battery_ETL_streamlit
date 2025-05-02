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
from app.etl.validation import generate_validation_report
from app.models.database import Experiment, Step, Measurement, ProcessedFile, Cell, Machine
from app.utils.database import get_session
from sqlmodel import select, desc
import hashlib


def render_upload_page():
    """Render the upload page UI
    
    This function displays the upload UI components for Step.csv and Detail.csv files,
    processes the uploaded files, and provides feedback to the user.
    """
    st.header("Upload Battery Test Files")
    
    # Get available cells and machines from database
    with get_session() as session:
        cells = session.exec(select(Cell).order_by(Cell.id)).all()
        machines = session.exec(select(Machine).order_by(Machine.name)).all()
    
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
            
            nominal_capacity = st.number_input(
                "Nominal Capacity (Ah)*",
                min_value=0.0,
                help="Nominal capacity of the battery in Amp-hours",
                value=st.session_state.get("nominal_capacity", 0.0),
            )
            
            # Cell selection
            if cells:
                cell_options = []
                for cell in cells:
                    cell_name_display = f"{cell.name}: " if cell.name else ""
                    cell_options.append(f"{cell_name_display}{cell.chemistry.value} - {cell.capacity}Ah ({cell.form.value})")
                cell_ids = [cell.id for cell in cells]
                selected_cell_index = st.selectbox(
                    "Battery Cell*",
                    options=range(len(cell_options)),
                    format_func=lambda x: cell_options[x] if x < len(cell_options) else "Select a cell",
                    index=0,
                    help="Select the battery cell used in this experiment"
                )
                selected_cell_id = cell_ids[selected_cell_index] if selected_cell_index < len(cell_ids) else None
            else:
                st.warning("No cells available. Please add cells in the Settings page.")
                selected_cell_id = None
        
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
            
            # Machine selection
            if machines:
                machine_options = [f"{machine.name} ({machine.model_number or 'N/A'})" for machine in machines]
                machine_ids = [machine.id for machine in machines]
                selected_machine_index = st.selectbox(
                    "Testing Machine*",
                    options=range(len(machine_options)),
                    format_func=lambda x: machine_options[x] if x < len(machine_options) else "Select a machine",
                    index=0,
                    help="Select the testing machine used for this experiment"
                )
                selected_machine_id = machine_ids[selected_machine_index] if selected_machine_index < len(machine_ids) else None
            else:
                st.warning("No testing machines available. Please add machines in the Settings page.")
                selected_machine_id = None
        
        st.markdown("*Required fields")
        
        # Save experiment info to session state
        submit_experiment = st.form_submit_button("Save Experiment Info", type="primary")
    
    if submit_experiment:
        if not experiment_name or nominal_capacity <= 0:
            st.error("Please fill in all required fields with valid values.")
        elif cells and selected_cell_id is None:
            st.error("Please select a battery cell for this experiment.")
        elif machines and selected_machine_id is None:
            st.error("Please select a testing machine for this experiment.")
        else:
            # Save experiment info to session state
            st.session_state["experiment_name"] = experiment_name
            st.session_state["nominal_capacity"] = nominal_capacity
            st.session_state["experiment_date"] = experiment_date
            st.session_state["operator"] = operator
            st.session_state["cell_id"] = selected_cell_id
            st.session_state["machine_id"] = selected_machine_id
            
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
                                    step_file_path, detail_file_path,
                                    nominal_capacity=st.session_state["nominal_capacity"]
                                )
                                
                                # Generate validation reports
                                step_validation_report = generate_validation_report(
                                    step_df, 
                                    step_type=None  # Apply validation for all step types
                                )
                                
                                detail_validation_report = generate_validation_report(
                                    detail_df, 
                                    step_type=None  # Apply validation for all step types
                                )
                                
                                # Combine validation results
                                validation_status = step_validation_report['valid'] and detail_validation_report['valid']
                                combined_validation_report = {
                                    'valid': validation_status,
                                    'step_validation': step_validation_report,
                                    'detail_validation': detail_validation_report,
                                    'timestamp': datetime.utcnow().isoformat()
                                }
                                
                                # Create experiment record
                                # Get battery type from cell
                                with get_session() as cell_session:
                                    cell = cell_session.get(Cell, st.session_state["cell_id"])
                                    battery_type = cell.chemistry.value if cell else "Unknown"
                                
                                # Import the convert_numpy_types function to ensure all numpy types are converted to Python native types
                                from app.etl.extraction import convert_numpy_types
                                
                                # Convert any numpy data types in metadata and validation report to Python native types
                                experiment_metadata = convert_numpy_types(metadata["experiment"])
                                validation_report_converted = convert_numpy_types(combined_validation_report)
                                
                                experiment = Experiment(
                                    name=st.session_state["experiment_name"],
                                    description="",  # Could add a description field to the form
                                    battery_type=battery_type,
                                    nominal_capacity=st.session_state["nominal_capacity"],
                                    temperature_avg=float(step_df["temperature_avg"].mean()),  # Convert numpy.float64 to Python float
                                    operator=st.session_state["operator"],
                                    start_date=datetime.combine(
                                        st.session_state["experiment_date"], 
                                        datetime.min.time()
                                    ),
                                    end_date=None,  # Will be updated after processing
                                    data_meta=experiment_metadata,
                                    validation_status=validation_status,
                                    validation_report=validation_report_converted,
                                    cell_id=st.session_state.get("cell_id"),
                                    machine_id=st.session_state.get("machine_id")
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
                                            data_meta={}
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
                                    
                                    # Record processed files - convert metadata to ensure no numpy types
                                    step_file_meta = convert_numpy_types(metadata["step_file"])
                                    detail_file_meta = convert_numpy_types(metadata["detail_file"])
                                    
                                    session.add(ProcessedFile(
                                        experiment_id=experiment.id,
                                        filename=step_file.name,
                                        file_type="step",
                                        file_hash=step_file_hash,
                                        row_count=int(len(step_df)),  # Ensure this is a Python int
                                        data_meta=step_file_meta
                                    ))
                                    
                                    session.add(ProcessedFile(
                                        experiment_id=experiment.id,
                                        filename=detail_file.name,
                                        file_type="detail",
                                        file_hash=detail_file_hash,
                                        row_count=int(len(detail_df)),  # Ensure this is a Python int
                                        data_meta=detail_file_meta
                                    ))
                                    
                                    session.commit()
                                
                                # Update timestamp for end date - convert numpy timestamp to Python datetime
                                with get_session() as session:
                                    experiment = session.get(Experiment, experiment.id)
                                    if experiment:
                                        # Convert numpy timestamp to Python datetime
                                        end_time = convert_numpy_types(step_df["end_time"].max())
                                        experiment.end_date = end_time
                                        session.add(experiment)
                                        session.commit()
                                
                                # Display validation summary
                                st.subheader("Validation Results")
                                
                                if validation_status:
                                    st.success("All validation checks passed!")
                                else:
                                    st.warning("Validation found potential issues with the data.")
                                
                                # Step validation summary
                                with st.expander("Step Data Validation"):
                                    step_summary = step_validation_report['summary']
                                    
                                    col1, col2, col3 = st.columns(3)
                                    with col1:
                                        st.metric("Total Issues", step_summary['total_issues'])
                                    with col2:
                                        st.metric("Critical Issues", step_summary['critical_issues'])
                                    with col3:
                                        st.metric("Warning Issues", step_summary['warning_issues'])
                                    
                                    # Display critical issues
                                    if step_summary['critical_issues'] > 0:
                                        st.markdown("##### Critical Issues:")
                                        for issue in step_validation_report['issues_by_severity']['critical']:
                                            st.error(f"**{issue['validation']}**: {issue['issue']}")
                                    
                                    # Display warnings
                                    if step_summary['warning_issues'] > 0:
                                        st.markdown("##### Warnings:")
                                        for issue in step_validation_report['issues_by_severity']['warning']:
                                            st.warning(f"**{issue['validation']}**: {issue['issue']}")
                                
                                # Detail validation summary
                                with st.expander("Measurement Data Validation"):
                                    detail_summary = detail_validation_report['summary']
                                    
                                    col1, col2, col3 = st.columns(3)
                                    with col1:
                                        st.metric("Total Issues", detail_summary['total_issues'])
                                    with col2:
                                        st.metric("Critical Issues", detail_summary['critical_issues'])
                                    with col3:
                                        st.metric("Warning Issues", detail_summary['warning_issues'])
                                    
                                    # Display critical issues
                                    if detail_summary['critical_issues'] > 0:
                                        st.markdown("##### Critical Issues:")
                                        for issue in detail_validation_report['issues_by_severity']['critical']:
                                            st.error(f"**{issue['validation']}**: {issue['issue']}")
                                    
                                    # Display warnings
                                    if detail_summary['warning_issues'] > 0:
                                        st.markdown("##### Warnings:")
                                        for issue in detail_validation_report['issues_by_severity']['warning']:
                                            st.warning(f"**{issue['validation']}**: {issue['issue']}")
                                
                                st.success(f"Files processed successfully! Experiment ID: {experiment.id}")
                                st.info(f"Processed {len(step_df)} steps and {len(detail_df)} measurements.")
                                
                                # Clear file uploaders
                                st.session_state["step_file"] = None
                                st.session_state["detail_file"] = None
                                
                                # Add continue button if there are issues to allow user to acknowledge them
                                if not validation_status:
                                    if st.button("Continue Anyway", type="primary"):
                                        st.rerun()
                                else:
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