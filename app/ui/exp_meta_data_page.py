"""
Upload UI components for the Battery ETL Dashboard

This module provides UI components for uploading and processing battery test data files.
"""
import streamlit as st
from app.ui.components.meta_data_page.entity_management_ui import render_cell_management
from app.ui.components.meta_data_page.entity_management_ui import render_machine_management
from app.ui.components.meta_data_page.experiment_info_ui import render_experiment_metadata
from app.ui.components.meta_data_page.selected_data_processing_ui import render_preview_data_section
from app.utils.config import UPLOAD_FOLDER
from app.etl import (
    validate_csv_format, 
    parse_step_csv, 
    parse_detail_csv
)
from app.etl.extraction import STEP_REQUIRED_HEADERS, DETAIL_REQUIRED_HEADERS
from app.etl.validation import generate_validation_report
from app.models import Cell, Machine
from app.utils.database import get_session as get_db_session
from app.utils.temp_files import temp_file_from_upload

# Define the path to example files
EXAMPLE_FOLDER = "./example_csv_chromaLex"


def render_upload_page():
    """Render the upload page UI
    
    This function displays the experiment information components.
    """
    # Set up page
    st.title("Battery ETL Dashboard - Experiment Information")
    
    # Get database entities for references
    # Try to get cells and machines with connection retry logic
    try:
        with get_db_session() as session:
            cells = session.query(Cell).order_by(Cell.name).all()
            machines = session.query(Machine).order_by(Machine.name).all()
    except Exception as e:
        # If first attempt fails, try resetting the connection pool
        st.warning("Database connection issue detected. Attempting to reconnect...")
        try:
            with get_db_session() as session:
                cells = session.query(Cell).order_by(Cell.name).all()
                machines = session.query(Machine).order_by(Machine.name).all()
        except Exception as retry_error:
            st.error(f"Database connection error: {str(retry_error)}")
            st.info("Please try refreshing the page. If the issue persists, contact support.")
            cells = []
            machines = []
    
    # Create tabs for different sections
    tab1, tab2, tab3 = st.tabs([
        "Cell Management",
        "Machine Management",
        "Experiment Information"
    ])
    
    # Tab 1: Cell Management
    with tab1:
        render_cell_management()
    
    # Tab 2: Machine Management
    with tab2:
        render_machine_management()
    
    # Tab 3: Experiment Information
    with tab3:
        # Check if data is available from previous step
        has_data_from_preview = "selected_steps" in st.session_state
        
        # Render experiment metadata form
        render_experiment_metadata(cells, machines, has_data_from_preview)
        
        # Render section for data from preview
        if has_data_from_preview:
            st.markdown("---")
            render_preview_data_section()