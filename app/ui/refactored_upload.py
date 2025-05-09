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
    st.subheader(header_text)
    
    # Create columns - one for adding new entities, one for listing existing ones
    col1, col2 = st.columns(2)
    
    # Add new entity section
    with col1:
        st.write(f"#### Add New {entity_type.capitalize()}")
        # Use a form to collect input data
        with st.form(f"add_{entity_type}_form"):
            # Create the fields based on provided form_fields
            field_values = {}
            for field in form_fields:
                field_name = field["name"]
                field_type = field.get("type", "text")
                field_label = field.get("label", field_name.replace("_", " ").capitalize())
                field_options = field.get("options", None)
                field_default = field.get("default", None)
                
                # Create different input types based on field_type
                if field_type == "text":
                    field_values[field_name] = st.text_input(field_label, value=field_default or "")
                elif field_type == "number":
                    field_values[field_name] = st.number_input(field_label, value=field_default or 0.0)
                elif field_type == "select":
                    field_values[field_name] = st.selectbox(field_label, options=field_options, index=0 if field_default is None else field_options.index(field_default))
                elif field_type == "date":
                    field_values[field_name] = st.date_input(field_label, value=field_default)
                elif field_type == "textarea":
                    field_values[field_name] = st.text_area(field_label, value=field_default or "")
            
            # Add submit button
            submit_button = st.form_submit_button(f"Add {entity_type.capitalize()}")
    
        # Process form submission
        if submit_button:
            try:
                # Create entity object with form data
                entity_data = {}
                for field in form_fields:
                    field_name = field["name"]
                    entity_data[field_name] = field_values[field_name]
                
                new_entity = entity_class(**entity_data)
                
                # Save to database
                with get_session() as session:
                    session.add(new_entity)
                    session.commit()
                    session.refresh(new_entity)
                
                st.success(f"{entity_type.capitalize()} added successfully!")
                
            except Exception as e:
                st.error(f"Error adding {entity_type}: {str(e)}")
    
    # Display existing entities
    with col2:
        st.write(f"#### Existing {entity_type.capitalize()}s")
        
        with get_session() as session:
            # Get all entities
            entities = session.query(entity_class).all()
            
            if not entities:
                st.info(f"No {entity_type}s found. Add one using the form.")
            else:
                # Display as a table
                for entity in entities:
                    with st.expander(f"{entity_type.capitalize()} #{entity.id}"):
                        # Display each field defined in display_fields
                        for field in display_fields:
                            attr_name = field["attr"]
                            display_name = field["display"]
                            # Get attribute value, handle nested attributes with dots
                            if "." in attr_name:
                                parts = attr_name.split(".")
                                value = entity
                                for part in parts:
                                    value = getattr(value, part, None)
                            else:
                                value = getattr(entity, attr_name, None)
                            
                            st.write(f"**{display_name}:** {value}")
                        
                        # Add delete button
                        if st.button(f"Delete {entity_type.capitalize()}", key=f"delete_{entity_type}_{entity.id}"):
                            # Check if entity can be deleted
                            can_delete = True
                            message = ""
                            
                            if reference_check:
                                can_delete, message = reference_check(session, entity.id)
                            
                            if can_delete:
                                try:
                                    # Delete the entity
                                    session.delete(entity)
                                    session.commit()
                                    st.success(f"{entity_type.capitalize()} deleted successfully!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error deleting {entity_type}: {str(e)}")
                            else:
                                st.error(message)


def cell_reference_check(session, cell_id):
    """Check if a cell can be safely deleted"""
    # Check if cell is referenced in any experiments
    experiment_count = session.query(Experiment).filter(
        Experiment.cell_id == cell_id
    ).count()
    
    if experiment_count > 0:
        return False, f"Cannot delete cell: It is referenced by {experiment_count} experiments."
    
    return True, "Cell can be safely deleted."


