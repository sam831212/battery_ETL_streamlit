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
    load_and_preprocess_files,
    convert_numpy_types
)
from app.etl.extraction import STEP_REQUIRED_HEADERS, DETAIL_REQUIRED_HEADERS
from app.etl.validation import generate_validation_report
from app.models import Experiment, Step, Measurement, ProcessedFile, Cell, Machine
from app.models.database import CellChemistry, CellFormFactor
from app.utils.database import get_session
from app.utils.temp_files import temp_file_from_upload, calculate_file_hash_from_memory, calculate_file_hash, create_session_temp_file
from sqlmodel import select, desc, delete, func
import hashlib
from typing import Dict, List, Tuple, Optional, Any, Union, BinaryIO

# Define the path to example files
EXAMPLE_FOLDER = "./example_csv_chromaLex"


def render_entity_management(
    entity_type, 
    entity_class, 
    header_text, 
    form_fields, 
    display_fields,
    reference_check=None,
):
    """
    Generic entity management UI component
    
    Args:
        entity_type: String name of the entity type (e.g., "cell", "machine")
        entity_class: The SQLModel class for the entity
        header_text: Text to display as the header
        form_fields: List of dictionaries defining form fields for adding entities
        display_fields: List of dictionaries mapping entity attributes to display names
        reference_check: Optional function to check if entity can be deleted
    """
    st.header(header_text)
    
    # Display existing entities
    st.subheader(f"Existing {header_text}")
    
    with get_session() as session:
        entities = session.exec(select(entity_class).order_by(entity_class.id)).all()
        
        if entities:
            # Create a table to display entities
            entity_data = []
            for entity in entities:
                data_row = {"ID": entity.id}
                for field in display_fields:
                    attr_value = getattr(entity, field["attr"], None)
                    if attr_value is None and "default" in field:
                        formatted_value = field["default"]
                    elif "format" in field and callable(field["format"]):
                        formatted_value = field["format"](attr_value)
                    else:
                        formatted_value = attr_value
                    data_row[field["display"]] = formatted_value
                entity_data.append(data_row)
            
            st.dataframe(entity_data, use_container_width=True)
        else:
            st.info(f"No {entity_type}s have been added yet.")
    
    # Form to add a new entity
    st.subheader(f"Add New {header_text}")
    
    with st.form(key=f"add_{entity_type}_form"):
        # Form fields
        field_values = {}
        for field in form_fields:
            field_type = field.get("type", "text")
            
            if field_type == "text":
                field_values[field["name"]] = st.text_input(
                    field["label"],
                    max_chars=field.get("max_chars"),
                    help=field.get("help", ""),
                )
            elif field_type == "number":
                field_values[field["name"]] = st.number_input(
                    field["label"],
                    min_value=field.get("min_value"),
                    max_value=field.get("max_value"),
                    value=field.get("default_value", 0.0),
                    step=field.get("step", 1.0),
                    help=field.get("help", ""),
                )
            elif field_type == "select":
                field_values[field["name"]] = st.selectbox(
                    field["label"],
                    options=field["options"],
                    help=field.get("help", ""),
                )
            elif field_type == "textarea":
                field_values[field["name"]] = st.text_area(
                    field["label"],
                    max_chars=field.get("max_chars"),
                    help=field.get("help", ""),
                )
        
        # Submit button
        submitted = st.form_submit_button(f"Add {header_text}", type="primary")
    
    if submitted:
        # Validate required fields if specified
        required_fields = [f for f in form_fields if f.get("required", False)]
        missing_fields = [f["label"] for f in required_fields if not field_values.get(f["name"])]
        
        if missing_fields:
            st.error(f"Please fill in all required fields: {', '.join(missing_fields)}")
        else:
            # Create entity with collected values
            entity_args = {}
            for field in form_fields:
                value = field_values[field["name"]]
                
                # Apply transformations if needed
                if "transform" in field and callable(field["transform"]):
                    value = field["transform"](value)
                
                # Handle empty values
                if not value and field.get("allow_none", False):
                    value = None
                
                entity_args[field["name"]] = value
            
            # Create new entity in database
            with get_session() as session:
                new_entity = entity_class(**entity_args)
                
                session.add(new_entity)
                session.commit()
                
                st.success(f"New {entity_type} added successfully! ID: {new_entity.id}")
                st.rerun()
    
    # Delete entity section
    st.subheader(f"Delete {header_text}")
    
    with get_session() as session:
        all_entities = session.exec(select(entity_class).order_by(entity_class.id)).all()
        
        if all_entities:
            # Create display options for the select dropdown
            if hasattr(entity_class, "name") and all(getattr(e, "name", None) for e in all_entities):
                entity_options = [f"ID {e.id}: {e.name}" for e in all_entities]
            else:
                entity_options = [f"ID {e.id}" for e in all_entities]
            entity_ids = [e.id for e in all_entities]
            
            col1, col2 = st.columns([3, 1])
            
            with col1:
                selected_entity_index = st.selectbox(
                    f"Select {header_text} to Delete",
                    options=range(len(entity_options)),
                    format_func=lambda x: entity_options[x]
                )
            
            with col2:
                delete_button = st.button(f"Delete {header_text}", type="secondary")
            
            if delete_button:
                confirm_key = f"confirm_delete_{entity_type}"
                if st.session_state.get(confirm_key, False):
                    # Perform deletion
                    entity_id = entity_ids[selected_entity_index]
                    
                    # Check if the entity can be deleted (if reference check provided)
                    if reference_check:
                        can_delete, message = reference_check(session, entity_id)
                        if not can_delete:
                            st.error(message)
                            st.session_state[confirm_key] = False
                            return
                    
                    # Safe to delete
                    session.exec(delete(entity_class).where(entity_class.id == entity_id))
                    session.commit()
                    st.success(f"{header_text} with ID {entity_id} deleted successfully!")
                    st.session_state[confirm_key] = False
                    st.rerun()
                else:
                    st.warning(f"⚠️ Are you sure you want to delete this {entity_type}? This action cannot be undone.")
                    if st.button("Confirm Delete", type="primary"):
                        st.session_state[confirm_key] = True
                        st.rerun()
        else:
            st.info(f"No {entity_type}s available to delete.")


