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
from app.ui.components.dashboard_page.edit_components import render_edit_button_and_modal
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
    st.title("電池 ETL 儀表板")
    st.markdown("探索並視覺化專案、實驗與步驟層級的電池測試資料。")
    
    # Initialize session state
    init_session_state()
    
    # Show AgGrid availability status
    if not AGGRID_AVAILABLE:
        st.warning("st_aggrid 尚未安裝。將使用備用表格。完整功能請安裝：pip install streamlit-aggrid")
    

    # Create tabs for the hierarchical tables
    st.header("資料選擇")
    tab_projects, tab_cells, tab_experiments, tab_steps = st.tabs(["Project", "Cell", "Experiment", "Step"])

    with tab_projects:
        st.subheader("Project")
        projects_df = get_projects_data()
        if not projects_df.empty:
            project_response = create_interactive_table(projects_df, "Projects")
            selected_project_rows = project_response.get("selected_rows", [])            
            if selected_project_rows is not None and len(selected_project_rows) > 0:
                selected_project_ids = extract_selected_ids(selected_project_rows, "Projects")
                st.session_state.selected_projects = selected_project_ids
                if selected_project_ids:
                    st.success(f"已選取 {len(selected_project_ids)} 個專案")
                    # Add edit functionality
                    render_edit_button_and_modal("Projects", selected_project_rows)                
                else:
                    st.warning("無法從選取項目中取得專案 ID")
            else:
                st.session_state.selected_projects = []
        else:
            st.warning("資料庫中找不到專案")
            st.session_state.selected_projects = []

    with tab_cells:
        st.subheader("Cell")
        cells_df = get_cells_data()  # 從 DB 取得 cell table
        if not cells_df.empty:
            # 直接使用 cells_df，不再 apply_filters
            cell_response = create_interactive_table(cells_df, "Cells")
            selected_cell_rows = cell_response.get("selected_rows", [])
            if selected_cell_rows is not None and len(selected_cell_rows) > 0:
                selected_cell_ids = extract_selected_ids(selected_cell_rows, "Cells")
                st.session_state.selected_cells = selected_cell_ids
                if selected_cell_ids:
                    st.success(f"已選取 {len(selected_cell_ids)} 顆電池")
                    # Add edit functionality
                    render_edit_button_and_modal("Cells", selected_cell_rows)
                else:
                    st.warning("無法從選取項目中取得電池 ID")            
            else:
                st.session_state.selected_cells = []
        else:
            st.warning("資料庫中找不到電池")
            st.session_state.selected_cells = []

    with tab_experiments:
        st.subheader("Experiment")        # print(f"DEBUG: Getting experiments for project IDs: {st.session_state.selected_projects}") # Removed debug print
        experiments_df = get_experiments_data(st.session_state.selected_projects, st.session_state.selected_cells)
        # print(f"DEBUG: Experiments before filter: {len(experiments_df)} rows") # Removed debug print
        if not experiments_df.empty:
            # 直接使用 experiments_df，不再 apply_filters
            experiments_df_filtered = experiments_df
            # print(f"DEBUG: Experiments after filter: {len(experiments_df_filtered)} rows") # Removed debug print
            
            if experiments_df_filtered.empty and not experiments_df.empty:
                st.info("目前的篩選條件下沒有符合的實驗。")
                st.session_state.selected_experiments = []
            else:
                experiment_response = create_interactive_table(experiments_df_filtered, "Experiments")
                selected_experiment_rows = experiment_response.get("selected_rows", [])
                if selected_experiment_rows is not None and len(selected_experiment_rows) > 0:
                    selected_experiment_ids = extract_selected_ids(selected_experiment_rows, "Experiments")
                    st.session_state.selected_experiments = selected_experiment_ids
                    if selected_experiment_ids:
                        st.success(f"已選取 {len(selected_experiment_ids)} 個實驗")
                        # Add edit functionality
                        render_edit_button_and_modal("Experiments", selected_experiment_rows)                    
                    else:
                        st.warning("無法從選取項目中取得實驗 ID")
                else:
                    st.session_state.selected_experiments = []
        else:
            if st.session_state.selected_projects:
                st.warning("所選專案下找不到實驗")
            else:
                st.info("請先選擇專案以檢視實驗")
            st.session_state.selected_experiments = []

    with tab_steps:
        st.subheader("Step")
        steps_df = get_steps_data(st.session_state.selected_experiments)
        # 直接使用 steps_df，不再 apply_filters
        if not steps_df.empty:
            step_response = create_interactive_table(steps_df, "Steps")
            selected_step_rows = step_response.get("selected_rows", [])
            if selected_step_rows and len(selected_step_rows) > 0:
                selected_step_ids = extract_selected_ids(selected_step_rows, "Steps")
                st.session_state.selected_steps = selected_step_ids
                if selected_step_ids:
                    st.success(f"已選取 {len(selected_step_ids)} 個步驟")
                    render_edit_button_and_modal("Steps", selected_step_rows)
                else:
                    st.warning("無法從選取項目中取得步驟 ID")
            else:
                st.session_state.selected_steps = []
        else:
            if st.session_state.selected_experiments:
                st.warning("所選實驗下找不到步驟")
            else:
                st.info("請先選擇實驗以檢視步驟")
            st.session_state.selected_steps = []
      # Plots Section
    st.divider()
    st.header("資料視覺化")

    # Step Plot
    if not steps_df.empty and st.session_state.selected_steps:
        selected_steps_df = steps_df[steps_df['id'].isin(st.session_state.selected_steps)]
        if not selected_steps_df.empty:
            render_step_plot(selected_steps_df)
        else:
            st.info("所選步驟在篩選後的資料中找不到，無法繪圖。")
            render_step_plot(pd.DataFrame(columns=STEP_DF_COLUMNS)) # Render with empty df
    elif not steps_df.empty:
        st.info("請從上方表格選擇步驟以檢視步驟層級的散佈圖。")
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
        st.info("請從上方表格選擇步驟以檢視詳細時序圖。")
        render_detail_plot([], {})

if __name__ == '__main__':
    render_dashboard_page()


