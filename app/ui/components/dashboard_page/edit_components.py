"""
Data editing components for the Battery ETL Dashboard
Provides UI components for editing database records
"""

import streamlit as st
import pandas as pd
from typing import Dict, Any, List, Optional
from datetime import datetime, date

from app.services.data_edit_service import (
    update_project, update_cell, update_experiment, update_step, update_measurement,
    get_editable_fields, get_field_type
)


def render_edit_form(table_name: str, record_data: Dict[str, Any], record_id: int) -> bool:
    """Render an edit form for a database record"""
    editable_fields = get_editable_fields(table_name)
    
    if not editable_fields:
        st.warning(f"No editable fields available for {table_name}")
        return False
    
    st.subheader(f"編輯 {table_name} (ID: {record_id})")
    
    # Create form
    with st.form(f"edit_{table_name}_{record_id}"):
        updates = {}
        
        for field in editable_fields:
            if field in record_data:
                current_value = record_data[field]
                field_type = get_field_type(field)
                new_value = None
                
                # Render appropriate input widget based on field type
                if field_type == "numeric":
                    if current_value is not None:
                        new_value = st.number_input(
                            f"{field}:",
                            value=float(current_value) if current_value is not None else 0.0,
                            key=f"{field}_{record_id}",
                            format="%.6f"
                        )
                    else:
                        new_value = st.number_input(
                            f"{field}:",
                            value=0.0,
                            key=f"{field}_{record_id}",
                            format="%.6f"
                        )
                        
                elif field_type == "datetime":
                    if current_value is not None:
                        if isinstance(current_value, str):
                            try:
                                current_datetime = datetime.fromisoformat(current_value.replace('Z', '+00:00'))
                                current_date = current_datetime.date()
                            except:
                                current_date = date.today()
                        elif isinstance(current_value, datetime):
                            current_date = current_value.date()
                        else:
                            current_date = date.today()
                    else:
                        current_date = date.today()
                    
                    date_input = st.date_input(
                        f"{field}:",
                        value=current_date,
                        key=f"{field}_{record_id}"
                    )
                    
                    time_input = st.time_input(
                        f"{field} time:",
                        value=datetime.now().time(),
                        key=f"{field}_time_{record_id}"
                    )
                    
                    # Combine date and time
                    new_value = datetime.combine(date_input, time_input)
                    
                else:  # text field
                    new_value = st.text_input(
                        f"{field}:",
                        value=str(current_value) if current_value is not None else "",
                        key=f"{field}_{record_id}"
                    )
                
                # Only include in updates if value has changed
                if new_value != current_value:
                    updates[field] = new_value
        
        # Submit button
        submitted = st.form_submit_button("💾 保存變更")
        
        if submitted and updates:
            # Call appropriate update function
            success = False
            if table_name.lower() == "projects":
                success = update_project(record_id, updates)
            elif table_name.lower() == "cells":
                success = update_cell(record_id, updates)
            elif table_name.lower() == "experiments":
                success = update_experiment(record_id, updates)
            elif table_name.lower() == "steps":
                success = update_step(record_id, updates)
            elif table_name.lower() == "measurements":
                success = update_measurement(record_id, updates)
            
            if success:
                st.success(f"✅ {table_name} 記錄已成功更新！")
                st.rerun()  # Refresh the page to show updated data
                return True
            else:
                st.error(f"❌ 更新 {table_name} 記錄時出錯")
        
        elif submitted and not updates:
            st.info("ℹ️ 沒有檢測到變更")
    
    return False


