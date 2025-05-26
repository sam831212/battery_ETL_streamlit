"""
Step Selection UI components for the Battery ETL Dashboard

This module provides UI components for selecting and filtering battery test steps
for analysis and database loading.
"""
import streamlit as st
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any

from app.etl.transformation import calculate_soc


def format_range(start: float, end: float, format_str: str = "{:.2f}") -> str:
    """
    Format a range of values as a string.
    
    Args:
        start: Start value of the range
        end: End value of the range
        format_str: Format string for the values
        
    Returns:
        String representation of the range
    """
    if pd.isna(start) or pd.isna(end):
        return "N/A"
    
    start_str = format_str.format(start)
    end_str = format_str.format(end)
    
    return f"{start_str} → {end_str}"


def init_step_selection_state():
    """
    Initialize session state variables for step selection.
    """
    if 'full_discharge_step_idx' not in st.session_state:
        st.session_state.full_discharge_step_idx = None
    
    if 'selected_steps_for_db' not in st.session_state:
        st.session_state.selected_steps_for_db = []
        
    # Temporary storage for DB selections before update
    if 'temp_selected_steps_for_db' not in st.session_state:
        st.session_state.temp_selected_steps_for_db = []
        
    if 'steps_df_with_soc' not in st.session_state:
        st.session_state.steps_df_with_soc = None
        
    if 'details_df_with_soc' not in st.session_state:
        st.session_state.details_df_with_soc = None
        
    if 'filtered_step_types' not in st.session_state:
        st.session_state.filtered_step_types = ["charge", "discharge", "rest", "waveform"]
        
    # Temporary storage for selected reference step before update
    if 'temp_reference_step_idx' not in st.session_state:
        st.session_state.temp_reference_step_idx = None
        
    # Flag to track if update is needed
    if 'update_needed' not in st.session_state:
        st.session_state.update_needed = False
        
    # Store the last used steps dataframe for SOC calculations
    if 'current_steps_df' not in st.session_state:
        st.session_state.current_steps_df = None


