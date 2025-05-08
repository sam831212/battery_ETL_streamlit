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

# Define the path to example files
EXAMPLE_FOLDER = "./example_csv_chromaLex"


def render_cell_management():
    """Render cell management UI"""
    st.header("Cell Management")
    
    # Display existing cells
    st.subheader("Existing Cells")
    
    with get_session() as session:
        cells = session.exec(select(Cell).order_by(Cell.id)).all()
        
        if cells:
            # Create a table to display cells
            cell_data = []
            for cell in cells:
                cell_data.append({
                    "ID": cell.id,
                    "Name": cell.name or "N/A",
                    "Chemistry": cell.chemistry.value,
                    "Capacity (Ah)": cell.capacity,
                    "Form Factor": cell.form.value,
                    "Created": cell.created_at.strftime("%Y-%m-%d")
                })
            
            st.dataframe(cell_data, use_container_width=True)
        else:
            st.info("No cells have been added yet.")
    
    # Form to add a new cell
    st.subheader("Add New Cell")
    
    with st.form(key="add_cell_form"):
        # Cell properties
        cell_name = st.text_input(
            "Cell Name",
            help="Give this cell a descriptive name (optional)"
        )
        
        chemistry = st.selectbox(
            "Chemistry",
            options=[chem.value for chem in CellChemistry],
            help="Select the chemistry type of the cell"
        )
        
        capacity = st.number_input(
            "Capacity (Ah)",
            min_value=0.1,
            max_value=1000.0,
            value=1.0,
            step=0.1,
            help="Nominal capacity of the cell in Ampere-hours"
        )
        
        form_factor = st.selectbox(
            "Form Factor",
            options=[form.value for form in CellFormFactor],
            help="Select the physical form factor of the cell"
        )
        
        # Submit button
        submitted = st.form_submit_button("Add Cell", type="primary")
    
    if submitted:
        # Create new cell in database
        with get_session() as session:
            new_cell = Cell(
                name=cell_name if cell_name else None,
                chemistry=CellChemistry(chemistry),
                capacity=capacity,
                form=CellFormFactor(form_factor)
            )
            
            session.add(new_cell)
            session.commit()
            
            st.success(f"New cell added successfully! ID: {new_cell.id}")
            st.rerun()
    
    # Delete cell section
    st.subheader("Delete Cell")
    
    with get_session() as session:
        all_cells = session.exec(select(Cell).order_by(Cell.id)).all()
        
        if all_cells:
            cell_options = [f"ID {cell.id}: {cell.chemistry.value}, {cell.capacity} Ah, {cell.form.value}" for cell in all_cells]
            cell_ids = [cell.id for cell in all_cells]
            
            col1, col2 = st.columns([3, 1])
            
            with col1:
                selected_cell_index = st.selectbox(
                    "Select Cell to Delete",
                    options=range(len(cell_options)),
                    format_func=lambda x: cell_options[x]
                )
            
            with col2:
                delete_button = st.button("Delete Cell", type="secondary")
            
            if delete_button:
                if st.session_state.get("confirm_delete_cell", False):
                    # Perform deletion
                    cell_id = cell_ids[selected_cell_index]
                    
                    # Check if the cell is referenced by any experiments
                    experiment_count = session.exec(select(func.count("*")).where(Experiment.cell_id == cell_id)).one()
                    
                    if experiment_count > 0:
                        st.error(f"Cannot delete cell (ID: {cell_id}) because it is referenced by {experiment_count} experiments.")
                    else:
                        # Safe to delete
                        session.exec(delete(Cell).where(Cell.id == cell_id))
                        session.commit()
                        st.success(f"Cell with ID {cell_id} deleted successfully!")
                        st.session_state["confirm_delete_cell"] = False
                        st.rerun()
                else:
                    st.warning("⚠️ Are you sure you want to delete this cell? This action cannot be undone.")
                    if st.button("Confirm Delete", type="primary"):
                        st.session_state["confirm_delete_cell"] = True
                        st.rerun()
        else:
            st.info("No cells available to delete.")


