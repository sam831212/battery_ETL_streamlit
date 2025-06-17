"""
Dashboard page for the Battery ETL Dashboard
Implements hierarchical data visualization across Project → Experiment → Step levels
with interactive tables, filtering, and plotting capabilities.
"""

import streamlit as st
import pandas as pd
from typing import Optional
from sqlmodel import Session
from sqlalchemy import Column

from app.services.DB_fetch_service import get_projects_data
from app.services.DB_fetch_service import get_experiments_data
from app.services.DB_fetch_service import get_steps_data
from app.services.DB_fetch_service import get_cells_data  # 新增：取得 cell table 資料
from app.ui.components.dashboard_page.dashboard_components import create_interactive_table
from app.ui.components.dashboard_page.dashboard_components import render_step_plot
from app.ui.components.dashboard_page.dashboard_components import render_detail_plot
from app.ui.components.dashboard_page.dashboard_components import render_filtering_controls
from app.ui.components.dashboard_page.edit_components import render_edit_button_and_modal
from app.utils.dashboard_utils import apply_filters
from app.utils.dashboard_utils import extract_selected_ids
from app.utils.dashboard_constants import PROJECT_DF_COLUMNS, EXPERIMENT_DF_COLUMNS, STEP_DF_COLUMNS, MEASUREMENT_DF_COLUMNS, CELL_DF_COLUMNS  # 新增 CELL_DF_COLUMNS

try:
    from st_aggrid import AgGrid
    AGGRID_AVAILABLE = True
except ImportError:
    AGGRID_AVAILABLE = False

def init_session_state():
    """Initialize session state variables for the dashboard"""
    if "selected_projects" not in st.session_state:
        st.session_state.selected_projects = []
    if "selected_experiments" not in st.session_state:
        st.session_state.selected_experiments = []
    if "selected_steps" not in st.session_state:
        st.session_state.selected_steps = []
    if "selected_cells" not in st.session_state:
        st.session_state.selected_cells = []
    if "dashboard_filters" not in st.session_state:
        st.session_state.dashboard_filters = {}