def check_file_already_processed(file_hash: str) -> bool:
    """
    Check if a file with the given hash has already been processed.
    
    Args:
        file_hash: Hash value of the file
        
    Returns:
        True if already processed, False otherwise
    """
    if not file_hash:
        return False
        
    with get_session() as session:
        # Check if any ProcessedFile with this hash exists
        existing_file = session.query(ProcessedFile).filter(
            ProcessedFile.file_hash == file_hash
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

    col1, col2 = st.columns(2)
    
    with col1:
        st.write("### Step File")
        st.write(f"**Rows:** {len(step_df):,}")
        st.write(f"**Columns:** {len(step_df.columns)}")
        
        # Get step types and show breakdown
        if "Step_Type" in step_df.columns:
            st.write("#### Step Types")
            step_types = step_df["Step_Type"].value_counts().reset_index()
            step_types.columns = ["Step Type", "Count"]
            st.dataframe(step_types, use_container_width=True)
        
        # Show time range if available
        if "Date_Time" in step_df.columns:
            try:
                min_time = pd.to_datetime(step_df["Date_Time"].min())
                max_time = pd.to_datetime(step_df["Date_Time"].max())
                st.write("#### Time Range")
                st.write(f"From: {min_time}")
                st.write(f"To: {max_time}")
                duration = max_time - min_time
                st.write(f"Duration: {duration}")
            except Exception as e:
                st.warning(f"Could not determine time range: {str(e)}")
    
    with col2:
        st.write("### Detail File")
        st.write(f"**Rows:** {len(detail_df):,}")
        st.write(f"**Columns:** {len(detail_df.columns)}")
        
        # Show basic statistics for key columns
        numeric_cols = detail_df.select_dtypes(include=['number']).columns.tolist()
        key_cols = [col for col in ['Voltage', 'Current', 'Capacity', 'Energy'] if col in numeric_cols]
        
        if key_cols:
            st.write("#### Key Measurements")
            stats_df = pd.DataFrame()
            
            for col in key_cols:
                stats_df.loc["Min", col] = detail_df[col].min()
                stats_df.loc["Max", col] = detail_df[col].max()
                stats_df.loc["Mean", col] = detail_df[col].mean()
                stats_df.loc["Std", col] = detail_df[col].std()
            
            st.dataframe(stats_df.style.format("{:.4f}"), use_container_width=True)
        
        # Show time range if available
        datetime_col = next((col for col in ['Date_Time', 'DateTime'] if col in detail_df.columns), None)
        if datetime_col:
            try:
                min_time = pd.to_datetime(detail_df[datetime_col].min())
                max_time = pd.to_datetime(detail_df[datetime_col].max())
                st.write("#### Time Range")
                st.write(f"From: {min_time}")
                st.write(f"To: {max_time}")
                duration = max_time - min_time
                st.write(f"Duration: {duration}")
                
                # Show measurement frequency
                total_seconds = duration.total_seconds()
                if total_seconds > 0:
                    frequency = len(detail_df) / total_seconds
                    st.write(f"Measurement Frequency: {frequency:.2f} samples/second")
            except Exception as e:
                st.warning(f"Could not determine time range: {str(e)}")


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
    # Required headers for each file type
    REQUIRED_STEP_HEADERS = ["Step_Index", "Step_Type", "Step_Name", "Status"]
    REQUIRED_DETAIL_HEADERS = ["Date_Time", "Voltage", "Current"]
    
    try:
        # Read the first few rows to get headers
        step_df = pd.read_csv(step_file_path, nrows=1)
        detail_df = pd.read_csv(detail_file_path, nrows=1)
        
        # Get all headers
        step_headers = step_df.columns.tolist()
        detail_headers = detail_df.columns.tolist()
        
        # Check for missing required headers
        step_missing = [h for h in REQUIRED_STEP_HEADERS if h not in step_headers]
        detail_missing = [h for h in REQUIRED_DETAIL_HEADERS if h not in detail_headers]
        
        # Determine if files are valid
        step_valid = len(step_missing) == 0
        detail_valid = len(detail_missing) == 0
        
        return step_valid, detail_valid, step_missing, detail_missing, step_headers, detail_headers
        
    except Exception as e:
        st.error(f"Error validating files: {str(e)}")
        return False, False, REQUIRED_STEP_HEADERS, REQUIRED_DETAIL_HEADERS, [], []


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
    # Create columns for the results
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Step File Validation")
        if step_valid:
            st.success("Step file is valid ✅")
        else:
            st.error("Step file is missing required headers ❌")
            if step_missing:
                st.warning(f"Missing headers: {', '.join(step_missing)}")
    
    with col2:
        st.subheader("Detail File Validation")
        if detail_valid:
            st.success("Detail file is valid ✅")
        else:
            st.error("Detail file is missing required headers ❌")
            if detail_missing:
                st.warning(f"Missing headers: {', '.join(detail_missing)}")
    
    # Overall status
    if step_valid and detail_valid:
        st.success("Both files are valid and ready for processing.")
    else:
        st.error("Please provide valid files with the required headers before processing.")


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
    step_report = {}
    detail_report = {}
    
    # Step validation
    step_report["row_count"] = len(step_df)
    step_report["column_count"] = len(step_df.columns)
    step_report["columns"] = step_df.columns.tolist()
    
    # Check for required step columns
    required_step_cols = ["Step_Index", "Step_Type", "Step_Name"]
    step_report["missing_columns"] = [col for col in required_step_cols if col not in step_df.columns]
    step_report["has_required_columns"] = len(step_report["missing_columns"]) == 0
    
    # Check step types
    if "Step_Type" in step_df.columns:
        step_report["step_types"] = step_df["Step_Type"].value_counts().to_dict()
    else:
        step_report["step_types"] = {}
    
    # Time range check
    if "Date_Time" in step_df.columns:
        try:
            step_report["start_time"] = step_df["Date_Time"].min()
            step_report["end_time"] = step_df["Date_Time"].max()
            step_report["time_range_valid"] = True
        except Exception:
            step_report["time_range_valid"] = False
    else:
        step_report["time_range_valid"] = False
    
    # Detail validation
    detail_report["row_count"] = len(detail_df)
    detail_report["column_count"] = len(detail_df.columns)
    detail_report["columns"] = detail_df.columns.tolist()
    
    # Check for required detail columns
    required_detail_cols = ["Date_Time", "Voltage", "Current"]
    detail_report["missing_columns"] = [col for col in required_detail_cols if col not in detail_df.columns]
    detail_report["has_required_columns"] = len(detail_report["missing_columns"]) == 0
    
    # Check value ranges
    for col in ["Voltage", "Current", "Capacity"]:
        if col in detail_df.columns:
            try:
                detail_report[f"{col}_min"] = float(detail_df[col].min())
                detail_report[f"{col}_max"] = float(detail_df[col].max())
                detail_report[f"{col}_mean"] = float(detail_df[col].mean())
            except Exception:
                detail_report[f"{col}_valid"] = False
        else:
            detail_report[f"{col}_valid"] = False
    
    # Time range check for detail file
    if "Date_Time" in detail_df.columns:
        try:
            detail_report["start_time"] = detail_df["Date_Time"].min()
            detail_report["end_time"] = detail_df["Date_Time"].max()
            detail_report["time_range_valid"] = True
        except Exception:
            detail_report["time_range_valid"] = False
    else:
        detail_report["time_range_valid"] = False
    
    # Overall validation status
    validation_status = (
        step_report.get("has_required_columns", False) and 
        detail_report.get("has_required_columns", False) and
        step_report.get("row_count", 0) > 0 and
        detail_report.get("row_count", 0) > 0
    )
    
    return validation_status, step_report, detail_report


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
    st.subheader("Data Validation Summary")
    
    # Overall status
    if validation_status:
        st.success("✅ Data validation passed - files are ready for processing")
    else:
        st.error("❌ Data validation failed - please check the issues below")
    
    # Create tabs for detailed reports
    step_tab, detail_tab = st.tabs(["Step Data", "Detail Data"])
    
    # Step data validation summary
    with step_tab:
        st.write("### Step Data Summary")
        
        # Display basic stats
        st.write(f"**Total rows:** {step_validation_report.get('row_count', 0)}")
        st.write(f"**Total columns:** {step_validation_report.get('column_count', 0)}")
        
        # Column validation
        if step_validation_report.get('has_required_columns', False):
            st.success("All required columns are present")
        else:
            st.error(f"Missing required columns: {', '.join(step_validation_report.get('missing_columns', []))}")
        
        # Display step types if available
        if step_validation_report.get('step_types'):
            st.write("### Step Types Breakdown")
            step_types_df = pd.DataFrame(
                list(step_validation_report.get('step_types', {}).items()),
                columns=["Step Type", "Count"]
            )
            st.dataframe(step_types_df)
            
            # Optional: Add visualization
            if not step_types_df.empty:
                st.bar_chart(step_types_df.set_index("Step Type"))
        
        # Time range info
        if step_validation_report.get('time_range_valid', False):
            st.write("### Time Range")
            st.write(f"**Start time:** {step_validation_report.get('start_time')}")
            st.write(f"**End time:** {step_validation_report.get('end_time')}")
    
    # Detail data validation summary
    with detail_tab:
        st.write("### Detail Data Summary")
        
        # Display basic stats
        st.write(f"**Total rows:** {detail_validation_report.get('row_count', 0)}")
        st.write(f"**Total columns:** {detail_validation_report.get('column_count', 0)}")
        
        # Column validation
        if detail_validation_report.get('has_required_columns', False):
            st.success("All required columns are present")
        else:
            st.error(f"Missing required columns: {', '.join(detail_validation_report.get('missing_columns', []))}")
        
        # Value ranges for key columns
        st.write("### Value Ranges")
        range_data = []
        
        for col in ["Voltage", "Current", "Capacity"]:
            if all(k in detail_validation_report for k in [f"{col}_min", f"{col}_max", f"{col}_mean"]):
                range_data.append({
                    "Column": col,
                    "Min": round(detail_validation_report.get(f"{col}_min", 0), 4),
                    "Max": round(detail_validation_report.get(f"{col}_max", 0), 4),
                    "Mean": round(detail_validation_report.get(f"{col}_mean", 0), 4)
                })
        
        if range_data:
            range_df = pd.DataFrame(range_data)
            st.dataframe(range_df)
        
        # Time range info
        if detail_validation_report.get('time_range_valid', False):
            st.write("### Time Range")
            st.write(f"**Start time:** {detail_validation_report.get('start_time')}")
            st.write(f"**End time:** {detail_validation_report.get('end_time')}")
            
    # Show overall validation decision
    if validation_status:
        st.success("Files are valid and can be processed")
    else:
        st.error("Please fix the validation issues before processing")


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
        with get_session() as cell_session:
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
        with get_session() as session:
            # Create new experiment
            experiment = save_experiment_to_db(
                experiment_metadata={
                    'name': st.session_state["experiment_name"],
                    'date': st.session_state["experiment_date"],
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
            example_pairs.append((base_name, os.path.join(EXAMPLE_FOLDER, step_file), os.path.join(EXAMPLE_FOLDER, detail_file)))
    
    return example_pairs


def machine_reference_check(session, machine_id):
    """Check if a machine can be safely deleted"""
    # Check if machine is referenced in any experiments
    experiment_count = session.query(Experiment).filter(
        Experiment.machine_id == machine_id
    ).count()
    
    if experiment_count > 0:
        return False, f"Cannot delete machine: It is referenced by {experiment_count} experiments."
    
    return True, "Machine can be safely deleted."


def render_machine_management():
    """Render machine management UI"""
    # Existing code (unchanged)
    pass


def render_cell_management():
    """Render cell management UI"""
    # Existing code (unchanged)
    pass


def render_experiment_metadata(cells, machines, has_data_from_preview):
    """Render experiment metadata form"""
    # Existing code (unchanged)
    pass


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
    # Existing code (unchanged)
    pass


def render_preview_data_section():
    """Render UI section for data from preview page"""
    # Existing code (unchanged)
    pass


def handle_selected_steps_save():
    """Handle saving selected steps to database"""
    # Existing code (unchanged)
    pass


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
    
    base_name, step_file_path, detail_file_path = example_pairs[selected_pair]
    
    st.info(f"Selected files: {os.path.basename(step_file_path)} and {os.path.basename(detail_file_path)}")
    
    # Load the selected example files
    if st.button("Load Example Files", type="primary"):
        # Store the selected pair in session state
        st.session_state["selected_example_pair"] = example_pairs[selected_pair]
        
        st.success(f"Example files loaded: {os.path.basename(step_file_path)} and {os.path.basename(detail_file_path)}")
        st.info("Click 'Process Example Files' below to process these example files.")
        
        st.rerun()
    
    # Process example files if loaded
    if "selected_example_pair" in st.session_state:
        process_loaded_example_files()


def process_loaded_example_files():
    """Process loaded example files"""
    # Replace with the new unified approach
    step_pair = st.session_state.get("selected_example_pair")
    if step_pair:
        base_name, step_file_path, detail_file_path = step_pair
        
        # Validate files
        step_valid, detail_valid, step_missing, detail_missing, _, _ = validate_files(
            step_file_path, detail_file_path
        )
        
        # Display validation results
        display_validation_results(step_valid, detail_valid, step_missing, detail_missing)
        
        # Process button
        if st.button("Process Example Files", type="primary"):
            if not st.session_state.get("experiment_name"):
                st.error("Please fill in and save the experiment information before processing files.")
            elif not step_valid or not detail_valid:
                st.error("Please select valid files with the required headers.")
            else:
                # Process the files using the unified pipeline
                with st.spinner("Processing example files..."):
                    # Get file data and metadata
                    file_data = get_file_data_and_metadata(
                        step_file_path, 
                        detail_file_path, 
                        is_example_file=True
                    )
                    
                    # Process files using the unified pipeline
                    success = handle_file_processing_pipeline(file_data)
                    
                    if success:
                        # Add a button to navigate to step selection
                        if st.button("Go to Step Selection", type="primary"):
                            st.session_state['current_page'] = "Step Selection"
                            st.rerun()
                        
                        # Clear file session state
                        st.session_state["selected_example_pair"] = None


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
    
    try:
        # Get file data and metadata using the unified helper
        file_data = get_file_data_and_metadata(
            step_file, 
            detail_file, 
            is_example_file=False
        )
        
        # Display file statistics
        display_file_statistics(file_data['step_df'], file_data['detail_df'])
        
        # Validate files
        step_valid, detail_valid, step_missing, detail_missing, _, _ = validate_files(
            file_data['step_file_path'], 
            file_data['detail_file_path']
        )
        
        # Show validation results
        display_validation_results(step_valid, detail_valid, step_missing, detail_missing)
        
        # Process button
        if st.button("Process Files", type="primary"):
            if not st.session_state.get("experiment_name"):
                st.error("Please fill in and save the experiment information before processing files.")
            elif not step_valid or not detail_valid:
                st.error("Please upload valid files with the required headers.")
            else:
                # Process the files using the unified pipeline
                with st.spinner("Processing files..."):
                    success = handle_file_processing_pipeline(file_data)
                    
                    if success:
                        # Add a button to navigate to step selection
                        if st.button("Go to Step Selection", type="primary"):
                            st.session_state['current_page'] = "Step Selection"
                            st.rerun()
                        
                        # Clear file uploaders
                        st.session_state["step_file"] = None
                        st.session_state["detail_file"] = None
    
    except Exception as e:
        st.error(f"Error processing files: {str(e)}")
        st.exception(e)


def render_upload_page():
    """Render the upload page UI
    
    This function displays the upload UI components for Step.csv and Detail.csv files,
    processes the uploaded files, and provides feedback to the user.
    """
    # Existing code (unchanged)
    pass