def cell_reference_check(session, cell_id):
    """Check if a cell can be safely deleted"""
    experiment_count = session.exec(select(func.count("*")).where(Experiment.cell_id == cell_id)).one()
    if experiment_count > 0:
        return False, f"Cannot delete cell (ID: {cell_id}) because it is referenced by {experiment_count} experiments."
    return True, ""


def check_file_already_processed(file_hash: str) -> bool:
    """
    Check if a file with the given hash has already been processed.
    
    Args:
        file_hash: Hash value of the file
        
    Returns:
        True if already processed, False otherwise
    """
    with get_session() as session:
        existing_file = session.exec(
            select(ProcessedFile).where(
                ProcessedFile.file_hash == file_hash
            )
        ).first()
        
        return existing_file is not None


def display_file_statistics(step_df: pd.DataFrame, detail_df: pd.DataFrame):
    """
    Display statistics for uploaded CSV files.
    
    Args:
        step_df: Step data DataFrame
        detail_df: Detail data DataFrame
    """
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


def validate_files(
    step_file_path: str, 
    detail_file_path: str
) -> Tuple[bool, bool, List[str], List[str], List[str], List[str]]:
    """
    Validate the format of step and detail files.
    
    Args:
        step_file_path: Path to the step file
        detail_file_path: Path to the detail file
        
    Returns:
        Tuple containing:
        - Whether step file is valid
        - Whether detail file is valid
        - Missing headers in step file
        - Missing headers in detail file
        - All headers in step file
        - All headers in detail file
    """
    step_valid, step_missing, step_headers = validate_csv_format(
        step_file_path, 
        STEP_REQUIRED_HEADERS
    )
    
    detail_valid, detail_missing, detail_headers = validate_csv_format(
        detail_file_path, 
        DETAIL_REQUIRED_HEADERS
    )
    
    return step_valid, detail_valid, step_missing, detail_missing, step_headers, detail_headers


def display_validation_results(
    step_valid: bool, 
    detail_valid: bool, 
    step_missing: List[str], 
    detail_missing: List[str]
):
    """
    Display validation results for the files.
    
    Args:
        step_valid: Whether step file is valid
        detail_valid: Whether detail file is valid
        step_missing: Missing headers in step file
        detail_missing: Missing headers in detail file
    """
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


def generate_validation_results(
    step_df: pd.DataFrame, 
    detail_df: pd.DataFrame
) -> Tuple[bool, Dict[str, Any], Dict[str, Any]]:
    """
    Generate validation reports for step and detail data.
    
    Args:
        step_df: Step data DataFrame
        detail_df: Detail data DataFrame
        
    Returns:
        Tuple containing:
        - Overall validation status
        - Step validation report
        - Detail validation report
    """
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
    
    return validation_status, step_validation_report, detail_validation_report


def display_validation_summary(
    validation_status: bool,
    step_validation_report: Dict[str, Any],
    detail_validation_report: Dict[str, Any]
):
    """
    Display validation summary for the data.
    
    Args:
        validation_status: Overall validation status
        step_validation_report: Step validation report
        detail_validation_report: Detail validation report
    """
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


