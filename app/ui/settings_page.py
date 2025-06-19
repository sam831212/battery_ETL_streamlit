"""
Settings UI components for the Battery ETL Dashboard

This module provides UI components for configuring database connections,
file formats, and other application settings.
"""
import streamlit as st
from app.utils.database import test_db_connection, init_db, get_session
from app.utils.config import (
    DB_PATH, DATABASE_URL
)
from app.models.database import Cell, CellChemistry, CellFormFactor, Machine, Experiment
from sqlmodel import select, delete, func


def render_settings_page():
    """Render the settings page UI"""
    st.title("設定")
    
    st.subheader("資料庫設定")
    st.info("使用 SQLite 資料庫")
    st.write(f"資料庫檔案：{DB_PATH}")
    st.write(f"資料庫連線字串：{DATABASE_URL}")
    
    # Add a button to test database connection
    if st.button("測試資料庫連線", help="驗證與目前設定之 SQLite 資料庫的連線狀態。"):
        with st.spinner("連線測試中..."):
            try:
                from app.utils.database import test_db_connection # Local import if not already at top
                if test_db_connection():
                    st.success("資料庫連線成功！")
                else:
                    st.error("資料庫連線失敗，請檢查日誌以獲得詳細資訊。")
            except Exception as e:
                st.error(f"測試資料庫連線時發生錯誤。詳細資訊：{str(e)}")
    
def render_file_format_settings():
    """Render file format settings"""
    st.header("檔案格式設定")
    
    # File format settings
    st.subheader("CSV 匯入設定")
    
    col1, col2 = st.columns(2)
    
    with col1:
        delimiter = st.selectbox(
            "CSV 分隔符號",
            options=[",", ";", "\t", "|"],
            index=0,
            help="CSV 檔案中使用的分隔符號",
        )
        
        encoding = st.selectbox(
            "檔案編碼",
            options=["utf-8", "latin-1", "iso-8859-1", "cp1252"],
            index=0,
            help="輸入檔案所使用的字元編碼",
        )
    
    with col2:
        header_row = st.number_input(
            "標題列（Header Row）",
            min_value=0,
            max_value=10,
            value=0,
            help="包含欄位名稱的列號（從 0 開始）",
        )
        
        skip_rows = st.number_input(
            "跳過列數",
            min_value=0,
            max_value=10,
            value=0,
            help="檔案開頭要跳過的列數",
        )
    
    # Save button
    if st.button("儲存檔案格式設定", type="primary"):
        # In a real implementation, these would be saved to a database or config file
        st.session_state["delimiter"] = delimiter
        st.session_state["encoding"] = encoding
        st.session_state["header_row"] = header_row
        st.session_state["skip_rows"] = skip_rows
        st.success("檔案格式設定已儲存！")


def render_ui_preferences():
    """Render UI preference settings"""
    st.header("介面偏好設定")
    
    # UI preference settings
    st.subheader("顯示設定")
    
    col1, col2 = st.columns(2)
    
    with col1:
        show_debug_info = st.toggle(
            "顯示除錯資訊",
            value=st.session_state.get("show_debug_info", False),
            help="在介面中顯示額外的除錯資訊",
        )
        
        decimals = st.slider(
            "小數位數",
            min_value=1,
            max_value=6,
            value=st.session_state.get("decimals", 2),
            help="數值顯示的小數位數",
        )
    
    with col2:
        default_plot_height = st.slider(
            "預設圖表高度",
            min_value=300,
            max_value=800,
            value=st.session_state.get("default_plot_height", 400),
            help="圖表預設高度（像素）",
        )
        
        default_theme = st.selectbox(
            "預設主題",
            options=["Light", "Dark", "Auto"],
            index=0 if st.session_state.get("default_theme", "Light") == "Light" else 
                  1 if st.session_state.get("default_theme", "Light") == "Dark" else 2,
            help="應用程式的預設主題",
        )
    
    # Save button
    if st.button("儲存介面偏好設定", type="primary"):
        # In a real implementation, these would be saved to a database or config file
        st.session_state["show_debug_info"] = show_debug_info
        st.session_state["decimals"] = decimals
        st.session_state["default_plot_height"] = default_plot_height
        st.session_state["default_theme"] = default_theme
        st.success("介面偏好設定已儲存！")


