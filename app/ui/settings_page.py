"""
Settings UI components for the Battery ETL Dashboard

This module provides UI components for configuring database connections,
file formats, and other application settings.
"""
import streamlit as st
from app.utils.database import test_db_connection, init_db, get_session
from app.utils.config import (
    DB_PATH, DATABASE_URL
)
from app.models.database import Cell, CellChemistry, CellFormFactor, Machine, Experiment
from sqlmodel import select, delete, func


def render_settings_page():
    """Render the settings page UI"""
    st.title("Settings")
    
    st.subheader("Database Settings")
    st.info("Using SQLite database")
    st.write(f"Database file: {DB_PATH}")
    st.write(f"Database URL: {DATABASE_URL}")
    
    # Add a button to test database connection
    if st.button("Test Database Connection", help="Verify connectivity to the configured SQLite database."):
        with st.spinner("Testing connection..."):
            try:
                from app.utils.database import test_db_connection # Local import if not already at top
                if test_db_connection():
                    st.success("Database connection successful!")
                else:
                    st.error("Database connection failed. Check logs for details.")
            except Exception as e:
                st.error(f"An error occurred while testing database connection. Details: {str(e)}")
    
def render_file_format_settings():
    """Render file format settings"""
    st.header("File Format Settings")
    
    # File format settings
    st.subheader("CSV Import Settings")
    
    col1, col2 = st.columns(2)
    
    with col1:
        delimiter = st.selectbox(
            "CSV Delimiter",
            options=[",", ";", "\t", "|"],
            index=0,
            help="Delimiter used in CSV files",
        )
        
        encoding = st.selectbox(
            "File Encoding",
            options=["utf-8", "latin-1", "iso-8859-1", "cp1252"],
            index=0,
            help="Character encoding used in input files",
        )
    
    with col2:
        header_row = st.number_input(
            "Header Row",
            min_value=0,
            max_value=10,
            value=0,
            help="Row number containing column headers (0-based)",
        )
        
        skip_rows = st.number_input(
            "Skip Rows",
            min_value=0,
            max_value=10,
            value=0,
            help="Number of rows to skip at the beginning of the file",
        )
    
    # Save button
    if st.button("Save File Format Settings", type="primary"):
        # In a real implementation, these would be saved to a database or config file
        st.session_state["delimiter"] = delimiter
        st.session_state["encoding"] = encoding
        st.session_state["header_row"] = header_row
        st.session_state["skip_rows"] = skip_rows
        st.success("File format settings saved!")


