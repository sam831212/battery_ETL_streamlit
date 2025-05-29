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
    :root {
        --primary-color: #1E88E5; /* Blue */
        --secondary-color: #f0f2f6; /* Light gray for hover */
        --background-color: #FFFFFF; /* White */
        --text-color: #262730; /* Dark gray */
        --sidebar-text-color: #4A4A4A; /* Medium gray for sidebar text */
        --sidebar-active-text-color: #FFFFFF; /* White for active sidebar text */
        --default-font: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }

    body {
        font-family: var(--default-font);
        color: var(--text-color);
        background-color: var(--background-color);
    }

    /* Sidebar specific styles */
    div[data-testid="stSidebarUserContent"] {
        padding-top: 0px; /* Reduce top padding of sidebar */
    }

    .sidebar-menu {
        padding: 12px 15px; /* Increased padding for better spacing */
        border-radius: 8px;
        margin: 5px 0; /* Adjusted margin */
        cursor: pointer;
        transition: background-color 0.2s ease-in-out, color 0.2s ease-in-out, border-left 0.2s ease-in-out;
        display: flex;
        align-items: center;
        color: var(--sidebar-text-color); /* Use CSS variable */
        border-left: 4px solid transparent; /* For active indicator */
    }
    .sidebar-menu:hover {
        background-color: var(--secondary-color); /* Use CSS variable */
        color: var(--primary-color); /* Darker text on hover */
    }
    .sidebar-menu.active {
        background-color: var(--primary-color); /* Use CSS variable */
        color: var(--sidebar-active-text-color); /* Use CSS variable */
        font-weight: 600; /* Make text bolder */
        border-left: 4px solid var(--primary-color); /* Prominent left border */
    }
    .sidebar-menu-icon {
        margin-right: 12px; /* Slightly increased margin */
        width: 24px; /* Increased icon size */
        height: 24px; /* Increased icon size */
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .sidebar-title {
        margin-top: 15px; /* Adjusted margin */
        margin-bottom: 8px; /* Adjusted margin */
        font-weight: bold;
        font-size: 1.1em; /* Slightly larger title */
        color: var(--text-color);
    }
    .sidebar-divider {
        height: 1px;
        background-color: #e0e0e0;
        margin: 10px 0; /* Adjusted margin */
    }

    /* Global styles for buttons and headers */
    .stButton>button {
        border-radius: 8px;
        padding: 10px 15px;
        font-family: var(--default-font);
        font-weight: 600;
        transition: background-color 0.2s ease-in-out, color 0.2s ease-in-out;
    }

    .stButton>button[kind="primary"] {
        background-color: var(--primary-color);
        color: white;
    }
    .stButton>button[kind="primary"]:hover {
        background-color: #1565C0; /* Darker shade of primary for hover */
    }

    .stButton>button[kind="secondary"] {
        background-color: var(--secondary-color);
        color: var(--primary-color);
        border: 1px solid var(--primary-color);
    }
    .stButton>button[kind="secondary"]:hover {
        background-color: #e0e0e0; /* Slightly darker secondary for hover */
        color: #1565C0; /* Darker primary text on hover */
    }

    h1, h2, h3 {
        font-family: var(--default-font);
        color: var(--primary-color); /* Use primary color for headers */
    }

    /* Page Title adjustments */
    div[data-testid="stVerticalBlock"] div[data-testid="stMarkdownContainer"] > h1, /* Targets st.title */
    div[data-testid="stVerticalBlock"] div[data-testid="stHeading"] > h1 /* Targets st.header, st.subheader if they render as h1 */
    {
        display: flex;
        align-items: center;
        font-size: 2em; /* Ensure title is prominent */
        font-weight: 700;
    }

    /* Styling for the icon in the title if we use markdown for it */
    div[data-testid="stVerticalBlock"] div[data-testid="stMarkdownContainer"] > h1 > span:first-child,
    div[data-testid="stVerticalBlock"] div[data-testid="stHeading"] > h1 > span:first-child
    {
        margin-right: 15px; /* Space between icon and text in title */
        font-size: 1.2em; /* Adjust icon size relative to title */
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

# Create menu items using markdown for better control over styling
for page, icon in menu_items.items():
    active_class = "active" if st.session_state['current_page'] == page else ""
    # Use a unique key for each markdown element that acts as a button
    button_key = f"menu_btn_{page.lower().replace(' ', '_')}" 
    
    st.sidebar.markdown(
        f"""
        <div class="sidebar-menu {active_class}" onclick="document.getElementById('{button_key}').click()">
            <span class="sidebar-menu-icon">{icon}</span>
            <span>{page}</span>
        </div>
        """,
        unsafe_allow_html=True
    )
    # Hidden button to trigger page change, linked by onclick above
    if st.sidebar.button(page, key=button_key, type="primary" if active_class else "secondary", use_container_width=True, help=f"Go to {page}"):
        # This button is styled by Streamlit's default, we hide it and use styled div above
        # However, we still need a button for Streamlit's event handling
        change_page(page)

# Hide the actual Streamlit buttons used for callbacks, keep only styled divs visible
st.markdown("""
<style>
    /* Attempt to hide the underlying Streamlit buttons more effectively */
    div[data-testid="stSidebarNavItems"] button[data-testid="baseButton-secondary"],
    div[data-testid="stSidebarNavItems"] button[data-testid="baseButton-primary"] {
        display: none !important; /* This might be too aggressive or not work as expected */
    }
    /* If the above doesn't work, try targeting by key if possible, or ensure the button itself is not taking space */
    /* The goal is that only the styled divs are interactive and visible */
</style>
""", unsafe_allow_html=True)


# Sidebar divider
st.sidebar.markdown('<div class="sidebar-divider"></div>', unsafe_allow_html=True)

# Show debug information if in debug mode
if DEBUG:
    st.sidebar.warning("DEBUG mode is ON. For development/testing only.")
    st.sidebar.write(f"Current page: {st.session_state['current_page']}")

# Main content area
# Reconstruct the title to allow for better styling if needed, e.g. with HTML in markdown
title_icon = menu_items[st.session_state['current_page']]
title_text = st.session_state['current_page']
st.markdown(f"<h1><span>{title_icon}</span> {title_text}</h1>", unsafe_allow_html=True)


# Display different content based on the selected page
if st.session_state['current_page'] == "Data Preview":
    from app.ui.preview_page import render_preview_page
    render_preview_page()
    
elif st.session_state['current_page'] == "Step Selection":
    # Import step selection page
    from app.ui.step_selection_page import render_step_selection_page
    
    # Check if we have data in session state
    if 'steps_df' not in st.session_state or 'details_df' not in st.session_state:
        st.warning("No data available for step selection. Please upload and process files first.")
        st.info("Go to the Data Preview page to upload and preview battery test files.")
        
        # Add a button to navigate to preview page
        if st.button("Go to Data Preview", type="primary", key="goto_preview_btn", help="Upload and process your battery test data first."):
            change_page("Data Preview")
    else:
        # Render the step selection page with data from session state
        render_step_selection_page(
            st.session_state.steps_df if 'steps_df_transformed' not in st.session_state else st.session_state.steps_df_transformed,
            st.session_state.details_df if 'details_df_transformed' not in st.session_state else st.session_state.details_df_transformed
        )

elif st.session_state['current_page'] == "Experiment Info":
    from app.ui.meta_data_page import render_meta_data_page  # Use the refactored upload module
    
    # Always render the tabbed interface for experiment info
    render_meta_data_page()
    
    # Check if steps have been selected in session state and show appropriate message
    if 'selected_steps_for_db' not in st.session_state or not st.session_state.selected_steps_for_db:
        st.warning("No steps selected for database loading. Please select steps first.")
        st.info("Go to the Step Selection page to select steps for processing.")
        
        # Add a button to navigate to step selection page
        if st.button("Go to Step Selection", type="primary", key="goto_step_selection_btn", help="Select your desired steps for analysis and database loading."):
            change_page("Step Selection")
    else:
        # Show success message
        st.success(f"You've selected {len(st.session_state.selected_steps_for_db)} steps for processing.")
    
elif st.session_state['current_page'] == "Dashboard":
    from app.ui.dashboard_page import render_dashboard_page
    render_dashboard_page()
    
elif st.session_state['current_page'] == "Settings":
    from app.ui.settings_page import render_settings_page
    render_settings_page()
