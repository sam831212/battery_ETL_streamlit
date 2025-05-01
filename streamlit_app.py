"""
Battery ETL Dashboard - Main application entry point
"""
import streamlit as st
from app.utils.config import DEBUG
import os

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

# Initialize session state for navigation
if 'current_page' not in st.session_state:
    st.session_state['current_page'] = "Upload & Process"

# Function to change page
def change_page(page):
    st.session_state['current_page'] = page
    
# Sidebar logo and title
st.sidebar.title("⚡ Battery ETL")

# Navigation menu
st.sidebar.markdown('<div class="sidebar-title">Navigation</div>', unsafe_allow_html=True)

# Menu items with icons
menu_items = {
    "Upload & Process": "📤",
    "Dashboard": "📊",
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
        btn = st.button(
            page, 
            key=f"btn_{page}", 
            use_container_width=True,
            type="primary" if st.session_state.get('current_page') == page else "secondary"
        )
        if btn:
            st.session_state['current_page'] = page
            st.experimental_rerun()

# Sidebar divider
st.sidebar.markdown('<div class="sidebar-divider"></div>', unsafe_allow_html=True)

# Show debug information if in debug mode
if DEBUG:
    st.sidebar.warning("Application is running in DEBUG mode")
    st.sidebar.write(f"Current page: {st.session_state['current_page']}")

# Main content area
st.title(f"{menu_items[st.session_state['current_page']]} {st.session_state['current_page']}")

# Display different content based on the selected page
if st.session_state['current_page'] == "Upload & Process":
    st.write("""
    Here you can upload Step.csv and Detail.csv files for processing. 
    The system will guide you through the ETL process and help you prepare data for analysis.
    """)
    
    # Placeholder for file upload UI
    st.info("File upload UI will be implemented in future tasks.")
    
elif st.session_state['current_page'] == "Dashboard":
    st.write("""
    Explore and visualize processed battery test data. 
    Use the filters to select specific experiments and steps, and generate custom visualizations.
    """)
    
    # Placeholder for dashboard UI
    st.info("Dashboard UI will be implemented in future tasks.")
    
elif st.session_state['current_page'] == "Settings":
    st.write("""
    Configure application settings including database connections, 
    file format preferences, and visualization defaults.
    """)
    
    # Placeholder for settings UI
    st.info("Settings UI will be implemented in future tasks.")
