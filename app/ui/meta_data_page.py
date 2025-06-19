"""
Upload UI components for the Battery ETL Dashboard

This module provides UI components for uploading and processing battery test data files.
"""
import streamlit as st
from app.ui.components.meta_data_page.entity_management_ui import render_cell_management
from app.ui.components.meta_data_page.entity_management_ui import render_machine_management
from app.ui.components.meta_data_page.entity_management_ui import render_project_management
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
from app.models.database import Project
from app.utils.database import get_session as get_db_session
from app.utils.temp_files import temp_file_from_upload

# Define the path to example files
EXAMPLE_FOLDER = "./example_csv_chromaLex"


def render_meta_data_page():
    """Render the meta_data page UI
    
    This function displays the experiment information components.
    """
    # 顯示刷新提示
    st.info("如需更新資料，請點擊左側側邊欄的『Meta Data』頁籤以重新載入。")
    
    # Set up page
    st.title("電池 ETL 儀表板 - 基本資料")
    st.caption("在此管理您的實驗基本資料。請使用上方分頁切換 Cell、Machine 與 Meta Data。")
    
    # Get database entities for references
    # Try to get cells and machines with connection retry logic
    try:
        with get_db_session() as session:
            cells = session.query(Cell).order_by(Cell.name).all()
            machines = session.query(Machine).order_by(Machine.name).all()
            projects = session.query(Project).order_by(Project.name).all()
    except Exception as e:
        # If first attempt fails, try resetting the connection pool
        st.warning("偵測到資料庫連線問題，正在嘗試重新連線...")
        try:
            with get_db_session() as session:
                cells = session.query(Cell).order_by(Cell.name).all()
                machines = session.query(Machine).order_by(Machine.name).all()
                projects = session.query(Project).order_by(Project.name).all()
        except Exception as retry_error:
            st.error(f"重試後仍無法連線資料庫，請檢查資料庫設定或聯絡管理員。詳細資訊：{str(retry_error)}")
            st.info("請嘗試重新整理頁面，若問題持續發生請聯絡管理員。")
            cells = []
            machines = []
            projects = []
    
    # Create tabs for different sections
    tab1, tab2, tab3, tab4 = st.tabs([
        "Cell Management",
        "Machine Management",
        "Project Management",
        "Experiment Info"
    ])
    
    # Tab 1: Cell Management
    with tab1:
        render_cell_management()
    
    # Tab 2: Machine Management
    with tab2:
        render_machine_management()
    
    # Tab 3: Project Management
    with tab3:
        render_project_management()
    
    # Tab 4: Experiment Information
    with tab4:
        # Check if data is available from previous step
        has_data_from_preview = "selected_steps" in st.session_state
        
        # Render experiment metadata form
        render_experiment_metadata(cells, machines, has_data_from_preview, projects)
        
        # Render section for data from preview
        if has_data_from_preview:
            st.markdown("---")
            render_preview_data_section()