def render_bulk_edit_form(table_name: str, records: List[Dict[str, Any]]) -> bool:
    """Render a bulk edit form for multiple records"""
    if not records:
        st.warning("沒有選中的記錄進行批量編輯")
        return False
    
    editable_fields = get_editable_fields(table_name)
    if not editable_fields:
        st.warning(f"No editable fields available for {table_name}")
        return False
    
    st.subheader(f"批量編輯 {table_name} ({len(records)} 條記錄)")
    
    # Show selected records
    with st.expander("查看選中的記錄", expanded=False):
        df = pd.DataFrame(records)
        st.dataframe(df)
    
    # Create bulk edit form
    with st.form(f"bulk_edit_{table_name}"):
        st.write("選擇要批量更新的欄位：")
        
        updates = {}
        enabled_updates = {}
        
        for field in editable_fields:
            col1, col2 = st.columns([1, 3])
            
            with col1:
                enable_field = st.checkbox(
                    f"更新 {field}",
                    key=f"enable_{field}_bulk"
                )
                enabled_updates[field] = enable_field
            
            with col2:
                if enable_field:
                    field_type = get_field_type(field)
                    
                    if field_type == "numeric":
                        new_value = st.number_input(
                            f"新的 {field} 值:",
                            value=0.0,
                            key=f"{field}_bulk",
                            format="%.6f"
                        )
                    elif field_type == "datetime":
                        date_input = st.date_input(
                            f"新的 {field} 日期:",
                            value=date.today(),
                            key=f"{field}_bulk"
                        )
                        time_input = st.time_input(
                            f"新的 {field} 時間:",
                            value=datetime.now().time(),
                            key=f"{field}_time_bulk"
                        )
                        new_value = datetime.combine(date_input, time_input)
                    else:
                        new_value = st.text_input(
                            f"新的 {field} 值:",
                            key=f"{field}_bulk"
                        )
                    
                    if enable_field:
                        updates[field] = new_value
        
        # Submit button
        submitted = st.form_submit_button("💾 批量保存變更", type="primary")
        
        if submitted and updates:
            success_count = 0
            error_count = 0
            
            # Progress bar
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for i, record in enumerate(records):
                record_id = record.get('id')
                if record_id:
                    # Call appropriate update function
                    success = False
                    if table_name.lower() == "projects":
                        success = update_project(record_id, updates)
                    elif table_name.lower() == "cells":
                        success = update_cell(record_id, updates)
                    elif table_name.lower() == "experiments":
                        success = update_experiment(record_id, updates)
                    elif table_name.lower() == "steps":
                        success = update_step(record_id, updates)
                    elif table_name.lower() == "measurements":
                        success = update_measurement(record_id, updates)
                    
                    if success:
                        success_count += 1
                    else:
                        error_count += 1
                
                # Update progress
                progress = (i + 1) / len(records)
                progress_bar.progress(progress)
                status_text.text(f"處理中... {i + 1}/{len(records)}")
            
            # Show results
            if success_count > 0:
                st.success(f"✅ 成功更新 {success_count} 條記錄！")
            if error_count > 0:
                st.error(f"❌ 更新 {error_count} 條記錄時出錯")
            
            if success_count > 0:
                st.rerun()  # Refresh the page to show updated data
                return True
        
        elif submitted and not updates:
            st.info("ℹ️ 請選擇至少一個欄位進行更新")
    
    return False


def render_edit_button_and_modal(table_name: str, selected_rows: List[Dict[str, Any]]):
    """Render edit button and modal for selected records"""
    if not selected_rows:
        return
    
    # Create columns for edit buttons
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        if len(selected_rows) == 1:
            if st.button("✏️ 編輯選中記錄", key=f"edit_{table_name}"):
                st.session_state[f"show_edit_{table_name}"] = True
    
    with col2:
        if len(selected_rows) > 1:
            if st.button("📝 批量編輯", key=f"bulk_edit_{table_name}"):
                st.session_state[f"show_bulk_edit_{table_name}"] = True
    
    # Show edit modal for single record
    if st.session_state.get(f"show_edit_{table_name}", False):
        with st.container():
            st.markdown("---")
            record = selected_rows[0]
            record_id = record.get('id')
            
            if record_id:
                success = render_edit_form(table_name, record, record_id)
                if success:
                    st.session_state[f"show_edit_{table_name}"] = False
            
            if st.button("❌ 取消編輯", key=f"cancel_edit_{table_name}"):
                st.session_state[f"show_edit_{table_name}"] = False
                st.rerun()
    
    # Show bulk edit modal
    if st.session_state.get(f"show_bulk_edit_{table_name}", False):
        with st.container():
            st.markdown("---")
            success = render_bulk_edit_form(table_name, selected_rows)
            if success:
                st.session_state[f"show_bulk_edit_{table_name}"] = False
            
            if st.button("❌ 取消批量編輯", key=f"cancel_bulk_edit_{table_name}"):
                st.session_state[f"show_bulk_edit_{table_name}"] = False
                st.rerun()