def render_machine_management():
    """Render machine management UI"""
    st.header("Machine Management")
    
    # Display existing machines
    st.subheader("Existing Machines")
    
    with get_session() as session:
        machines = session.exec(select(Machine).order_by(Machine.id)).all()
        
        if machines:
            # Create a table to display machines
            machine_data = []
            for machine in machines:
                machine_data.append({
                    "ID": machine.id,
                    "Name": machine.name,
                    "Model": machine.model_number or "N/A",
                    "Description": machine.description or "N/A",
                    "Created": machine.created_at.strftime("%Y-%m-%d")
                })
            
            st.dataframe(machine_data, use_container_width=True)
        else:
            st.info("No machines have been added yet.")
    
    # Form to add a new machine
    st.subheader("Add New Machine")
    
    with st.form(key="add_machine_form"):
        # Machine properties
        name = st.text_input(
            "Name",
            max_chars=100,
            help="Name of the testing machine"
        )
        
        model_number = st.text_input(
            "Model Number",
            max_chars=50,
            help="Model number of the testing machine (optional)"
        )
        
        description = st.text_area(
            "Description",
            max_chars=500,
            help="Additional information about the testing machine (optional)"
        )
        
        # Submit button
        submitted = st.form_submit_button("Add Machine", type="primary")
    
    if submitted:
        if not name:
            st.error("Machine name is required!")
        else:
            # Create new machine in database
            with get_session() as session:
                new_machine = Machine(
                    name=name,
                    model_number=model_number if model_number else None,
                    description=description if description else None
                )
                
                session.add(new_machine)
                session.commit()
                
                st.success(f"New machine added successfully! ID: {new_machine.id}")
                st.rerun()
    
    # Delete machine section
    st.subheader("Delete Machine")
    
    with get_session() as session:
        all_machines = session.exec(select(Machine).order_by(Machine.id)).all()
        
        if all_machines:
            machine_options = [f"ID {machine.id}: {machine.name}" + (f" ({machine.model_number})" if machine.model_number else "") for machine in all_machines]
            machine_ids = [machine.id for machine in all_machines]
            
            col1, col2 = st.columns([3, 1])
            
            with col1:
                selected_machine_index = st.selectbox(
                    "Select Machine to Delete",
                    options=range(len(machine_options)),
                    format_func=lambda x: machine_options[x]
                )
            
            with col2:
                delete_button = st.button("Delete Machine", type="secondary")
            
            if delete_button:
                if st.session_state.get("confirm_delete_machine", False):
                    # Perform deletion
                    machine_id = machine_ids[selected_machine_index]
                    
                    # Check if the machine is referenced by any experiments
                    experiment_count = session.exec(select(func.count("*")).where(Experiment.machine_id == machine_id)).one()
                    
                    if experiment_count > 0:
                        st.error(f"Cannot delete machine (ID: {machine_id}) because it is referenced by {experiment_count} experiments.")
                    else:
                        # Safe to delete
                        session.exec(delete(Machine).where(Machine.id == machine_id))
                        session.commit()
                        st.success(f"Machine with ID {machine_id} deleted successfully!")
                        st.session_state["confirm_delete_machine"] = False
                        st.rerun()
                else:
                    st.warning("⚠️ Are you sure you want to delete this machine? This action cannot be undone.")
                    if st.button("Confirm Delete", type="primary"):
                        st.session_state["confirm_delete_machine"] = True
                        st.rerun()
        else:
            st.info("No machines available to delete.")


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
    
    # Handle form submission
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
            st.session_state["description"] = description
            st.session_state["cell_id"] = selected_cell_id
            st.session_state["machine_id"] = selected_machine_id
            
            st.success("Experiment information saved.")
    

    
    # Display data status
    st.subheader("Data Files")
    
    # Check if we have data from previous steps
    has_data_from_preview = ('steps_df' in st.session_state and 
                             'details_df' in st.session_state)
    
    if has_data_from_preview:
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
                if not st.session_state.get("experiment_name"):
                    st.error("Please fill in and save the experiment information before processing files.")
                else:
                    # Use the data from session state to save to database
                    with st.spinner("Saving data to database..."):
                        try:
                            # Get the transformed data if available, otherwise use the raw data
                            steps_df_to_use = st.session_state.get('steps_df_transformed', steps_df)
                            details_df_to_use = st.session_state.get('details_df_transformed', details_df)
                            
                            # Use only the selected steps
                            selected_step_indices = st.session_state.get('selected_steps_for_db', [])
                            selected_steps_df = steps_df_to_use.loc[selected_step_indices]
                            
                            # Create experiment in database
                            with get_session() as session:
                                # Get cell to determine battery type
                                with get_session() as cell_session:
                                    cell = cell_session.get(Cell, st.session_state["cell_id"])
                                    battery_type = cell.chemistry.value if cell else "Unknown"
                                
                                # Create experiment
                                experiment = Experiment(
                                    name=st.session_state["experiment_name"],
                                    description=st.session_state.get("description", ""),
                                    battery_type=battery_type,
                                    nominal_capacity=st.session_state["nominal_capacity"],
                                    start_date=datetime.combine(st.session_state["experiment_date"], datetime.min.time()),
                                    operator=st.session_state.get("operator", ""),
                                    cell_id=st.session_state["cell_id"],
                                    machine_id=st.session_state["machine_id"],
                                )
                                
                                session.add(experiment)
                                session.commit()
                                session.refresh(experiment)
                                
                                # Process each selected step
                                for _, step_row in selected_steps_df.iterrows():
                                    # Convert numpy values to Python native types
                                    step_data = convert_numpy_types(step_row.to_dict())
                                    
                                    # Create Step object with correct field names
                                    step = Step(
                                        experiment_id=experiment.id,
                                        step_number=step_data["step_number"],
                                        step_type=step_data["step_type"],
                                        # Required fields that must be provided
                                        start_time=datetime.now(),  # Get proper timestamp or from data
                                        duration=step_data.get("duration_seconds", 0.0),
                                        voltage_start=step_data.get("voltage_start", 0.0),
                                        voltage_end=step_data.get("voltage_end", 0.0),
                                        current=step_data.get("current", 0.0),
                                        capacity=step_data.get("capacity_ah", 0.0),
                                        energy=step_data.get("energy_wh", 0.0),
                                        temperature_avg=step_data.get("temperature", 25.0),
                                        temperature_min=step_data.get("temperature_min", 25.0),
                                        temperature_max=step_data.get("temperature_max", 25.0),
                                        c_rate=step_data.get("c_rate", 0.0),
                                        # Optional fields
                                        end_time=datetime.now(),  # Get proper timestamp or from data
                                        soc_start=step_data.get("soc_start"),
                                        soc_end=step_data.get("soc_end"),
                                        ocv=step_data.get("ocv_end"),  # Store final OCV value
                                        data_meta={"original_step_type": step_data.get("original_step_type", step_data["step_type"])}
                                    )
                                    
                                    session.add(step)
                                
                                # Add file processing records
                                for file_type, file_path in [("step", "Step.csv"), ("detail", "Detail.csv")]:
                                    processed_file = ProcessedFile(
                                        experiment_id=experiment.id,
                                        file_type=file_type,
                                        filename=file_path,  # Correct field name: "filename" not "file_name"
                                        file_hash="from_session_state",  # Since we're using session state data
                                        processed_at=datetime.now(),  # Correct field name: "processed_at" not "processed_date"
                                        row_count=len(selected_steps_df) if file_type == "step" else 0  # Adding required row_count field
                                    )
                                    session.add(processed_file)
                                
                                session.commit()
                                
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
            
        # Option to use different files
        use_different_files = st.checkbox("Use different files instead", key="use_different_files")
        
        if not use_different_files:
            step_file = None
            detail_file = None
        else:
            st.info("You've chosen to upload new files instead of using the ones from Data Preview.")
    else:
        st.warning("No data available from previous steps. Please upload files.")
        use_different_files = True
    
    # Option to use example files
    use_example_files = st.checkbox("Use example files from example_csv_chromaLex folder", key="use_example_files")
    
    if use_example_files:
        # Display list of available example files
        example_step_files = [f for f in os.listdir(EXAMPLE_FOLDER) if f.endswith("_Step.csv")]
        example_detail_files = [f for f in os.listdir(EXAMPLE_FOLDER) if f.endswith("_Detail.csv")]
        
        if not example_step_files or not example_detail_files:
            st.error("No example files found in the example_csv_chromaLex folder.")
            use_example_files = False
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
                
                # Load the selected example files as file objects
                if st.button("Load Example Files", type="primary"):
                    step_file_path = os.path.join(EXAMPLE_FOLDER, selected_step_file)
                    detail_file_path = os.path.join(EXAMPLE_FOLDER, selected_detail_file)
                    
                    # Let's use a simpler approach - just use the file paths directly
                    st.session_state["step_file_path"] = os.path.join(EXAMPLE_FOLDER, selected_step_file)
                    st.session_state["detail_file_path"] = os.path.join(EXAMPLE_FOLDER, selected_detail_file)
                    st.session_state["using_example_files"] = True
                    
                    # Show a message that files are loaded
                    st.success(f"Example files loaded: {selected_step_file} and {selected_detail_file}")
                    st.info("Click 'Process Example Files' below to process these example files.")
                    
                    # Force a rerun to update the UI
                    st.rerun()
            else:
                st.warning("No matching step and detail file pairs found.")
    
    # Regular file upload if not using example files
    if not use_example_files:
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
    # If using example files, get the files from session state
    elif "step_file" in st.session_state and "detail_file" in st.session_state:
        step_file = st.session_state["step_file"]
        detail_file = st.session_state["detail_file"]
    else:
        step_file = None
        detail_file = None
    
    # Check if example files are loaded
    if "using_example_files" in st.session_state and st.session_state["using_example_files"]:
        # Get the example file paths
        step_file_path = st.session_state.get("step_file_path")
        detail_file_path = st.session_state.get("detail_file_path")
        
        if step_file_path and detail_file_path:
            st.info(f"Example files loaded. Ready to process.")
            
            # Read files into DataFrames
            try:
                step_df = pd.read_csv(step_file_path)
                detail_df = pd.read_csv(detail_file_path)
                
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
                if st.button("Process Example Files", type="primary"):
                    if not st.session_state.get("experiment_name"):
                        st.error("Please fill in and save the experiment information before processing files.")
                    elif not step_valid or not detail_valid:
                        st.error("Please select valid files with the required headers.")
                    else:
                        # Process the files
                        with st.spinner("Processing example files..."):
                            try:
                                # Calculate file hashes to check for duplicates
                                step_file_hash = calculate_file_hash(step_file_path)
                                detail_file_hash = calculate_file_hash(detail_file_path)
                                
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
                                    
                                    # Convert any numpy data types in metadata and validation report to Python native types
                                    experiment_metadata = convert_numpy_types(metadata["experiment"])
                                    validation_report_converted = convert_numpy_types(combined_validation_report)
                                    
                                    experiment = Experiment(
                                        name=st.session_state["experiment_name"],
                                        description=st.session_state.get("description", ""),
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
                                                voltage_start=row["voltage_start"] if "voltage_start" in row else None,
                                                voltage_end=row["voltage_end"] if "voltage_end" in row else None,
                                                current=row["current"] if "current" in row else None,
                                                capacity=row["capacity"] if "capacity" in row else None,
                                                energy=row["energy"] if "energy" in row else None,
                                                temperature_avg=row["temperature_avg"] if "temperature_avg" in row else None,
                                                c_rate=abs(row["current"]) / st.session_state["nominal_capacity"] if "current" in row else None,
                                                soc_start=row["soc_start"] if "soc_start" in row else None,
                                                soc_end=row["soc_end"] if "soc_end" in row else None,
                                                ir=row["ir"] if "ir" in row else None,
                                                ocv=row["ocv"] if "ocv" in row else None,
                                                efficiency=row["efficiency"] if "efficiency" in row else None,
                                                data_meta=convert_numpy_types(row.to_dict())
                                            )
                                            session.add(step)
                                        
                                        session.commit()
                                        
                                        # Create measurement batches (to avoid memory issues with large files)
                                        batch_size = 1000
                                        for i in range(0, len(detail_df), batch_size):
                                            batch = detail_df.iloc[i:i+batch_size]
                                            
                                            # Create measurement objects
                                            measurements = []
                                            for _, row in batch.iterrows():
                                                measurement = Measurement(
                                                    experiment_id=experiment.id,
                                                    step_number=row["step_number"],
                                                    timestamp=row["timestamp"],
                                                    voltage=row["voltage"],
                                                    current=row["current"],
                                                    temperature=row["temperature"],
                                                    capacity=row["capacity"],
                                                    energy=row["energy"],
                                                    soc=row["soc"] if "soc" in row else None,
                                                    c_rate=abs(row["current"]) / st.session_state["nominal_capacity"] if "current" in row else None,
                                                    data_meta=convert_numpy_types(row.to_dict())
                                                )
                                                measurements.append(measurement)
                                            
                                            # Add batch of measurements
                                            session.add_all(measurements)
                                            session.commit()
                                        
                                        # Record processed files
                                        step_file_meta = convert_numpy_types(metadata["step_file"])
                                        detail_file_meta = convert_numpy_types(metadata["detail_file"])
                                        
                                        session.add(ProcessedFile(
                                            experiment_id=experiment.id,
                                            filename=os.path.basename(step_file_path),
                                            file_type="step",
                                            file_hash=step_file_hash,
                                            row_count=int(len(step_df)),  # Ensure this is a Python int
                                            data_meta=step_file_meta
                                        ))
                                        
                                        session.add(ProcessedFile(
                                            experiment_id=experiment.id,
                                            filename=os.path.basename(detail_file_path),
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
                                    
                                    st.success(f"Example files processed successfully! Experiment ID: {experiment.id}")
                                    st.info(f"Processed {len(step_df)} steps and {len(detail_df)} measurements.")
                                    
                                    # Store the processed DataFrames in session state for step selection
                                    st.session_state['steps_df'] = step_df
                                    st.session_state['details_df'] = detail_df
                                    
                                    # Add a button to navigate to step selection
                                    if st.button("Go to Step Selection", type="primary"):
                                        st.session_state['current_page'] = "Step Selection"
                                        st.rerun()
                                    
                                    # Clear file session state
                                    st.session_state.pop("step_file_path", None)
                                    st.session_state.pop("detail_file_path", None)
                                    st.session_state["using_example_files"] = False
                                    
                                    # Add continue button if there are issues to allow user to acknowledge them
                                    if not validation_status:
                                        if st.button("Continue Anyway"):
                                            st.rerun()
                                    else:
                                        st.rerun()
                            
                            except Exception as e:
                                st.error(f"Error processing example files: {str(e)}")
                                st.exception(e)
            
            except Exception as e:
                st.error(f"Error reading example files: {str(e)}")
                st.exception(e)
    
    # Process regular uploaded files when both are uploaded
    elif step_file and detail_file:
        st.info("Both files uploaded. Processing...")
        
        # Calculate hashes from memory for duplicate detection
        step_file_hash = calculate_file_hash_from_memory(step_file.getbuffer())
        detail_file_hash = calculate_file_hash_from_memory(detail_file.getbuffer())
        
        # Store metadata in session state
        st.session_state["step_file_name"] = step_file.name
        st.session_state["detail_file_name"] = detail_file.name
        st.session_state["step_file_hash"] = step_file_hash
        st.session_state["detail_file_hash"] = detail_file_hash
        
        # Read files into DataFrames directly from memory
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
            
            # Validate file formats using temporary files
            step_valid = False
            detail_valid = False
            step_missing = []
            detail_missing = []
            step_headers = []
            detail_headers = []
            
            # Use session-persistent temporary files for validation
            step_file_hash = calculate_file_hash_from_memory(step_file.getbuffer())
            detail_file_hash = calculate_file_hash_from_memory(detail_file.getbuffer())
            
            # Store the hash values in session state for later use
            st.session_state["step_file_hash"] = step_file_hash
            st.session_state["detail_file_hash"] = detail_file_hash
            
            # Create persistent temp files
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
            
            # Check if the file formats are valid
            step_valid, step_missing, step_headers = validate_csv_format(
                temp_step_path, 
                STEP_REQUIRED_HEADERS
            )
            
            detail_valid, detail_missing, detail_headers = validate_csv_format(
                temp_detail_path, 
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
                            # Use file hashes already calculated earlier when files were uploaded
                            step_file_hash = st.session_state["step_file_hash"] 
                            detail_file_hash = st.session_state["detail_file_hash"]
                            
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
                                # Use session-persistent temporary files for processing
                                # Reuse the hash values already stored in session state
                                step_file_hash = st.session_state["step_file_hash"]
                                detail_file_hash = st.session_state["detail_file_hash"]
                                
                                # Create persistent temp files (or retrieve if already created)
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
                                
                                # Use ETL functions to process files
                                step_df, detail_df, metadata = load_and_preprocess_files(
                                    temp_step_path, temp_detail_path,
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
                                
                                # We already have convert_numpy_types imported from app.etl
                                
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
                                
                                # Store the processed DataFrames in session state for step selection
                                st.session_state['steps_df'] = step_df
                                st.session_state['details_df'] = detail_df
                                
                                # Add a button to navigate to step selection
                                if st.button("Go to Step Selection", type="primary"):
                                    st.session_state['current_page'] = "Step Selection"
                                    st.rerun()
                                
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