def render_cell_management():
    """Render cell management UI"""
    st.header("電池管理")
    
    # Display existing cells
    st.subheader("現有電池")
    
    with get_session() as session:
        cells = session.exec(select(Cell).order_by(Cell.id)).all()
        
        if cells:
            # Create a table to display cells
            cell_data = []
            for cell in cells:
                cell_data.append({
                    "ID": cell.id,
                    "名稱": cell.name or "N/A",
                    "化學組成": cell.chemistry.value,
                    "容量 (Ah)": cell.capacity,
                    "外型": cell.form.value
                })
            
            st.dataframe(cell_data, use_container_width=True)
        else:
            st.info("尚未新增任何電池。")
    
    # Form to add a new cell
    st.subheader("新增電池")
    
    with st.form(key="add_cell_form"):
        # Cell properties
        cell_name = st.text_input(
            "電池名稱",
            help="為此電池命名（可選）"
        )
        
        chemistry = st.selectbox(
            "化學組成",
            options=[chem.value for chem in CellChemistry],
            help="選擇電池的化學組成"
        )
        
        capacity = st.number_input(
            "容量 (Ah)",
            min_value=0.1,
            max_value=1000.0,
            value=1.0,
            step=0.1,
            help="電池的額定容量（安培小時）"
        )
        
        form_factor = st.selectbox(
            "外型",
            options=[form.value for form in CellFormFactor],
            help="選擇電池的物理外型"
        )
        
        # Submit button
        submitted = st.form_submit_button("新增電池", type="primary")
    
    if submitted:
        # Create new cell in database
        with st.spinner("新增電池至資料庫中..."):
            with get_session() as session:
                new_cell = Cell(
                    name=cell_name if cell_name else None,
                    chemistry=CellChemistry(chemistry),
                    capacity=capacity,
                    form=CellFormFactor(form_factor)
                )
                
                session.add(new_cell)
                session.commit()
                
                st.success(f"新電池 '{new_cell.name or 'N/A'}' 新增成功！ID: {new_cell.id}")
                st.rerun()
    
    # Delete cell section
    st.subheader("刪除電池")
    
    with get_session() as session:
        all_cells = session.exec(select(Cell).order_by(Cell.id)).all()
        
        if all_cells:
            cell_options = [f"ID {cell.id}: {cell.chemistry.value}, {cell.capacity} Ah, {cell.form.value}" for cell in all_cells]
            cell_ids = [cell.id for cell in all_cells]
            
            col1, col2 = st.columns([3, 1])
            
            with col1:
                selected_cell_index = st.selectbox(
                    "選擇要刪除的電池",
                    options=range(len(cell_options)),
                    format_func=lambda x: cell_options[x],
                    help="選擇要永久刪除的電池資料。"
                )
            
            with col2:
                delete_button = st.button("刪除電池", type="secondary", help="將所選電池從資料庫中永久移除。")
            
            if delete_button:
                if st.session_state.get("confirm_delete_cell", False):
                    with st.spinner("從資料庫刪除電池中..."):
                        # Perform deletion
                        cell_id_to_delete = cell_ids[selected_cell_index]
                        
                        # Check if the cell is referenced by any experiments
                        experiment_count = session.exec(select(func.count(Experiment.id)).where(Experiment.cell_id == cell_id_to_delete)).one()
                        
                        if experiment_count > 0:
                            st.error(f"無法刪除電池（ID: {cell_id_to_delete}），因為有 {experiment_count} 筆實驗資料引用此電池。請先更新或移除相關實驗。")
                        else:
                            # Safe to delete
                            session.exec(delete(Cell).where(Cell.id == cell_id_to_delete))
                            session.commit()
                            st.success(f"ID 為 {cell_id_to_delete} 的電池已成功刪除！")
                            st.session_state["confirm_delete_cell"] = False # Reset confirmation
                            st.rerun()
                else:
                    st.warning("⚠️ 確定要刪除此電池嗎？此操作無法復原。")
                    if st.button("確認刪除電池", type="primary", key="confirm_delete_cell_btn"):
                        st.session_state["confirm_delete_cell"] = True
                        st.rerun() # Rerun to process the delete on next click if confirmed
        else:
            st.info("目前沒有可刪除的電池。")