def save_experiment_to_db(
    experiment_metadata: Dict[str, Any],
    validation_report: Dict[str, Any],
    cell_id: int,
    machine_id: int,
    battery_type: str,
    temperature_avg: float
) -> Experiment:
    """
    Create and save a new experiment record in the database.
    
    Args:
        experiment_metadata: Metadata about the experiment
        validation_report: Validation report
        cell_id: ID of the cell used in the experiment
        machine_id: ID of the machine used in the experiment
        battery_type: Type of battery used
        temperature_avg: Average temperature
        
    Returns:
        Created Experiment object
    """
    experiment = Experiment(
        name=st.session_state["experiment_name"],
        description=st.session_state.get("description", ""),
        battery_type=battery_type,
        nominal_capacity=st.session_state["nominal_capacity"],
        temperature_avg=temperature_avg,  # Convert numpy.float64 to Python float
        operator=st.session_state.get("operator", ""),
        start_date=datetime.combine(
            st.session_state["experiment_date"], 
            datetime.min.time()
        ),
        end_date=None,  # Will be updated after processing
        data_meta=experiment_metadata,
        validation_status=validation_report['valid'],
        validation_report=validation_report,
        cell_id=cell_id,
        machine_id=machine_id
    )
    
    with get_session() as session:
        session.add(experiment)
        session.commit()
        session.refresh(experiment)
        
    return experiment


def save_steps_to_db(
    experiment_id: int,
    steps_df: pd.DataFrame,
    nominal_capacity: float
) -> List[Step]:
    """
    Save step data to the database.
    
    Args:
        experiment_id: ID of the experiment
        steps_df: Step data DataFrame
        nominal_capacity: Nominal capacity of the battery
        
    Returns:
        List of created Step objects
    """
    steps = []
    
    with get_session() as session:
        for _, row in steps_df.iterrows():
            row_dict = convert_numpy_types(row.to_dict())
            
            step = Step(
                experiment_id=experiment_id,
                step_number=row_dict["step_number"],
                step_type=row_dict["step_type"],
                start_time=row_dict["start_time"],
                end_time=row_dict["end_time"],
                duration=row_dict["duration"],
                voltage_start=row_dict.get("voltage_start", 0.0),
                voltage_end=row_dict.get("voltage_end", 0.0),
                current=row_dict.get("current", 0.0),
                capacity=row_dict.get("capacity", 0.0),
                energy=row_dict.get("energy", 0.0),
                temperature_avg=row_dict.get("temperature_avg", 25.0),
                temperature_min=row_dict.get("temperature_min", 25.0),
                temperature_max=row_dict.get("temperature_max", 25.0),
                c_rate=abs(row_dict.get("current", 0.0)) / nominal_capacity,
                soc_start=row_dict.get("soc_start"),
                soc_end=row_dict.get("soc_end"),
                ocv=row_dict.get("ocv"),
                data_meta=row_dict
            )
            
            session.add(step)
            steps.append(step)
        
        session.commit()
    
    return steps


def save_measurements_to_db(
    experiment_id: int,
    details_df: pd.DataFrame,
    step_mapping: Dict[int, int],
    nominal_capacity: float,
    batch_size: int = 1000
):
    """
    Save measurement data to the database in batches.
    
    Args:
        experiment_id: ID of the experiment
        details_df: Detail data DataFrame
        step_mapping: Mapping of step numbers to step IDs
        nominal_capacity: Nominal capacity of the battery
        batch_size: Size of batches for database inserts
    """
    detail_df_len = len(details_df)
    
    with get_session() as session:
        for i in range(0, detail_df_len, batch_size):
            batch = details_df.iloc[i:min(i+batch_size, detail_df_len)]
            measurements = []
            
            for _, row in batch.iterrows():
                row_dict = convert_numpy_types(row.to_dict())
                step_id = step_mapping.get(row_dict["step_number"])
                
                if step_id is not None:
                    measurement = Measurement(
                        step_id=step_id,
                        timestamp=row_dict["timestamp"],
                        voltage=row_dict["voltage"],
                        current=row_dict["current"],
                        temperature=row_dict["temperature"],
                        capacity=row_dict["capacity"],
                        energy=row_dict["energy"],
                        soc=row_dict.get("soc")
                    )
                    measurements.append(measurement)
            
            # Add batch of measurements
            session.add_all(measurements)
            session.commit()


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
):
    """
    Save processed file records to the database.
    
    Args:
        experiment_id: ID of the experiment
        step_filename: Filename of the step file
        detail_filename: Filename of the detail file
        step_file_hash: Hash of the step file
        detail_file_hash: Hash of the detail file
        step_df_len: Number of rows in step DataFrame
        detail_df_len: Number of rows in detail DataFrame
        step_metadata: Metadata about the step file
        detail_metadata: Metadata about the detail file
    """
    with get_session() as session:
        session.add(ProcessedFile(
            experiment_id=experiment_id,
            filename=step_filename,
            file_type="step",
            file_hash=step_file_hash,
            row_count=step_df_len,
            data_meta=step_metadata
        ))
        
        session.add(ProcessedFile(
            experiment_id=experiment_id,
            filename=detail_filename,
            file_type="detail",
            file_hash=detail_file_hash,
            row_count=detail_df_len,
            data_meta=detail_metadata
        ))
        
        session.commit()


def update_experiment_end_date(experiment_id: int, end_time: datetime):
    """
    Update the end date of an experiment.
    
    Args:
        experiment_id: ID of the experiment
        end_time: End time to set
    """
    with get_session() as session:
        experiment = session.get(Experiment, experiment_id)
        if experiment:
            experiment.end_date = end_time
            session.add(experiment)
            session.commit()


