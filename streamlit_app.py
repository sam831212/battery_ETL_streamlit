"""
Battery ETL Dashboard - Main application entry point
"""
import streamlit as st
from app.utils.config import DEBUG
from app.utils.database import init_db
import os

# Initialize the database
# Use recreate_tables=True to rebuild the database schema
db_init_success = init_db(recreate_tables=True)

# Configure the page
st.set_page_config(
    page_title="Battery ETL Dashboard",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for modern sidebar menu
st.markdown("""
<style>
    .sidebar-menu {
        padding: 10px;
        border-radius: 8px;
        margin-bottom: 10px;
        cursor: pointer;
        transition: background-color 0.3s;
        display: flex;
        align-items: center;
        color: #262730;
    }
    .sidebar-menu:hover {
        background-color: #f0f2f6;
    }
    .sidebar-menu.active {
        background-color: #1E88E5;
        color: white;
    }
    .sidebar-menu-icon {
        margin-right: 10px;
        width: 20px;
        text-align: center;
    }
    .sidebar-title {
        margin-top: 20px;
        margin-bottom: 10px;
        font-weight: bold;
    }
    .sidebar-divider {
        height: 1px;
        background-color: #e0e0e0;
        margin: 15px 0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state variables
if 'current_page' not in st.session_state:
    st.session_state['current_page'] = "Data Preview"

# Initialize temp files registry if it doesn't exist
if 'temp_files_registry' not in st.session_state:
    st.session_state.temp_files_registry = {}

# Function to change page
def change_page(page):
    st.session_state['current_page'] = page
    st.rerun()
    
# Sidebar logo and title
st.sidebar.title("⚡ Battery ETL")

# Navigation menu
st.sidebar.markdown('<div class="sidebar-title">Navigation</div>', unsafe_allow_html=True)

# Menu items with icons
menu_items = {
    "Data Preview": "📊",
    "Step Selection": "✅",
    "Experiment Info": "📝",
    "Dashboard": "📈",
    "Settings": "⚙️"
}

# Create buttons styled as menu items
for page, icon in menu_items.items():
    active_class = "active" if st.session_state['current_page'] == page else ""
    
    # Use columns to create button with icon
    col1, col2 = st.sidebar.columns([1, 5])
    
    with col1:
        st.write(f"### {icon}")
    
    with col2:
        if st.button(
            page, 
            key=f"btn_{page}", 
            use_container_width=True,
            type="primary" if st.session_state['current_page'] == page else "secondary"
        ):
            change_page(page)

# Sidebar divider
st.sidebar.markdown('<div class="sidebar-divider"></div>', unsafe_allow_html=True)

# Show debug information if in debug mode
if DEBUG:
    st.sidebar.warning("Application is running in DEBUG mode")
    st.sidebar.write(f"Current page: {st.session_state['current_page']}")

# Main content area
st.title(f"{menu_items[st.session_state['current_page']]} {st.session_state['current_page']}")

# Display different content based on the selected page
if st.session_state['current_page'] == "Data Preview":
    from app.ui.preview import render_preview_page
    render_preview_page()
    
elif st.session_state['current_page'] == "Step Selection":
    # Import step selection page
    from app.ui.step_selection import render_step_selection_page
    
    # Check if we have data in session state
    if 'steps_df' not in st.session_state or 'details_df' not in st.session_state:
        st.warning("No data available for step selection. Please upload and process files first.")
        st.info("Go to the Data Preview page to upload and preview battery test files.")
        
        # Add a button to navigate to preview page
        if st.button("Go to Data Preview", type="primary", key="goto_preview_btn"):
            change_page("Data Preview")
    else:
        # Render the step selection page with data from session state
        render_step_selection_page(
            st.session_state.steps_df if 'steps_df_transformed' not in st.session_state else st.session_state.steps_df_transformed,
            st.session_state.details_df if 'details_df_transformed' not in st.session_state else st.session_state.details_df_transformed
        )

elif st.session_state['current_page'] == "Experiment Info":
    from app.ui.refactored_upload import render_upload_page  # Use the refactored upload module
    
    # Always render the tabbed interface for experiment info
    render_upload_page()
    
    # Check if steps have been selected in session state and show appropriate message
    if 'selected_steps_for_db' not in st.session_state or not st.session_state.selected_steps_for_db:
        st.warning("No steps selected for database loading. Please select steps first.")
        st.info("Go to the Step Selection page to select steps for processing.")
        
        # Add a button to navigate to step selection page
        if st.button("Go to Step Selection", type="primary", key="goto_step_selection_btn"):
            change_page("Step Selection")
    else:
        # Show success message
        st.success(f"You've selected {len(st.session_state.selected_steps_for_db)} steps for processing.")
    
elif st.session_state['current_page'] == "Dashboard":
    from app.ui.dashboard import render_dashboard_page
    render_dashboard_page()
    
elif st.session_state['current_page'] == "Settings":
    from app.ui.settings import render_settings_page
    render_settings_page()