def render_machine_management():
    """Render machine management UI"""
    st.header("設備管理")
    
    # Display existing machines
    st.subheader("現有設備")
    
    with get_session() as session:
        machines = session.exec(select(Machine).order_by(Machine.id)).all()
        
        if machines:
            # Create a table to display machines
            machine_data = []
            for machine in machines:
                machine_data.append({
                    "ID": machine.id,
                    "名稱": machine.name,
                    "型號": machine.model_number or "N/A",
                    "描述": machine.description or "N/A"
                })
            
            st.dataframe(machine_data, use_container_width=True)
        else:
            st.info("尚未新增任何設備。")
    
    # Form to add a new machine
    st.subheader("新增設備")
    
    with st.form(key="add_machine_form"):
        # Machine properties
        name = st.text_input(
            "名稱",
            max_chars=100,
            help="設備名稱"
        )
        
        model_number = st.text_input(
            "型號",
            max_chars=50,
            help="設備型號（可選）"
        )
        
        description = st.text_area(
            "描述",
            max_chars=500,
            help="設備的其他說明（可選）"
        )
        
        # Submit button
        submitted = st.form_submit_button("新增設備", type="primary")
    
    if submitted:
        if not name:
            st.error("設備名稱為必填欄位。")
        else:
            # Create new machine in database
            with st.spinner("新增設備至資料庫中..."):
                with get_session() as session:
                    new_machine = Machine(
                        name=name,
                        model_number=model_number if model_number else None,
                        description=description if description else None
                    )
                    
                    session.add(new_machine)
                    session.commit()
                    
                    st.success(f"新設備 '{new_machine.name}' 新增成功！ID: {new_machine.id}")
                    st.rerun()
    
    # Delete machine section
    st.subheader("刪除設備")
    
    with get_session() as session:
        all_machines = session.exec(select(Machine).order_by(Machine.id)).all()
        
        if all_machines:
            machine_options = [f"ID {machine.id}: {machine.name}" + (f" ({machine.model_number})" if machine.model_number else "") for machine in all_machines]
            machine_ids = [machine.id for machine in all_machines]
            
            col1, col2 = st.columns([3, 1])
            
            with col1:
                selected_machine_index = st.selectbox(
                    "選擇要刪除的設備",
                    options=range(len(machine_options)),
                    format_func=lambda x: machine_options[x],
                    help="選擇要永久刪除的設備資料。"
                )
            
            with col2:
                delete_button = st.button("刪除設備", type="secondary", help="將所選設備從資料庫中永久移除。")
            
            if delete_button:
                if st.session_state.get("confirm_delete_machine", False):
                    with st.spinner("從資料庫刪除設備中..."):
                        # Perform deletion
                        machine_id_to_delete = machine_ids[selected_machine_index]
                        
                        # Check if the machine is referenced by any experiments
                        experiment_count = session.exec(select(func.count(Experiment.id)).where(Experiment.machine_id == machine_id_to_delete)).one()
                        
                        if experiment_count > 0:
                            st.error(f"無法刪除設備（ID: {machine_id_to_delete}），因為有 {experiment_count} 筆實驗資料引用此設備。請先更新或移除相關實驗。")
                        else:
                            # Safe to delete
                            session.exec(delete(Machine).where(Machine.id == machine_id_to_delete))
                            session.commit()
                            st.success(f"ID 為 {machine_id_to_delete} 的設備已成功刪除！")
                            st.session_state["confirm_delete_machine"] = False # Reset confirmation
                            st.rerun()
                else:
                    st.warning("⚠️ 確定要刪除此設備嗎？此操作無法復原。")
                    if st.button("確認刪除設備", type="primary", key="confirm_delete_machine_btn"):
                        st.session_state["confirm_delete_machine"] = True
                        st.rerun() # Rerun to process the delete on next click if confirmed
        else:
            st.info("目前沒有可刪除的設備。")