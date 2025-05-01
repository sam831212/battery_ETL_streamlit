"""
Battery ETL Dashboard - Main application entry point
"""
import streamlit as st
from app.utils.config import DEBUG
from app.utils.database import init_db
import os

# Initialize the database
db_init_success = init_db()

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
    st.rerun()
    
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
if st.session_state['current_page'] == "Upload & Process":
    from app.ui.upload import render_upload_page
    render_upload_page()
    
elif st.session_state['current_page'] == "Dashboard":
    from app.ui.dashboard import render_dashboard_page
    render_dashboard_page()
    
elif st.session_state['current_page'] == "Settings":
    from app.ui.settings import render_settings_page
    render_settings_page()
