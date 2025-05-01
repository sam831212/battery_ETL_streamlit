"""
Settings UI components for the Battery ETL Dashboard

This module provides UI components for configuring database connections,
file formats, and other application settings.
"""
import streamlit as st
from app.utils.database import test_db_connection, init_db
from app.utils.config import (
    DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD, DATABASE_URL
)


def render_settings_page():
    """Render the settings page UI
    
    This function displays the settings UI components for database connections,
    file formats, and user preferences.
    """
    # Create tabs for different settings categories
    db_tab, file_tab, ui_tab = st.tabs(["Database", "File Formats", "UI Preferences"])
    
    with db_tab:
        render_database_settings()
    
    with file_tab:
        render_file_format_settings()
    
    with ui_tab:
        render_ui_preferences()


def render_database_settings():
    """Render database connection settings"""
    st.header("Database Connection")
    
    # Database connection settings form
    with st.form(key="database_settings"):
        # Display current database settings
        st.write("Current Database Configuration:")
        st.code(
            f"Host: {DB_HOST}\n"
            f"Port: {DB_PORT}\n"
            f"Database: {DB_NAME}\n"
            f"User: {DB_USER}\n"
            f"Connection URL: {DATABASE_URL.replace(DB_PASSWORD, '********') if DB_PASSWORD else DATABASE_URL}"
        )
        
        # Test connection button
        col1, col2 = st.columns([1, 3])
        with col1:
            test_connection = st.form_submit_button(
                "Test Connection", type="primary"
            )
        with col2:
            reinit_db = st.form_submit_button(
                "Re-Initialize Database", type="secondary"
            )
    
    # Handle test connection button click
    if test_connection:
        success, error_message = test_db_connection()
        if success:
            st.success("Database connection successful!")
        else:
            st.error(f"Database connection failed: {error_message}")
    
    # Handle re-initialize database button click
    if reinit_db:
        if st.session_state.get("confirm_reinit", False):
            success = init_db()
            if success:
                st.success("Database tables re-initialized successfully!")
                st.session_state["confirm_reinit"] = False
            else:
                st.error("Failed to re-initialize database tables.")
        else:
            st.warning("⚠️ This will recreate all database tables. Any existing data will remain untouched, but schema changes will be applied.")
            if st.button("Confirm Re-Initialize", type="primary"):
                st.session_state["confirm_reinit"] = True
                st.rerun()
    
    # Database information
    st.subheader("Database Information")
    st.info(
        """
        The application uses PostgreSQL database to store battery test data.
        Database connection settings are configured using environment variables.
        
        To change database settings, update the following environment variables:
        - `PGHOST` - Database host
        - `PGPORT` - Database port
        - `PGDATABASE` - Database name
        - `PGUSER` - Database user
        - `PGPASSWORD` - Database password
        
        Alternatively, you can set `DATABASE_URL` to override the individual settings.
        """
    )


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