def calculate_step_ranges(steps_df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate range values for step data.
    
    Args:
        steps_df: DataFrame containing step data
        
    Returns:
        DataFrame with additional range columns
    """
    # Make a copy to avoid modifying the original
    df = steps_df.copy()
    
    # Add SOC range column if SOC columns exist
    if 'soc_start' in df.columns and 'soc_end' in df.columns:
        df['soc_range'] = df.apply(
            lambda row: format_range(row['soc_start'], row['soc_end'], "{:.1f}%") 
            if not pd.isna(row['soc_start']) and not pd.isna(row['soc_end']) 
            else "N/A", 
            axis=1
        )
    else:
        df['soc_range'] = "N/A"
    
    # Add C-rate range column if c_rate column exists
    if 'c_rate' in df.columns:
        # Use the same C-rate for start and end as a simplification
        # Alternatively, you could calculate min/max C-rate for each step
        df['c_rate_range'] = df.apply(
            lambda row: format_range(row['c_rate'], row['c_rate'], "{:.2f}C")
            if not pd.isna(row['c_rate'])
            else "N/A",
            axis=1
        )
    else:
        df['c_rate_range'] = "N/A"
    
    # Add temperature range column if temperature_min and temperature_max exist
    if 'temperature_min' in df.columns and 'temperature_max' in df.columns:
        df['temperature_range'] = df.apply(
            lambda row: format_range(row['temperature_min'], row['temperature_max'], "{:.1f}°C")
            if not pd.isna(row['temperature_min']) and not pd.isna(row['temperature_max'])
            else "N/A",
            axis=1
        )
    elif 'temperature' in df.columns:
        # If only single temperature value is available
        df['temperature_range'] = df.apply(
            lambda row: format_range(row['temperature'], row['temperature'], "{:.1f}°C")
            if not pd.isna(row['temperature'])
            else "N/A",
            axis=1
        )
    else:
        df['temperature_range'] = "N/A"
        
    return df


def filter_steps_by_type(steps_df: pd.DataFrame, step_types: List[str]) -> pd.DataFrame:
    """
    Filter steps by step type.
    
    Args:
        steps_df: DataFrame containing step data
        step_types: List of step types to include
        
    Returns:
        Filtered DataFrame
    """
    return steps_df[steps_df['step_type'].isin(step_types)]


def display_steps_table(steps_df: pd.DataFrame) -> Tuple[pd.DataFrame, Optional[int], List[int]]:
    """
    Display a table of steps with selection functionality.
    
    Args:
        steps_df: DataFrame containing step data
        
    Returns:
        Tuple containing:
        - Filtered DataFrame
        - Selected full discharge step index (or None)
        - List of selected step indices for database loading
    """
    # Initialize session state if needed
    init_step_selection_state()
    
    # Calculate ranges for display
    display_df = calculate_step_ranges(steps_df)
    
    # Filter step types
    st.subheader("Filter Steps")
    
    # Allow user to select which step types to display
    available_step_types = sorted(display_df['step_type'].unique().tolist())
    
    # Filter default step types to only include available ones
    filtered_defaults = [step_type for step_type in st.session_state.filtered_step_types 
                        if step_type in available_step_types]
    
    selected_step_types = st.multiselect(
        "Select step types to display:",
        options=available_step_types,
        default=filtered_defaults,
        key="step_type_filter"
    )
    
    # Update session state with selected step types
    st.session_state.filtered_step_types = selected_step_types
    
    # Filter based on selected step types
    if selected_step_types:
        filtered_df = filter_steps_by_type(display_df, selected_step_types)
    else:
        filtered_df = display_df
        
    # Check if there are discharge steps for reference selection
    discharge_steps = filtered_df[filtered_df['step_type'] == 'discharge']
    has_discharge_steps = not discharge_steps.empty
    
    if not has_discharge_steps:
        st.warning("No discharge steps available for reference selection. Please include discharge steps in your filter.")
    
    # Prepare columns for display
    # Create a new DataFrame for display to avoid modifying the filtered one
    display_cols = [
        'step_number', 
        'original_step_type', 
        'step_type', 
        'duration',  # 使用原始資料中的工步執行時間(秒)
        'c_rate_range', 
        'soc_range', 
        'temperature_range',
        ]
    
    # Add full_discharge_reference column for selection
    filtered_df['full_discharge_reference'] = False
    
    # Add db_selection column for selection
    filtered_df['db_selection'] = False
    
    # Update based on session state
    if st.session_state.full_discharge_step_idx is not None:
        if st.session_state.full_discharge_step_idx in filtered_df.index:
            filtered_df.loc[st.session_state.full_discharge_step_idx, 'full_discharge_reference'] = True
    
    # Initialize temp_selected_steps_for_db with selected_steps_for_db if empty
    if not st.session_state.temp_selected_steps_for_db and st.session_state.selected_steps_for_db:
        st.session_state.temp_selected_steps_for_db = st.session_state.selected_steps_for_db.copy()
    
    # Use the temporary selections for display in the data editor
    # This ensures the UI shows the most recent checkbox selections
    for idx in st.session_state.temp_selected_steps_for_db:
        if idx in filtered_df.index:
            filtered_df.loc[idx, 'db_selection'] = True
    
    # Create two sections: one for reference selection, one for DB selection
    st.subheader("Step Selection")
    
    # Display the steps table
    st.write("#### Select Full Discharge Reference Step (for SOC calculation)")
    discharge_only = filtered_df[filtered_df['step_type'] == 'discharge'].copy()
    
    # Only show discharge steps for reference selection
    if not discharge_only.empty:
        # Create a radio button for selecting the reference discharge step
        # 只取前 5 個放電工步
        discharge_options = {
            f"Step {row['step_number']} ({row['original_step_type']})": idx 
            for idx, row in discharge_only.head(5).iterrows()
        }
        
        # Add a "None" option
        discharge_options["None (Auto-detect)"] = None
        
        # 如果放電工步超過 5 個，顯示提示訊息
        if len(discharge_only) > 5:
            st.info(f"顯示前 5 個放電工步（共 {len(discharge_only)} 個）。")
        
        # Determine the current index in options based on session state
        current_idx = st.session_state.full_discharge_step_idx
        current_option = next(
            (k for k, v in discharge_options.items() if v == current_idx), 
            "None (Auto-detect)"
        )
        
        selected_reference_option = st.radio(
            "Select a discharge step as 0% SOC reference:",
            options=list(discharge_options.keys()),
            index=list(discharge_options.keys()).index(current_option),
            key="reference_step_selector"
        )
        
        selected_reference_idx = discharge_options[selected_reference_option]
        
        # Store selection in temporary state and set update flag
        if selected_reference_idx != st.session_state.temp_reference_step_idx:
            st.session_state.temp_reference_step_idx = selected_reference_idx
            st.session_state.update_needed = True
    else:
        st.info("No discharge steps available for reference selection. Include discharge steps in your filter.")
        selected_reference_idx = None
    
    # Display section for database loading selection
    st.write("#### Select Steps for Database Loading")
    
    # Add db_selection column to DataFrame if it doesn't exist
    if 'db_selection' not in filtered_df.columns:
        filtered_df['db_selection'] = False
        
    # Set initial values for db_selection based on session state
    for idx in filtered_df.index:
        filtered_df.loc[idx, 'db_selection'] = idx in st.session_state.temp_selected_steps_for_db
    
    # Create a form to wrap the data editor
    with st.form(key="step_selection_form"):
        st.write("Select steps to include in database loading:")
        
        # Store a copy of the filtered_df in session state to compare changes
        if 'previous_filtered_df' not in st.session_state:
            st.session_state.previous_filtered_df = filtered_df.copy()
        
        # Create a data editor for multi-selection
        edited_df = st.data_editor(
            filtered_df[display_cols + ['db_selection']],
            column_config={
                "step_number": st.column_config.NumberColumn("工步編號"),
                "original_step_type": st.column_config.TextColumn("原始工步類型"),
                "step_type": st.column_config.TextColumn("工步動作"),
                "c_rate_range": st.column_config.TextColumn("充放電倍率"),
                "soc_range": st.column_config.TextColumn("SOC範圍"),
                "temperature_range": st.column_config.TextColumn("溫度範圍"),
                "duration": st.column_config.NumberColumn("工步執行時間(秒)", format="%.1f"),
                "db_selection": st.column_config.CheckboxColumn("選擇載入資料庫"),
            },
            hide_index=True,
            use_container_width=True,
            key="step_selection_table"
        )
        
        # Add a form submit button
        submit_form = st.form_submit_button("Apply Selection Changes", type="primary")
    
    # When form is submitted, update the session state
    if submit_form:
        # Update the temporary db selection in session state based on edited values
        temp_selected_db_indices = []
        for idx, row in edited_df.iterrows():
            if row['db_selection']:
                temp_selected_db_indices.append(idx)
        
        # Update temporary session state and set update flag
        if set(temp_selected_db_indices) != set(st.session_state.temp_selected_steps_for_db):
            st.session_state.temp_selected_steps_for_db = temp_selected_db_indices
            st.session_state.update_needed = True
            
        # Store the edited dataframe for future comparison
        st.session_state.previous_filtered_df = edited_df.copy()
        
    # Use the actual selections for returning
    selected_db_indices = st.session_state.selected_steps_for_db
    
    return filtered_df, selected_reference_idx, selected_db_indices


def handle_reference_step_selection(
    steps_df: pd.DataFrame, 
    details_df: pd.DataFrame,
    full_discharge_step_idx: Optional[int] = None
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Handle the reference step selection and recalculate SOC values.
    
    Args:
        steps_df: DataFrame containing step data
        details_df: DataFrame containing detailed measurement data
        full_discharge_step_idx: Optional index of the discharge step to use as reference
        
    Returns:
        Tuple containing:
        - Updated steps DataFrame with SOC values
        - Updated details DataFrame with SOC values
    """
    if full_discharge_step_idx is not None:
        st.info(f"Recalculating SOC using the selected discharge step as reference.")
    else:
        st.info("Recalculating SOC using automatic reference step detection.")
    
    # Calculate SOC with the selected reference step
    try:
        steps_with_soc, details_with_soc = calculate_soc(
            steps_df.copy(), 
            details_df.copy(),
            full_discharge_step_idx=full_discharge_step_idx
        )
        
        # Update session state
        st.session_state.steps_df_with_soc = steps_with_soc
        st.session_state.details_df_with_soc = details_with_soc
        
        # Success message
        st.success("Successfully recalculated SOC with the new reference step!")
        
        return steps_with_soc, details_with_soc
        
    except Exception as e:
        st.error(f"Error calculating SOC: {str(e)}")
        st.error("Check if the reference step has valid capacity data.")
        return steps_df, details_df


def display_selected_steps_overview(filtered_df: pd.DataFrame, selected_indices: List[int]):
    """
    Display an overview of the selected steps.
    
    Args:
        filtered_df: DataFrame containing step data
        selected_indices: List of selected step indices
    """
    if not selected_indices:
        st.info("No steps selected for database loading. Please select steps using the checkboxes above.")
        return
    
    # Filter to only show selected steps (safely)
    # Make sure all indices exist in the filtered_df
    valid_indices = [idx for idx in selected_indices if idx in filtered_df.index]
    
    if not valid_indices:
        st.info("No valid steps selected. Please select steps using the checkboxes above.")
        return
        
    selected_df = filtered_df.loc[valid_indices]
    
    st.subheader("Selected Steps Overview")
    
    # Display count by step type
    step_type_counts = selected_df['step_type'].value_counts().reset_index()
    step_type_counts.columns = ['Step Type', 'Count']
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write(f"Total selected steps: {len(selected_df)}")
        st.dataframe(step_type_counts, hide_index=True)
    
    with col2:
        # Create a pie chart of selected step types
        import plotly.express as px
        fig = px.pie(
            step_type_counts, 
            values='Count', 
            names='Step Type', 
            title='Selected Steps by Type'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Show the selected steps table
    st.write("已選擇的工步：")
    display_cols = [
        'step_number', 
        'original_step_type', 
        'step_type', 
        'c_rate_range', 
        'soc_range', 
        'temperature_range',
        'duration'
    ]
    st.dataframe(selected_df[display_cols], hide_index=True, use_container_width=True)


def create_processing_controls():
    """
    Create buttons for pre-processing and database loading.
    
    Returns:
        Tuple containing:
        - Boolean indicating if pre-process button was clicked
        - Boolean indicating if load to DB button was clicked
    """
    st.subheader("Processing Controls")
    
    col1, col2 = st.columns(2)
    
    with col1:
        preprocess_clicked = st.button(
            "Pre-process Selected Steps",
            type="primary",
            use_container_width=True,
            disabled=(st.session_state.full_discharge_step_idx is None)
        )
        
        if st.session_state.full_discharge_step_idx is None:
            st.info("Select a reference discharge step to enable pre-processing.")
    
    with col2:
        load_db_clicked = st.button(
            "Load to Database",
            type="secondary",
            use_container_width=True,
            disabled=(len(st.session_state.selected_steps_for_db) == 0 or st.session_state.steps_df_with_soc is None)
        )
        
        if len(st.session_state.selected_steps_for_db) == 0:
            st.info("Select steps for database loading.")
        elif st.session_state.steps_df_with_soc is None:
            st.info("Pre-process steps before loading to database.")
    
    return preprocess_clicked, load_db_clicked


def validate_step_selections() -> bool:
    """
    Validate that the step selections meet requirements.
    
    Returns:
        Boolean indicating if selections are valid
    """
    # Check if a reference step is selected for discharge
    if st.session_state.full_discharge_step_idx is None:
        st.warning("Please select a reference discharge step for SOC calculation.")
        return False
    
    # Check if steps are selected for DB loading
    if not st.session_state.selected_steps_for_db:
        st.warning("Please select at least one step for database loading.")
        return False
    
    return True


def get_current_selections() -> Dict[str, Any]:
    """
    Get the current step selections from session state.
    
    Returns:
        Dictionary containing current selections
    """
    return {
        'full_discharge_step_idx': st.session_state.full_discharge_step_idx,
        'selected_steps_for_db': st.session_state.selected_steps_for_db,
        'steps_df_with_soc': st.session_state.steps_df_with_soc,
        'details_df_with_soc': st.session_state.details_df_with_soc,
        'filtered_step_types': st.session_state.filtered_step_types
    }


def persist_selections():
    """
    Save current selections to session state.
    """
    # Already using session state for persistence
    pass


def restore_selections() -> Dict[str, Any]:
    """
    Restore selections from session state.
    
    Returns:
        Dictionary containing restored selections
    """
    # Initialize session state if needed
    init_step_selection_state()
    
    # Return current selections
    return get_current_selections()


def render_step_selection_page(steps_df: pd.DataFrame, details_df: pd.DataFrame):
    """
    Render the step selection page UI.
    
    Args:
        steps_df: DataFrame containing step data
        details_df: DataFrame containing detailed measurement data
    """
    st.header("Step Selection and Processing")
    
    # Display info about loaded data
    st.info(f"Processing {len(steps_df)} steps and {len(details_df)} detail measurements.")
    
    # Initialize session state if needed
    init_step_selection_state()
    
    # Display the steps table and get selections
    filtered_df, selected_reference_idx, selected_db_indices = display_steps_table(steps_df)
    
    # Add an update button after the selection with explanatory text
    st.info("Make your selections above and click 'Update' to apply changes. Changes won't take effect until you click Update.")
    update_col1, update_col2 = st.columns([3, 1])
    with update_col2:
        update_clicked = st.button("Update Selections", type="primary", key="update_button", use_container_width=True)
    
    # Apply updates when the button is clicked
    if update_clicked:
        # Update the full discharge step index from the temporary storage
        st.session_state.full_discharge_step_idx = st.session_state.temp_reference_step_idx
        
        # Update the selected steps for DB from temporary storage
        st.session_state.selected_steps_for_db = st.session_state.temp_selected_steps_for_db
        
        # Store the current steps_df for SOC calculations
        st.session_state.current_steps_df = steps_df
        
        # Calculate SOC with the updated reference step
        if st.session_state.full_discharge_step_idx is not None or not st.session_state.filtered_step_types:
            steps_with_soc, details_with_soc = handle_reference_step_selection(
                steps_df, 
                details_df,
                full_discharge_step_idx=st.session_state.full_discharge_step_idx
            )
            
            # Update the steps_df with SOC values to display in the table
            steps_df = steps_with_soc
            
            # Reset the update needed flag
            st.session_state.update_needed = False
            
            # Force a rerun to update the UI with new values
            st.rerun()
    
    # Display warning if update is needed but not applied
    if st.session_state.update_needed:
        st.warning("You have made selections that require an update. Click the Update button to apply changes.")
    
    # Display overview of selected steps
    display_selected_steps_overview(filtered_df, selected_db_indices)
    
    # Create processing controls
    preprocess_clicked, load_db_clicked = create_processing_controls()
    
    # Handle pre-processing button click
    if preprocess_clicked:
        if st.session_state.full_discharge_step_idx is not None or not st.session_state.filtered_step_types:
            steps_with_soc, details_with_soc = handle_reference_step_selection(
                steps_df, 
                details_df,
                full_discharge_step_idx=st.session_state.full_discharge_step_idx
            )
            
            # Update the steps_df with SOC values
            steps_df = steps_with_soc
            
            # Force a rerun to update the UI with new values
            st.rerun()
    
    # Handle load to DB button click
    if load_db_clicked:
        if validate_step_selections() and st.session_state.steps_df_with_soc is not None:
            # Prepare selected steps data to be used in the experiment info page
            selected_steps = []
            steps_df_with_soc = st.session_state.steps_df_with_soc
            details_df_with_soc = st.session_state.details_df_with_soc
            
            # Create list of step data dictionaries
            for step_idx in st.session_state.selected_steps_for_db:
                step_row = steps_df_with_soc.loc[step_idx].to_dict()
                # Add the step_number explicitly to make it easier to reference
                step_row['step_number'] = int(step_idx)
                selected_steps.append(step_row)
            
            # Store the selected steps and related data in session state for the experiment info page
            st.session_state["selected_steps"] = selected_steps
            st.session_state["selected_steps_details_df"] = details_df_with_soc
            
            # Navigate to the experiment info page
            st.session_state['current_page'] = "Experiment Info"
            st.success("Steps selected and ready for database loading! Redirecting to Experiment Info page...")
            st.rerun()
    
    # Return current selections for use in other components
    return get_current_selections()