def process_and_save_files(
    step_df: pd.DataFrame,
    detail_df: pd.DataFrame,
    step_file_path: Optional[str] = None,
    detail_file_path: Optional[str] = None,
    step_file_hash: Optional[str] = None,
    detail_file_hash: Optional[str] = None,
    step_filename: Optional[str] = None,
    detail_filename: Optional[str] = None,
    is_example_file: bool = False
) -> bool:
    """
    Process and save uploaded files to the database.
    
    Args:
        step_df: Step data DataFrame
        detail_df: Detail data DataFrame
        step_file_path: Path to the step file (optional for uploaded files)
        detail_file_path: Path to the detail file (optional for uploaded files)
        step_file_hash: Hash of the step file (optional for example files)
        detail_file_hash: Hash of the detail file (optional for example files)
        step_filename: Name of the step file (optional for example files)
        detail_filename: Name of the detail file (optional for example files)
        is_example_file: Whether this is an example file
        
    Returns:
        True if files were processed and saved successfully, False otherwise
    """
    try:
        # Calculate file hashes if not provided
        if not step_file_hash and step_file_path:
            step_file_hash = calculate_file_hash(step_file_path)
        if not detail_file_hash and detail_file_path:
            detail_file_hash = calculate_file_hash(detail_file_path)
            
        # Set filenames if not provided
        if not step_filename and step_file_path:
            step_filename = os.path.basename(step_file_path)
        if not detail_filename and detail_file_path:
            detail_filename = os.path.basename(detail_file_path)
        
        # Check if files have already been processed
        if check_file_already_processed(step_file_hash) or check_file_already_processed(detail_file_hash):
            st.warning("One or both files have already been processed. Skipping...")
            return False
        
        # Process files with ETL functions
        if is_example_file and step_file_path and detail_file_path:
            step_df, detail_df, metadata = load_and_preprocess_files(
                step_file_path, detail_file_path,
                nominal_capacity=st.session_state["nominal_capacity"]
            )
        else:
            # Assume DataFrames are already loaded for uploaded files
            # Just transform the data with the nominal capacity
            metadata = {
                "experiment": {"source": "uploaded_files"},
                "step_file": {"filename": step_filename},
                "detail_file": {"filename": detail_filename}
            }
        
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
        
        # Get battery type from cell
        with get_session() as cell_session:
            cell = cell_session.get(Cell, st.session_state["cell_id"])
            battery_type = cell.chemistry.value if cell else "Unknown"
        
        # Convert any numpy data types in metadata and validation report to Python native types
        experiment_metadata = convert_numpy_types(metadata["experiment"])
        validation_report_converted = convert_numpy_types(combined_validation_report)
        
        # Create experiment in database
        experiment = save_experiment_to_db(
            experiment_metadata=experiment_metadata,
            validation_report=validation_report_converted,
            cell_id=st.session_state["cell_id"],
            machine_id=st.session_state["machine_id"],
            battery_type=battery_type,
            temperature_avg=float(step_df["temperature_avg"].mean())
        )
        
        # Save steps to database and create step ID mapping
        steps = save_steps_to_db(
            experiment_id=experiment.id,
            steps_df=step_df,
            nominal_capacity=st.session_state["nominal_capacity"]
        )
        
        step_mapping = {step.step_number: step.id for step in steps}
        
        # Save measurements to database
        save_measurements_to_db(
            experiment_id=experiment.id,
            details_df=detail_df,
            step_mapping=step_mapping,
            nominal_capacity=st.session_state["nominal_capacity"]
        )
        
        # Record processed files
        step_file_meta = convert_numpy_types(metadata["step_file"])
        detail_file_meta = convert_numpy_types(metadata["detail_file"])
        
        save_processed_files_to_db(
            experiment_id=experiment.id,
            step_filename=step_filename,
            detail_filename=detail_filename,
            step_file_hash=step_file_hash,
            detail_file_hash=detail_file_hash,
            step_df_len=len(step_df),
            detail_df_len=len(detail_df),
            step_metadata=step_file_meta,
            detail_metadata=detail_file_meta
        )
        
        # Update timestamp for end date - convert numpy timestamp to Python datetime
        end_time = convert_numpy_types(step_df["end_time"].max())
        update_experiment_end_date(experiment.id, end_time)
        
        # Display validation summary
        display_validation_summary(
            validation_status,
            step_validation_report,
            detail_validation_report
        )
        
        st.success(f"Files processed successfully! Experiment ID: {experiment.id}")
        st.info(f"Processed {len(step_df)} steps and {len(detail_df)} measurements.")
        
        # Store the processed DataFrames in session state for step selection
        st.session_state['steps_df'] = step_df
        st.session_state['details_df'] = detail_df
        
        return True
    
    except Exception as e:
        st.error(f"Error processing files: {str(e)}")
        st.exception(e)
        return False