def render_ui_preferences():
    """Render UI preference settings"""
    st.header("UI Preferences")
    
    # UI preference settings
    st.subheader("Display Settings")
    
    col1, col2 = st.columns(2)
    
    with col1:
        show_debug_info = st.toggle(
            "Show Debug Information",
            value=st.session_state.get("show_debug_info", False),
            help="Display additional debugging information in the UI",
        )
        
        decimals = st.slider(
            "Decimal Places",
            min_value=1,
            max_value=6,
            value=st.session_state.get("decimals", 2),
            help="Number of decimal places to display for numeric values",
        )
    
    with col2:
        default_plot_height = st.slider(
            "Default Plot Height",
            min_value=300,
            max_value=800,
            value=st.session_state.get("default_plot_height", 400),
            help="Default height for plots in pixels",
        )
        
        default_theme = st.selectbox(
            "Default Theme",
            options=["Light", "Dark", "Auto"],
            index=0 if st.session_state.get("default_theme", "Light") == "Light" else 
                  1 if st.session_state.get("default_theme", "Light") == "Dark" else 2,
            help="Default theme for the application",
        )
    
    # Save button
    if st.button("Save UI Preferences", type="primary"):
        # In a real implementation, these would be saved to a database or config file
        st.session_state["show_debug_info"] = show_debug_info
        st.session_state["decimals"] = decimals
        st.session_state["default_plot_height"] = default_plot_height
        st.session_state["default_theme"] = default_theme
        st.success("UI preferences saved!")


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
                    "Form Factor": cell.form.value
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
        with st.spinner("Adding cell to database..."):
            with get_session() as session:
                new_cell = Cell(
                    name=cell_name if cell_name else None,
                    chemistry=CellChemistry(chemistry),
                    capacity=capacity,
                    form=CellFormFactor(form_factor)
                )
                
                session.add(new_cell)
                session.commit()
                
                st.success(f"New cell '{new_cell.name or 'N/A'}' added successfully! ID: {new_cell.id}")
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
                    format_func=lambda x: cell_options[x],
                    help="Select the specific cell entry you wish to permanently delete."
                )
            
            with col2:
                delete_button = st.button("Delete Cell", type="secondary", help="Permanently remove the selected cell from the database.")
            
            if delete_button:
                if st.session_state.get("confirm_delete_cell", False):
                    with st.spinner("Deleting cell from database..."):
                        # Perform deletion
                        cell_id_to_delete = cell_ids[selected_cell_index]
                        
                        # Check if the cell is referenced by any experiments
                        experiment_count = session.exec(select(func.count(Experiment.id)).where(Experiment.cell_id == cell_id_to_delete)).one()
                        
                        if experiment_count > 0:
                            st.error(f"Cannot delete cell (ID: {cell_id_to_delete}) because it is referenced by {experiment_count} experiment(s). Please update or remove those experiments first.")
                        else:
                            # Safe to delete
                            session.exec(delete(Cell).where(Cell.id == cell_id_to_delete))
                            session.commit()
                            st.success(f"Cell with ID {cell_id_to_delete} deleted successfully!")
                            st.session_state["confirm_delete_cell"] = False # Reset confirmation
                            st.rerun()
                else:
                    st.warning("⚠️ Are you sure you want to delete this cell? This action cannot be undone.")
                    if st.button("Confirm Delete Cell", type="primary", key="confirm_delete_cell_btn"):
                        st.session_state["confirm_delete_cell"] = True
                        st.rerun() # Rerun to process the delete on next click if confirmed
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
                    "Description": machine.description or "N/A"
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
            st.error("Machine name is required.")
        else:
            # Create new machine in database
            with st.spinner("Adding machine to database..."):
                with get_session() as session:
                    new_machine = Machine(
                        name=name,
                        model_number=model_number if model_number else None,
                        description=description if description else None
                    )
                    
                    session.add(new_machine)
                    session.commit()
                    
                    st.success(f"New machine '{new_machine.name}' added successfully! ID: {new_machine.id}")
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
                    format_func=lambda x: machine_options[x],
                    help="Select the specific machine entry you wish to permanently delete."
                )
            
            with col2:
                delete_button = st.button("Delete Machine", type="secondary", help="Permanently remove the selected machine from the database.")
            
            if delete_button:
                if st.session_state.get("confirm_delete_machine", False):
                    with st.spinner("Deleting machine from database..."):
                        # Perform deletion
                        machine_id_to_delete = machine_ids[selected_machine_index]
                        
                        # Check if the machine is referenced by any experiments
                        experiment_count = session.exec(select(func.count(Experiment.id)).where(Experiment.machine_id == machine_id_to_delete)).one()
                        
                        if experiment_count > 0:
                            st.error(f"Cannot delete machine (ID: {machine_id_to_delete}) because it is referenced by {experiment_count} experiment(s). Please update or remove those experiments first.")
                        else:
                            # Safe to delete
                            session.exec(delete(Machine).where(Machine.id == machine_id_to_delete))
                            session.commit()
                            st.success(f"Machine with ID {machine_id_to_delete} deleted successfully!")
                            st.session_state["confirm_delete_machine"] = False # Reset confirmation
                            st.rerun()
                else:
                    st.warning("⚠️ Are you sure you want to delete this machine? This action cannot be undone.")
                    if st.button("Confirm Delete Machine", type="primary", key="confirm_delete_machine_btn"):
                        st.session_state["confirm_delete_machine"] = True
                        st.rerun() # Rerun to process the delete on next click if confirmed
        else:
            st.info("No machines available to delete.")