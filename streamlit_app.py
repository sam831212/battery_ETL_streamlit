"""
Battery ETL Dashboard - Main application entry point
"""
import streamlit as st
from app.utils.config import DEBUG

# Configure the page
st.set_page_config(
    page_title="Battery ETL Dashboard",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Page header
st.title("⚡ Battery ETL Dashboard")
st.write("""
Welcome to the Battery ETL Dashboard, a tool for analyzing and visualizing battery test data.
This application helps streamline the process of analyzing battery test data from cyclers.
""")

# Setup sidebar navigation
st.sidebar.title("Navigation")
page = st.sidebar.radio(
    "Select a page:",
    ["Upload & Process", "Dashboard", "Settings"]
)

# Display different content based on the selected page
if page == "Upload & Process":
    st.header("Upload & Process Data")
    st.write("Here you can upload Step.csv and Detail.csv files for processing.")
    
    # Placeholder for file upload UI
    st.info("File upload UI will be implemented in future tasks.")
    
elif page == "Dashboard":
    st.header("Data Dashboard")
    st.write("Here you can explore and visualize processed battery test data.")
    
    # Placeholder for dashboard UI
    st.info("Dashboard UI will be implemented in future tasks.")
    
elif page == "Settings":
    st.header("Settings")
    st.write("Configure application settings.")
    
    # Placeholder for settings UI
    st.info("Settings UI will be implemented in future tasks.")

# Show debug information if in debug mode
if DEBUG:
    st.sidebar.warning("Application is running in DEBUG mode")
    st.sidebar.write(f"Current page: {page}")