def find_example_file_pairs() -> List[Tuple[str, str, str]]:
    """
    Find matching step and detail file pairs in the example folder.
    
    Returns:
        List of tuples containing (base_name, step_file, detail_file)
    """
    example_step_files = [f for f in os.listdir(EXAMPLE_FOLDER) if f.endswith("_Step.csv")]
    example_detail_files = [f for f in os.listdir(EXAMPLE_FOLDER) if f.endswith("_Detail.csv")]
    
    example_pairs = []
    for step_file in example_step_files:
        base_name = step_file.replace("_Step.csv", "")
        detail_file = f"{base_name}_Detail.csv"
        if detail_file in example_detail_files:
            example_pairs.append((base_name, step_file, detail_file))
    
    return example_pairs


def machine_reference_check(session, machine_id):
    """Check if a machine can be safely deleted"""
    experiment_count = session.exec(select(func.count("*")).where(Experiment.machine_id == machine_id)).one()
    if experiment_count > 0:
        return False, f"Cannot delete machine (ID: {machine_id}) because it is referenced by {experiment_count} experiments."
    return True, ""


def render_machine_management():
    """Render machine management UI"""
    # Define form fields for adding a machine
    machine_form_fields = [
        {
            "name": "name",
            "label": "Name",
            "type": "text",
            "max_chars": 100,
            "help": "Name of the testing machine",
            "required": True,
        },
        {
            "name": "model_number",
            "label": "Model Number",
            "type": "text",
            "max_chars": 50,
            "help": "Model number of the testing machine (optional)",
            "allow_none": True,
        },
        {
            "name": "description",
            "label": "Description",
            "type": "textarea",
            "max_chars": 500,
            "help": "Additional information about the testing machine (optional)",
            "allow_none": True,
        },
    ]
    
    # Define display fields for machines
    machine_display_fields = [
        {"attr": "name", "display": "Name"},
        {"attr": "model_number", "display": "Model", "default": "N/A"},
        {"attr": "description", "display": "Description", "default": "N/A"},
        {"attr": "created_at", "display": "Created", "format": lambda d: d.strftime("%Y-%m-%d")},
    ]
    
    # Use the generic component
    render_entity_management(
        entity_type="machine",
        entity_class=Machine,
        header_text="Machine Management",
        form_fields=machine_form_fields,
        display_fields=machine_display_fields,
        reference_check=machine_reference_check
    )


def render_cell_management():
    """Render cell management UI"""
    # Define form fields for adding a cell
    cell_form_fields = [
        {
            "name": "name",
            "label": "Cell Name",
            "type": "text",
            "help": "Give this cell a descriptive name (optional)",
            "allow_none": True,
        },
        {
            "name": "chemistry",
            "label": "Chemistry",
            "type": "select",
            "options": [chem.value for chem in CellChemistry],
            "help": "Select the chemistry type of the cell",
            "transform": lambda v: CellChemistry(v),
            "required": True,
        },
        {
            "name": "capacity",
            "label": "Capacity (Ah)",
            "type": "number",
            "min_value": 0.1,
            "max_value": 1000.0,
            "default_value": 1.0,
            "step": 0.1,
            "help": "Nominal capacity of the cell in Ampere-hours",
            "required": True,
        },
        {
            "name": "form",
            "label": "Form Factor",
            "type": "select",
            "options": [form.value for form in CellFormFactor],
            "help": "Select the physical form factor of the cell",
            "transform": lambda v: CellFormFactor(v),
            "required": True,
        },
    ]
    
    # Define display fields for cells
    cell_display_fields = [
        {"attr": "name", "display": "Name", "default": "N/A"},
        {"attr": "chemistry", "display": "Chemistry", "format": lambda c: c.value},
        {"attr": "capacity", "display": "Capacity (Ah)"},
        {"attr": "form", "display": "Form Factor", "format": lambda f: f.value},
        {"attr": "created_at", "display": "Created", "format": lambda d: d.strftime("%Y-%m-%d")},
    ]
    
    # Use the generic component
    render_entity_management(
        entity_type="cell",
        entity_class=Cell,
        header_text="Cell Management",
        form_fields=cell_form_fields,
        display_fields=cell_display_fields,
        reference_check=cell_reference_check
    )