def render_dashboard_page():
    """Main function to render the dashboard page"""
    st.title("Battery ETL Dashboard")
    st.markdown("Explore and visualize battery test data across projects, experiments, and steps.")
    
    # Initialize session state
    init_session_state()
    
    # Show AgGrid availability status
    if not AGGRID_AVAILABLE:
        st.warning("st_aggrid not available. Using fallback tables. For full functionality, install with: pip install streamlit-aggrid")
    
    # Render filtering controls
    render_filtering_controls()
    # Create tabs for the hierarchical tables
    st.header("Data Selection")
    tab_projects, tab_cells, tab_experiments, tab_steps = st.tabs(["Projects", "Cells", "Experiments", "Steps"])

    with tab_projects:
        st.subheader("Projects")
        projects_df = get_projects_data()
        if not projects_df.empty:
            project_response = create_interactive_table(projects_df, "Projects")
            selected_project_rows = project_response.get("selected_rows", [])            
            if selected_project_rows is not None and len(selected_project_rows) > 0:
                selected_project_ids = extract_selected_ids(selected_project_rows, "Projects")
                st.session_state.selected_projects = selected_project_ids
                if selected_project_ids:
                    st.success(f"Selected {len(selected_project_ids)} project(s)")
                    # Add edit functionality
                    render_edit_button_and_modal("Projects", selected_project_rows)                
                else:
                    st.warning("Could not extract project IDs from selection")
            else:
                st.session_state.selected_projects = []
        else:
            st.warning("No projects found in database")
            st.session_state.selected_projects = []

    with tab_cells:
        st.subheader("Cells")
        cells_df = get_cells_data()  # 從 DB 取得 cell table
        if not cells_df.empty:
            # Apply cell filters
            cells_df = apply_filters(cells_df, "cells")
            cell_response = create_interactive_table(cells_df, "Cells")
            selected_cell_rows = cell_response.get("selected_rows", [])
            if selected_cell_rows is not None and len(selected_cell_rows) > 0:
                selected_cell_ids = extract_selected_ids(selected_cell_rows, "Cells")
                st.session_state.selected_cells = selected_cell_ids
                if selected_cell_ids:
                    st.success(f"Selected {len(selected_cell_ids)} cell(s)")
                    # Add edit functionality
                    render_edit_button_and_modal("Cells", selected_cell_rows)
                else:
                    st.warning("Could not extract cell IDs from selection")            
            else:
                st.session_state.selected_cells = []
        else:
            st.warning("No cells found in database")
            st.session_state.selected_cells = []

    with tab_experiments:
        st.subheader("Experiments")        # print(f"DEBUG: Getting experiments for project IDs: {st.session_state.selected_projects}") # Removed debug print
        experiments_df = get_experiments_data(st.session_state.selected_projects, st.session_state.selected_cells)
        # print(f"DEBUG: Experiments before filter: {len(experiments_df)} rows") # Removed debug print
        if not experiments_df.empty:
            experiments_df_filtered = apply_filters(experiments_df, "experiments")
            # print(f"DEBUG: Experiments after filter: {len(experiments_df_filtered)} rows") # Removed debug print
            
            if experiments_df_filtered.empty and not experiments_df.empty:
                st.info("No experiments match the current filter criteria.")
                st.session_state.selected_experiments = []
            else:
                experiment_response = create_interactive_table(experiments_df_filtered, "Experiments")
                selected_experiment_rows = experiment_response.get("selected_rows", [])
                if selected_experiment_rows is not None and len(selected_experiment_rows) > 0:
                    selected_experiment_ids = extract_selected_ids(selected_experiment_rows, "Experiments")
                    st.session_state.selected_experiments = selected_experiment_ids
                    if selected_experiment_ids:
                        st.success(f"Selected {len(selected_experiment_ids)} experiment(s)")
                        # Add edit functionality
                        render_edit_button_and_modal("Experiments", selected_experiment_rows)
                    else:
                        st.warning("Could not extract experiment IDs from selection")
                else:
                    st.session_state.selected_experiments = []
        else:
            if st.session_state.selected_projects:
                st.warning("No experiments found for selected projects")
            else:
                st.info("Select projects to view experiments")
            st.session_state.selected_experiments = []

    with tab_steps:
        st.subheader("Steps")
        steps_df = get_steps_data(st.session_state.selected_experiments)
        steps_df = apply_filters(steps_df, "steps")
        # 將 data_meta 欄位移到 id 和 step_number 之間
        if not steps_df.empty and 'data_meta' in steps_df.columns and 'id' in steps_df.columns and 'step_number' in steps_df.columns:
            cols = list(steps_df.columns)
            cols.remove('data_meta')
            id_idx = cols.index('id')
            step_number_idx = cols.index('step_number')
            # 插入到 id 之後、step_number 之前
            insert_idx = id_idx + 1 if step_number_idx > id_idx else step_number_idx
            cols.insert(insert_idx, 'data_meta')
            steps_df = steps_df[cols]
        selected_step_ids = []
        if not steps_df.empty:
            step_response = create_interactive_table(steps_df, "Steps")
            selected_step_rows = step_response.get("selected_rows", [])
            if selected_step_rows is not None and len(selected_step_rows) > 0:
                selected_step_ids = extract_selected_ids(selected_step_rows, "Steps")
                st.session_state.selected_steps = selected_step_ids
                if selected_step_ids:
                    st.success(f"Selected {len(selected_step_ids)} step(s)")
                    # Add edit functionality
                    render_edit_button_and_modal("Steps", selected_step_rows)
                    # Create filtered dataframe for plotting
                    selected_steps_df = steps_df[steps_df['id'].isin(selected_step_ids)]
                else:
                    st.warning("Could not extract step IDs from selection")
                    selected_steps_df = pd.DataFrame()
            else:
                st.session_state.selected_steps = []
                selected_steps_df = pd.DataFrame()
        else:
            if st.session_state.selected_experiments:
                st.warning("No steps found for selected experiments")
            else:
                st.info("Select experiments to view steps")
            st.session_state.selected_steps = []
            selected_steps_df = pd.DataFrame()
      # Plots Section
    st.divider()
    st.header("Data Visualization")

    # Step Plot
    if not steps_df.empty and st.session_state.selected_steps:
        selected_steps_df = steps_df[steps_df['id'].isin(st.session_state.selected_steps)]
        if not selected_steps_df.empty:
            render_step_plot(selected_steps_df)
        else:
            st.info("Selected steps are not found in the filtered data for plotting.")
            render_step_plot(pd.DataFrame(columns=STEP_DF_COLUMNS)) # Render with empty df
    elif not steps_df.empty:
        st.info("Select steps from the table above to see step-level scatter plots.")
        render_step_plot(pd.DataFrame(columns=STEP_DF_COLUMNS)) # Render with empty df
    else:
        render_step_plot(pd.DataFrame(columns=STEP_DF_COLUMNS))

    # Detail Plot (Measurements)
    if st.session_state.selected_steps:
        # Prepare meta map from the DataFrame that was used to select these steps
        selected_steps_meta_map = {}
        if not steps_df.empty and 'id' in steps_df.columns and 'data_meta' in steps_df.columns:
            relevant_steps_df = steps_df[steps_df['id'].isin(st.session_state.selected_steps)]
            if not relevant_steps_df.empty:
                selected_steps_meta_map = dict(zip(relevant_steps_df['id'], relevant_steps_df['data_meta']))
        
        render_detail_plot(st.session_state.selected_steps, selected_steps_meta_map)
    else:
        st.info("Select steps from the table above to see detailed time-series plots.")
        render_detail_plot([], {})

if __name__ == '__main__':
    render_dashboard_page()