def render_experiment_metadata(cells, machines, has_data_from_preview):
    """Render experiment metadata form"""
    # Create experiment info form
    with st.form(key="experiment_info"):
        st.subheader("Experiment Metadata")
        
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
                st.warning("No cells available. Please add cells in the Cell Management tab.")
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
            
            # Description field
            description = st.text_area(
                "Description",
                help="Additional details about this experiment",
                value=st.session_state.get("description", ""),
                height=100
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
                st.warning("No testing machines available. Please add machines in the Machine Management tab.")
                selected_machine_id = None
        
        st.markdown("*Required fields")
        
        # Save experiment info to session state
        submit_enabled = has_data_from_preview
        submit_help = "" if submit_enabled else "Upload data files before saving experiment info"
        
        submit_experiment = st.form_submit_button(
            "Save Experiment Info", 
            type="primary",
            disabled=not submit_enabled,
            help=submit_help
        )
        
        if not submit_enabled:
            st.info("Upload data files in the Data Files section below before saving experiment info.")
    
    return submit_experiment, experiment_name, nominal_capacity, selected_cell_id, experiment_date, operator, description, selected_machine_id


def render_upload_page():
    """Render the upload page UI
    
    This function displays the upload UI components for Step.csv and Detail.csv files,
    processes the uploaded files, and provides feedback to the user.
    """
    st.header("Experiment Information")
    
    # Get available cells and machines from database
    with get_session() as session:
        cells = session.exec(select(Cell).order_by(Cell.id)).all()
        machines = session.exec(select(Machine).order_by(Machine.name)).all()
    
    # Check if we have data from previous steps
    has_data_from_preview = ('steps_df' in st.session_state and 
                            'details_df' in st.session_state)
    
    # Create tabs for different components                        
    exp_tab, cell_tab, machine_tab = st.tabs(["Experiment Metadata", "Cell Management", "Machine Management"])
    
    with exp_tab:
        # Render experiment metadata form
        submit_experiment, experiment_name, nominal_capacity, selected_cell_id, experiment_date, operator, description, selected_machine_id = render_experiment_metadata(cells, machines, has_data_from_preview)
        
        # Display message about data files if no data is available
        if not has_data_from_preview:
            st.info("Please go to the Step Selection page to process data files before saving experiment metadata.")
            if st.button("Go to Step Selection", type="primary", key="upload_goto_step_selection_btn"):
                st.session_state['current_page'] = "Step Selection"
                st.rerun()
    
    with cell_tab:
        # Render cell management UI
        render_cell_management()
    
    with machine_tab:
        # Render machine management UI
        render_machine_management()
    
    # Handle form submission for experiment metadata
    if submit_experiment:
        save_experiment_metadata(
            experiment_name, 
            nominal_capacity, 
            selected_cell_id, 
            experiment_date, 
            operator, 
            description,
            selected_machine_id,
            cells,
            machines
        )
    
    # Display data status
    st.subheader("Data Files")
    
    # Check if we have data from previous steps
    has_data_from_preview = ('steps_df' in st.session_state and 
                             'details_df' in st.session_state)
    
    # Handle data from previous steps
    if has_data_from_preview:
        render_preview_data_section()
    else:
        st.warning("No data available from previous steps. Please upload files.")
        use_different_files = True
    
    # Option to use example files
    use_example_files = st.checkbox("Use example files from example_csv_chromaLex folder", key="use_example_files")
    
    if use_example_files:
        render_example_files_section()
    else:
        # Regular file upload if not using example files
        render_file_upload_section()
    
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
    
    ### Detail.csv
    File containing detailed measurement data with the following required columns:
    - Step Index
    - DateTime [s]
    - Voltage [V]
    - Current [A]
    - Capacity [Ah]
    - Energy [Wh]
    """)


def save_experiment_metadata(
    experiment_name, 
    nominal_capacity, 
    selected_cell_id, 
    experiment_date, 
    operator, 
    description,
    selected_machine_id,
    cells,
    machines
):
    """Save experiment metadata to session state"""
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
        st.session_state["description"] = description
        st.session_state["cell_id"] = selected_cell_id
        st.session_state["machine_id"] = selected_machine_id
        
        st.success("Experiment information saved.")


def render_preview_data_section():
    """Render UI section for data from preview page"""
    st.success("Using data files from Data Preview page")
    steps_df = st.session_state['steps_df']
    details_df = st.session_state['details_df']
    
    # Display data summary
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Step Records", len(steps_df))
        st.metric("Step Types", steps_df['step_type'].nunique())
    with col2:
        st.metric("Detail Records", len(details_df))
        st.metric("Selected Steps", len(st.session_state.get('selected_steps_for_db', [])))
    
    # Add a button to save the data to the database
    if 'selected_steps_for_db' in st.session_state and st.session_state.get('selected_steps_for_db'):
        if st.button("Save Selected Steps to Database", type="primary"):
            handle_selected_steps_save()
    
    # Option to use different files
    use_different_files = st.checkbox("Use different files instead", key="use_different_files")
    
    if not use_different_files:
        st.session_state["step_file"] = None
        st.session_state["detail_file"] = None


def handle_selected_steps_save():
    """Handle saving selected steps to database"""
    if not st.session_state.get("experiment_name"):
        st.error("Please fill in and save the experiment information before processing files.")
    else:
        # Use the data from session state to save to database
        with st.spinner("Saving data to database..."):
            try:
                steps_df = st.session_state['steps_df']
                details_df = st.session_state['details_df']
                
                # Get the transformed data if available, otherwise use the raw data
                steps_df_to_use = st.session_state.get('steps_df_transformed', steps_df)
                details_df_to_use = st.session_state.get('details_df_transformed', details_df)
                
                # Use only the selected steps
                selected_step_indices = st.session_state.get('selected_steps_for_db', [])
                selected_steps_df = steps_df_to_use.loc[selected_step_indices]
                
                # Get battery type from cell
                with get_session() as cell_session:
                    cell = cell_session.get(Cell, st.session_state["cell_id"])
                    battery_type = cell.chemistry.value if cell else "Unknown"
                
                # Create experiment with selected data
                experiment = save_experiment_to_db(
                    experiment_metadata={"source": "selected_steps"},
                    validation_report={"valid": True},  # Simplified validation for selected steps
                    cell_id=st.session_state["cell_id"],
                    machine_id=st.session_state["machine_id"],
                    battery_type=battery_type,
                    temperature_avg=float(selected_steps_df["temperature_avg"].mean())
                )
                
                # Save selected steps to database
                steps = save_steps_to_db(
                    experiment_id=experiment.id,
                    steps_df=selected_steps_df,
                    nominal_capacity=st.session_state["nominal_capacity"]
                )
                
                # Create step ID mapping
                step_mapping = {step.step_number: step.id for step in steps}
                
                # Filter detail data to only include selected steps
                selected_step_numbers = selected_steps_df["step_number"].unique()
                filtered_details_df = details_df_to_use[details_df_to_use["step_number"].isin(selected_step_numbers)]
                
                # Save measurements for selected steps
                save_measurements_to_db(
                    experiment_id=experiment.id,
                    details_df=filtered_details_df,
                    step_mapping=step_mapping,
                    nominal_capacity=st.session_state["nominal_capacity"]
                )
                
                # Add file processing records with "selected_steps" as hash to indicate manual selection
                save_processed_files_to_db(
                    experiment_id=experiment.id,
                    step_filename="Selected steps from session",
                    detail_filename="Selected details from session",
                    step_file_hash="selected_steps",
                    detail_file_hash="selected_details",
                    step_df_len=len(selected_steps_df),
                    detail_df_len=len(filtered_details_df),
                    step_metadata={"source": "selected_steps"},
                    detail_metadata={"source": "selected_details"}
                )
                
                # Update end time
                end_time = convert_numpy_types(selected_steps_df["end_time"].max())
                update_experiment_end_date(experiment.id, end_time)
                
                st.success(f"Experiment '{experiment.name}' saved to database with {len(selected_steps_df)} steps.")
                
                # Clear the step selection state to avoid duplicate submissions
                st.session_state['selected_steps_for_db'] = []
                
                # Show a button to go to the dashboard
                if st.button("Go to Dashboard", type="primary"):
                    st.session_state['current_page'] = "Dashboard"
                    st.rerun()
                
            except Exception as e:
                st.error(f"Error saving data to database: {str(e)}")
                st.exception(e)


def render_example_files_section():
    """Render UI section for example files"""
    # Find example file pairs
    example_pairs = find_example_file_pairs()
    
    if not example_pairs:
        st.error("No example files found in the example_csv_chromaLex folder.")
        return
    
    st.success(f"Found {len(example_pairs)} step and detail file pairs.")
    
    # Display dropdown to select file pair
    selected_pair = st.selectbox(
        "Select example file pair:",
        options=range(len(example_pairs)),
        format_func=lambda i: example_pairs[i][0]
    )
    
    _, selected_step_file, selected_detail_file = example_pairs[selected_pair]
    
    st.info(f"Selected files: {selected_step_file} and {selected_detail_file}")
    
    # Load the selected example files
    if st.button("Load Example Files", type="primary"):
        # Set file paths in session state
        step_file_path = os.path.join(EXAMPLE_FOLDER, selected_step_file)
        detail_file_path = os.path.join(EXAMPLE_FOLDER, selected_detail_file)
        
        st.session_state["step_file_path"] = step_file_path
        st.session_state["detail_file_path"] = detail_file_path
        st.session_state["using_example_files"] = True
        
        st.success(f"Example files loaded: {selected_step_file} and {selected_detail_file}")
        st.info("Click 'Process Example Files' below to process these example files.")
        
        st.rerun()
    
    # Process example files if loaded
    if "using_example_files" in st.session_state and st.session_state["using_example_files"]:
        process_loaded_example_files()


def process_loaded_example_files():
    """Process loaded example files"""
    step_file_path = st.session_state.get("step_file_path")
    detail_file_path = st.session_state.get("detail_file_path")
    
    if not (step_file_path and detail_file_path):
        return
    
    st.info(f"Example files loaded. Ready to process.")
    
    try:
        # Read files into DataFrames
        step_df = pd.read_csv(step_file_path)
        detail_df = pd.read_csv(detail_file_path)
        
        # Display file statistics
        display_file_statistics(step_df, detail_df)
        
        # Validate files
        step_valid, detail_valid, step_missing, detail_missing, step_headers, detail_headers = validate_files(
            step_file_path, detail_file_path
        )
        
        # Show validation results
        display_validation_results(step_valid, detail_valid, step_missing, detail_missing)
        
        # Process button
        if st.button("Process Example Files", type="primary"):
            process_example_files(step_file_path, detail_file_path, step_valid, detail_valid)
    
    except Exception as e:
        st.error(f"Error reading example files: {str(e)}")
        st.exception(e)


def process_example_files(step_file_path, detail_file_path, step_valid, detail_valid):
    """Process example files and save to database"""
    if not st.session_state.get("experiment_name"):
        st.error("Please fill in and save the experiment information before processing files.")
    elif not step_valid or not detail_valid:
        st.error("Please select valid files with the required headers.")
    else:
        # Process the files
        with st.spinner("Processing example files..."):
            # Calculate file hashes for duplicate detection
            step_file_hash = calculate_file_hash(step_file_path)
            detail_file_hash = calculate_file_hash(detail_file_path)
            
            # Process and save files
            success = process_and_save_files(
                step_df=None,  # Will be loaded in the function
                detail_df=None,  # Will be loaded in the function
                step_file_path=step_file_path,
                detail_file_path=detail_file_path,
                step_file_hash=step_file_hash,
                detail_file_hash=detail_file_hash,
                step_filename=os.path.basename(step_file_path),
                detail_filename=os.path.basename(detail_file_path),
                is_example_file=True
            )
            
            if success:
                # Add a button to navigate to step selection
                if st.button("Go to Step Selection", type="primary"):
                    st.session_state['current_page'] = "Step Selection"
                    st.rerun()
                
                # Clear file session state
                st.session_state.pop("step_file_path", None)
                st.session_state.pop("detail_file_path", None)
                st.session_state["using_example_files"] = False


def render_file_upload_section():
    """Render UI section for regular file uploads"""
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
        process_uploaded_files(step_file, detail_file)


def process_uploaded_files(step_file, detail_file):
    """Process uploaded files from user"""
    st.info("Both files uploaded. Processing...")
    
    # Calculate hashes from memory for duplicate detection
    step_file_hash = calculate_file_hash_from_memory(step_file.getbuffer())
    detail_file_hash = calculate_file_hash_from_memory(detail_file.getbuffer())
    
    # Store metadata in session state
    st.session_state["step_file_name"] = step_file.name
    st.session_state["detail_file_name"] = detail_file.name
    st.session_state["step_file_hash"] = step_file_hash
    st.session_state["detail_file_hash"] = detail_file_hash
    
    try:
        # Read files into DataFrames
        step_df = pd.read_csv(step_file)
        detail_df = pd.read_csv(detail_file)
        
        # Display file statistics
        display_file_statistics(step_df, detail_df)
        
        # Create temporary files for validation
        temp_step_path = create_session_temp_file(
            step_file, 
            file_key=f"step_{step_file_hash}", 
            suffix=".csv"
        )
        
        temp_detail_path = create_session_temp_file(
            detail_file,
            file_key=f"detail_{detail_file_hash}",
            suffix=".csv"
        )
        
        # Validate files
        step_valid, detail_valid, step_missing, detail_missing, step_headers, detail_headers = validate_files(
            temp_step_path, temp_detail_path
        )
        
        # Show validation results
        display_validation_results(step_valid, detail_valid, step_missing, detail_missing)
        
        # Process button
        if st.button("Process Files", type="primary"):
            process_uploaded_csv_files(step_file, detail_file, step_df, detail_df, step_valid, detail_valid)
    
    except Exception as e:
        st.error(f"Error processing files: {str(e)}")
        st.exception(e)


def process_uploaded_csv_files(step_file, detail_file, step_df, detail_df, step_valid, detail_valid):
    """Process the uploaded CSV files and save to database"""
    if not st.session_state.get("experiment_name"):
        st.error("Please fill in and save the experiment information before processing files.")
    elif not step_valid or not detail_valid:
        st.error("Please upload valid files with the required headers.")
    else:
        # Process the files
        with st.spinner("Processing files..."):
            # Use file hashes already calculated earlier
            step_file_hash = st.session_state["step_file_hash"] 
            detail_file_hash = st.session_state["detail_file_hash"]
            
            # Create persistent temp files for processing
            temp_step_path = create_session_temp_file(
                step_file, 
                file_key=f"step_{step_file_hash}", 
                suffix=".csv"
            )
            
            temp_detail_path = create_session_temp_file(
                detail_file,
                file_key=f"detail_{detail_file_hash}",
                suffix=".csv"
            )
            
            # Process and save files
            success = process_and_save_files(
                step_df=step_df,
                detail_df=detail_df,
                step_file_path=temp_step_path,
                detail_file_path=temp_detail_path,
                step_file_hash=step_file_hash,
                detail_file_hash=detail_file_hash,
                step_filename=step_file.name,
                detail_filename=detail_file.name,
                is_example_file=False
            )
            
            if success:
                # Add a button to navigate to step selection
                if st.button("Go to Step Selection", type="primary"):
                    st.session_state['current_page'] = "Step Selection"
                    st.rerun()
                
                # Clear file uploaders
                st.session_state["step_file"] = None
                st.session_state["detail_file"] = None