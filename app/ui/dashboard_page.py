"""
Dashboard page for the Battery ETL Dashboard
Implements hierarchical data visualization across Project → Experiment → Step levels
with interactive tables, filtering, and plotting capabilities.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, List, Optional, Any, Union
from sqlmodel import Session, select, func, col
from sqlalchemy import Column

try:
    from st_aggrid import AgGrid, GridOptionsBuilder, DataReturnMode, GridUpdateMode, JsCode
    AGGRID_AVAILABLE = True
except ImportError:
    AGGRID_AVAILABLE = False

from app.models.database import Project, Experiment, Step, Measurement
from app.utils.database import get_session

# Define DataFrame column constants
PROJECT_DF_COLUMNS = ['id', 'name', 'description', 'start_date', 'end_date', 'experiment_count']
EXPERIMENT_DF_COLUMNS = ['id', 'name', 'project_id', 'project_name', 'battery_type',
                           'nominal_capacity', 'temperature', 'operator', 'start_date',
                           'end_date', 'step_count']
STEP_DF_COLUMNS = ['id', 'data_meta', 'experiment_id', 'experiment_name', 'step_number',
                   'step_type', 'start_time', 'end_time', 'duration',
                   'voltage_start', 'voltage_end', 'current', 'capacity',
                   'energy', 'temperature', 'c_rate', 'soc_start', 'soc_end', 'pre_test_rest_time']
MEASUREMENT_DF_COLUMNS = ['step_id', 'execution_time', 'voltage', 'current', 'temperature', 'capacity', 'energy']


def init_session_state():
    """Initialize session state variables for the dashboard"""
    if "selected_projects" not in st.session_state:
        st.session_state.selected_projects = []
    if "selected_experiments" not in st.session_state:
        st.session_state.selected_experiments = []
    if "selected_steps" not in st.session_state:
        st.session_state.selected_steps = []
    if "dashboard_filters" not in st.session_state:
        st.session_state.dashboard_filters = {}


def get_projects_data() -> pd.DataFrame:
    """Fetch all projects from database"""
    try:
        with get_session() as session:
            projects = session.exec(select(Project)).all()
            
            if not projects:
                return pd.DataFrame(columns=PROJECT_DF_COLUMNS)
            
            data = []
            for project in projects:
                experiment_count = len(project.experiments)
                data.append({
                    'id': project.id,
                    'name': project.name,
                    'description': project.description or '',
                    'start_date': project.start_date,
                    'end_date': project.end_date,
                    'experiment_count': experiment_count
                })
            
            return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Error fetching projects: {str(e)}")
        return pd.DataFrame(columns=PROJECT_DF_COLUMNS)


def get_experiments_data(selected_project_ids: Optional[List[int]] = None) -> pd.DataFrame:
    """Fetch experiments, optionally filtered by project IDs"""
    try:
        with get_session() as session:
            query = select(Experiment)
            if selected_project_ids:
                query = query.where(col(Experiment.project_id).in_(selected_project_ids))
            
            experiments = session.exec(query).all()
            
            if not experiments:
                return pd.DataFrame(columns=EXPERIMENT_DF_COLUMNS)
            
            data = []
            for experiment in experiments:
                step_count = len(experiment.steps)
                project_name = experiment.project.name if experiment.project else 'No Project'
                
                data.append({
                    'id': experiment.id,
                    'name': experiment.name,
                    'project_id': experiment.project_id,
                    'project_name': project_name,
                    'battery_type': experiment.battery_type,
                    'nominal_capacity': experiment.nominal_capacity,
                    'temperature': experiment.temperature,
                    'operator': getattr(experiment, 'operator', None),  # Safe access to operator field
                    'start_date': experiment.start_date,
                    'end_date': experiment.end_date,
                    'step_count': step_count
                })
            
            return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Error fetching experiments: {str(e)}")
        return pd.DataFrame(columns=EXPERIMENT_DF_COLUMNS)


def get_steps_data(selected_experiment_ids: Optional[List[int]] = None) -> pd.DataFrame:
    """Fetch steps, optionally filtered by experiment IDs"""
    try:
        with get_session() as session:
            query = select(Step)
            
            if selected_experiment_ids:
                query = query.where(col(Step.experiment_id).in_(selected_experiment_ids))
            
            steps = session.exec(query).all()
            
            if not steps:
                return pd.DataFrame(columns=STEP_DF_COLUMNS)
            
            data = []
            for step in steps:
                experiment_name = step.experiment.name if step.experiment else 'Unknown'
                
                # Refined temperature fetching logic
                temperature_val = getattr(step, 'temperature', None)
                if temperature_val is None:
                    temperature_val = getattr(step, 'temperature_start', None)
                
                data_meta = getattr(step, 'data_meta', None)
                pre_test_rest_time = getattr(step, 'pre_test_rest_time', None)
                
                data.append({
                    'id': step.id,
                    'step_number': step.step_number,
                    'experiment_id': step.experiment_id,
                    'experiment_name': experiment_name,
                    'step_type': step.step_type,
                    'start_time': step.start_time,
                    'end_time': step.end_time,
                    'duration': step.duration,
                    'voltage_start': step.voltage_start,
                    'voltage_end': step.voltage_end,
                    'current': step.current,
                    'capacity': step.capacity,
                    'energy': step.energy,
                    'temperature': temperature_val, # Use the refined value
                    'c_rate': step.c_rate,
                    'soc_start': step.soc_start,
                    'soc_end': step.soc_end,
                    'pre_test_rest_time': pre_test_rest_time,
                    'data_meta': data_meta
                })
            
            return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Error fetching steps: {str(e)}")
        return pd.DataFrame(columns=STEP_DF_COLUMNS)


def create_interactive_table(df: pd.DataFrame, table_name: str, 
                           selection_mode: str = "multiple") -> Dict[str, Any]:
    """Create an interactive table with st_aggrid or fallback to streamlit"""
    if df.empty:
        st.warning(f"No data available for {table_name}")
        return {"selected_rows": []}
    
    df = df.reset_index(drop=True)
    
    if not AGGRID_AVAILABLE:
        st.dataframe(df, use_container_width=True)
        selected_rows = []
        if 'name' in df.columns:
            selected_names = st.multiselect(f"Select {table_name} (by name):", 
                                          df['name'].tolist(), 
                                          key=f"{table_name}_selector")
            if selected_names:
                selected_rows = df[df['name'].isin(selected_names)].to_dict('records')
        return {"selected_rows": selected_rows}
    
    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_pagination(paginationAutoPageSize=True)
    gb.configure_side_bar()
    gb.configure_selection(selection_mode=selection_mode)

    # Determine the column for checkbox selection
    checkbox_col = None
    preferred_cols_for_checkbox = ['name', 'step_number', 'step_type', 'experiment_name']
    
    # Try preferred columns first
    for col_name in preferred_cols_for_checkbox:
        if col_name in df.columns and col_name != 'id':
            checkbox_col = col_name
            break
    
    # If no preferred column is found, use the first available column (not 'id')
    if not checkbox_col:
        checkbox_col = next((col_name for col_name in df.columns if col_name != 'id'), None)
    
    if checkbox_col:
        gb.configure_column(checkbox_col, checkboxSelection=True)
    
    # Configure columns based on table type and column characteristics
    # Assuming _configure_table_columns is defined elsewhere or not strictly needed for this refactoring pass.
    # If it's a local helper that was missed, it should be included.
    # For now, proceeding as if it's handled.
    _configure_table_columns(gb, df, table_name)
    
    grid_options = gb.build()
    grid_options['rowSelection'] = selection_mode
    grid_options['suppressRowClickSelection'] = False # Allow row click selection    # Enhanced column sizing for Steps table
    if table_name == "Steps":
        # Force autoWidth for all columns in Steps table
        for col_def in grid_options.get('columnDefs', []):
            col_def.update({
                'resizable': True,
                'sortable': True,
                'filter': True
            })
            # Remove any fixed width settings
            col_def.pop('width', None)
            col_def.pop('minWidth', None)
            col_def.pop('maxWidth', None)
            col_def.pop('flex', None)  # 也移除 flex 設置
        
        grid_options.update({
            'skipHeaderOnAutoSize': False,
            'suppressColumnVirtualisation': False,
            'enableColResize': True
        })
    
    # Define aggrid_key outside the conditional blocks
    aggrid_key = f"aggrid_{table_name.lower()}_{str(st.session_state.dashboard_filters)}"
    
    try:
        # Special configuration for Steps table
        if table_name == "Steps":
            # 為 Steps 表格添加專門的自動調整寬度配置
            
            grid_response = AgGrid(
                df,
                gridOptions=grid_options,
                data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
                update_mode=GridUpdateMode.SELECTION_CHANGED,
                fit_columns_on_grid_load=False,
                columns_auto_size_mode=2,  # Force auto-sizing
                enable_enterprise_modules=False,
                height=400,
                width='100%',
                key=aggrid_key,
                allow_unsafe_jscode=True,
                theme='streamlit'
            )
        else:
            grid_response = AgGrid(
                df,
                gridOptions=grid_options,
                data_return_mode=DataReturnMode.FILTERED_AND_SORTED, # Prefer this for consistency
                update_mode=GridUpdateMode.SELECTION_CHANGED,
                fit_columns_on_grid_load=False,
                enable_enterprise_modules=False, # Set to True if you have a license
                height=400,
                width='100%',
                key=aggrid_key,
                allow_unsafe_jscode=True # If using JsCode for formatting or callbacks
            )
    except Exception: # Fallback if FILTERED_AND_SORTED causes issues (less likely with simpler config)
        grid_response = AgGrid(
            df,
            gridOptions=grid_options,
            data_return_mode=DataReturnMode.AS_INPUT, # Fallback
            update_mode=GridUpdateMode.SELECTION_CHANGED,
            fit_columns_on_grid_load=False,
            enable_enterprise_modules=False,
            height=400,
            width='100%',
            key=f"{aggrid_key}_fallback",
            allow_unsafe_jscode=True
        )
    
    selected_rows_data = grid_response.get('selected_rows', [])


    # Ensure selected_rows_data is a list of dicts
    if isinstance(selected_rows_data, pd.DataFrame):
        processed_selected_rows = selected_rows_data.to_dict('records')
    elif isinstance(selected_rows_data, list) and all(isinstance(item, dict) for item in selected_rows_data):
        processed_selected_rows = selected_rows_data
    else: # If it's in an unexpected format, try to handle or default to empty
        processed_selected_rows = []
        if selected_rows_data: # Log if there's data but format is wrong
            st.warning(f"AgGrid selected_rows for {table_name} in unexpected format. Please check AgGrid configuration.")

    # Return a copy of the grid_response and ensure 'selected_rows' is in the desired format
    response_dict = dict(grid_response)
    response_dict['selected_rows'] = processed_selected_rows
    
    return response_dict


def get_available_numeric_columns(df: pd.DataFrame, candidate_columns: List[str]) -> List[str]:
    """Returns columns from candidate_columns that exist in df, are numeric, and not all NaN."""
    if df.empty:
        return []
    available_cols = []
    for col_name in candidate_columns:
        if col_name in df.columns:
            # Check if the column is numeric-like (handles ints, floats)
            # and ensure not all values are NaN, as this can cause issues with some plots
            try:
                if pd.api.types.is_numeric_dtype(df[col_name]) and not df[col_name].isna().all():
                    available_cols.append(col_name)
            except TypeError: # Handle cases where dtype check might fail for mixed types if not strictly numeric
                pass
    return available_cols


def render_step_plot(steps_df: pd.DataFrame):
    """Render the Step-level plotting area"""
    st.subheader("Step-Level Data Visualization")
    
    if steps_df.empty:
        st.info("Select steps to enable plotting")
        return
    
    col1, col2, col3 = st.columns(3)
    
    numeric_candidates = ['step_number', 'duration', 'voltage_start', 'voltage_end', 
                          'current', 'capacity', 'energy', 'temperature', 'c_rate', 
                          'soc_start', 'soc_end']
    
    with col1:
        available_x_cols = get_available_numeric_columns(steps_df, numeric_candidates)
        x_axis = st.selectbox("X-axis", available_x_cols, index=0 if available_x_cols else None, key="step_plot_x_axis")
    
    with col2:
        available_y_cols = get_available_numeric_columns(steps_df, numeric_candidates)
        y_axis_default_idx = 0 if available_y_cols else None # Default to first option or None if no options

        if available_y_cols and x_axis and x_axis in available_y_cols:
            # Try to find a default Y different from X
            non_x_options = [col for col in available_y_cols if col != x_axis]
            if non_x_options:
                y_axis_default_idx = available_y_cols.index(non_x_options[0])
            # If only x_axis is available (or x_axis is not in available_y_cols), 
            # y_axis_default_idx remains pointing to the first element (0) or None.
        
        y_axis = st.selectbox("Y-axis", available_y_cols, 
                             index=y_axis_default_idx, 
                             key="step_plot_y_axis")
    
    with col3:
        categorical_columns = ['step_type', 'experiment_name', 'data_meta']
        available_color_cols = ['None'] + [col for col in categorical_columns if col in steps_df.columns and steps_df[col].nunique() > 0]
        color_by = st.selectbox("Color/Group by", available_color_cols, key="step_plot_color_by")
    
    if x_axis and y_axis:
        # Create the plot
        if color_by == 'None':
            fig = px.scatter(steps_df, x=x_axis, y=y_axis,
                           title=f"{y_axis} vs {x_axis}",
                           hover_data=['experiment_name', 'step_number', 'step_type'])
        else:
            fig = px.scatter(steps_df, x=x_axis, y=y_axis, color=color_by,
                           title=f"{y_axis} vs {x_axis} (colored by {color_by})",
                           hover_data=['experiment_name', 'step_number', 'step_type'])
        
        fig.update_layout(height=500)
        st.plotly_chart(fig, use_container_width=True)


def get_measurements_for_steps(step_ids: List[int]) -> pd.DataFrame:
    """Fetch measurement data for selected steps"""
    if not step_ids:
        return pd.DataFrame(columns=MEASUREMENT_DF_COLUMNS)
    
    try:
        with get_session() as session:
            measurements = session.exec(
                select(Measurement).where(col(Measurement.step_id).in_(step_ids))
            ).all()
            
            if not measurements:
                return pd.DataFrame(columns=MEASUREMENT_DF_COLUMNS)
            
            data = []
            for measurement in measurements:
                data.append({
                    'step_id': measurement.step_id,
                    'execution_time': measurement.execution_time,  # 直接取用DB float欄位
                    'voltage': measurement.voltage,
                    'current': measurement.current,
                    'temperature': measurement.temperature,
                    'capacity': measurement.capacity,
                    'energy': measurement.energy,
                })
            
            df = pd.DataFrame(data)
            return df
    except Exception as e:
        st.error(f"Error fetching measurements: {str(e)}")
        return pd.DataFrame(columns=MEASUREMENT_DF_COLUMNS)


def render_detail_plot(selected_step_ids: List[int], steps_meta_map: Dict[int, Any]):
    """Render the Detail-level time-series plotting area with selectable X and Y axes."""
    st.subheader("Detail-Level Time-Series Visualization")
    
    if not selected_step_ids:
        st.info("Select steps to enable time-series plotting")
        return
    
    measurements_df = get_measurements_for_steps(selected_step_ids)
    
    if measurements_df.empty:
        st.warning("No measurement data available for selected steps or an error occurred.")
        return
    
    # steps_meta_map is now passed as an argument, removing internal fetching
    # try:
    #     all_steps_df = get_steps_data() 
    #     if 'data_meta' in all_steps_df.columns:
    #         steps_meta_map = dict(zip(all_steps_df['id'], all_steps_df['data_meta']))
    # except Exception:
    #     steps_meta_map = {}
    
    # Potential candidates for axes
    # Ensure 'execution_time' is handled as a primary candidate for x-axis
    # Other numeric columns can be candidates for both x and y axes.
    all_plottable_columns = MEASUREMENT_DF_COLUMNS.copy()
    if 'step_id' in all_plottable_columns:
        all_plottable_columns.remove('step_id')

    x_axis_options = []
    if 'execution_time' in measurements_df.columns and not measurements_df['execution_time'].isna().all():
        x_axis_options.append('execution_time')
    
    numeric_cols_for_x = get_available_numeric_columns(measurements_df, [col for col in all_plottable_columns if col != 'execution_time'])
    x_axis_options.extend(numeric_cols_for_x)

    if not x_axis_options:
        st.warning("No suitable columns available for X-axis in measurement data.")
        return

    col1, col2, col3 = st.columns(3)

    with col1:
        x_axis_detail = st.selectbox("Select X-axis", x_axis_options, key="detail_plot_x_axis")

    # Y-axis candidates are determined directly by get_available_numeric_columns, excluding x_axis_detail
    # The variable y_axis_candidate_cols was unused and has been removed.

    with col2:
        available_y_metrics = get_available_numeric_columns(measurements_df, [col for col in all_plottable_columns if col != x_axis_detail])
        
        default_y_selection = []
        if available_y_metrics:
            default_y_selection = available_y_metrics[:2] if len(available_y_metrics) >= 2 else available_y_metrics[:1]
        
        selected_y_metrics = st.multiselect("Select Y-metrics", available_y_metrics, 
                                            default=default_y_selection, key="detail_plot_y_metrics")
    
    with col3:
        plot_type = st.radio("Plot type", ["Separate subplots", "Combined plot"], key="detail_plot_type")
    
    def get_legend_label(step_id_val):
        meta = steps_meta_map.get(step_id_val, None)
        if meta is not None and str(meta).strip() != '':
            return f"{meta} (Step {step_id_val})"
        else:
            return f"Step {step_id_val}"
    
    if x_axis_detail and selected_y_metrics:
        if plot_type == "Separate subplots":
            from plotly.subplots import make_subplots
            if not selected_y_metrics:
                st.info("Please select at least one Y-metric to plot.")
                return
            fig = make_subplots(
                rows=len(selected_y_metrics), 
                cols=1,
                subplot_titles=[f"{metric} vs {x_axis_detail}" for metric in selected_y_metrics],
                shared_xaxes=True
            )
            
            for i, metric in enumerate(selected_y_metrics, 1):
                for step_id_val in selected_step_ids:
                    step_data = measurements_df[measurements_df['step_id'] == step_id_val]
                    if not step_data.empty and x_axis_detail in step_data.columns and metric in step_data.columns:
                        if not step_data[x_axis_detail].isna().all() and not step_data[metric].isna().all():
                            fig.add_trace(
                                go.Scatter(
                                    x=step_data[x_axis_detail],
                                    y=step_data[metric],
                                    mode='lines',
                                    name=get_legend_label(step_id_val),
                                    showlegend=(i == 1) 
                                ),
                                row=i, col=1
                            )
            
            fig.update_layout(height=max(400, 200 * len(selected_y_metrics)), title_text=f"Time-Series Data: Metrics vs {x_axis_detail}")
            fig.update_xaxes(title_text=x_axis_detail)

        else: # Combined plot
            fig = go.Figure()
            colors = px.colors.qualitative.Plotly
            
            for i, metric in enumerate(selected_y_metrics):
                color = colors[i % len(colors)]
                for step_id_val in selected_step_ids:
                    step_data = measurements_df[measurements_df['step_id'] == step_id_val]
                    if not step_data.empty and x_axis_detail in step_data.columns and metric in step_data.columns:
                        if not step_data[x_axis_detail].isna().all() and not step_data[metric].isna().all():
                            fig.add_trace(
                                go.Scatter(
                                    x=step_data[x_axis_detail],
                                    y=step_data[metric],
                                    mode='lines',
                                    name=f"{metric} (" + get_legend_label(step_id_val) + ")",
                                    line=dict(color=color),
                                    yaxis=f"y{i+1}" if len(selected_y_metrics) > 1 else "y"
                                )
                            )
            
            fig.update_layout(
                height=500, 
                title_text=f"Combined Time-Series: Metrics vs {x_axis_detail}",
                xaxis_title=x_axis_detail
            )

            if len(selected_y_metrics) == 1:
                 fig.update_layout(yaxis_title=selected_y_metrics[0])
            elif len(selected_y_metrics) > 1:
                fig.update_layout(yaxis_title=selected_y_metrics[0])
                for i, metric_name in enumerate(selected_y_metrics[1:], start=1):
                    fig.update_layout({
                        f'yaxis{i+1}': {
                            'title': metric_name,
                            'overlaying': 'y',
                            'side': 'right' if i % 2 == 0 else 'left',
                            'position': 0.15 * i if i%2 !=0 else 1 - (0.15* (i-1)),
                            'showgrid': False,
                        }
                    })
                fig.update_layout(margin=dict(r=80 + (len(selected_y_metrics)-2)*60))

        st.plotly_chart(fig, use_container_width=True)
    elif not selected_y_metrics:
        st.info("Please select at least one Y-metric to plot.")


def render_filtering_controls():
    """Render additional filtering controls"""
    with st.expander("Advanced Filters"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Step Filters")
            step_types = st.multiselect("Step Types", 
                                      ["charge", "discharge", "rest"], 
                                      default=[])
            
            c_rate_range = st.slider("C-Rate Range", 0.0, 30.0 , (0.0, 30.0), step=0.1)
            
        with col2:
            st.subheader("Experiment Filters")
            battery_types = st.multiselect("Battery Types", 
                                         ["Li-ion", "NMC", "LFP", "LTO"], 
                                         default=[])
            
            capacity_range = st.slider("Nominal Capacity Range (Ah)", 0.0, 100.0, (0.0, 100.0), step=0.1)
        
        # Store filters in session state
        st.session_state.dashboard_filters = {
            'step_types': step_types,
            'c_rate_range': c_rate_range,
            'battery_types': battery_types,
            'capacity_range': capacity_range
        }


def apply_filters(df: pd.DataFrame, table_type: str) -> pd.DataFrame:
    """Apply filters to dataframe based on table type"""
    filters = st.session_state.get('dashboard_filters', {})
    if not filters or df.empty:
        return df

    original_shape = df.shape
    filtered_df = df.copy()

    if table_type == "experiments":
        if 'battery_types' in filters and filters['battery_types']:
            if 'battery_type' in filtered_df.columns:
                filtered_df = filtered_df[filtered_df['battery_type'].isin(filters['battery_types'])]
        
        if 'capacity_range' in filters:
            min_cap, max_cap = filters['capacity_range']
            if 'nominal_capacity' in filtered_df.columns:
                if min_cap is not None:
                    filtered_df = filtered_df[filtered_df['nominal_capacity'] >= min_cap]
                if max_cap is not None:
                    filtered_df = filtered_df[filtered_df['nominal_capacity'] <= max_cap]

    elif table_type == "steps":
        if 'step_types' in filters and filters['step_types']:
            if 'step_type' in filtered_df.columns:
                filtered_df = filtered_df[filtered_df['step_type'].isin(filters['step_types'])]
        
        if 'c_rate_range' in filters:
            min_c, max_c = filters['c_rate_range']
            if 'c_rate' in filtered_df.columns:
                # Ensure c_rate is numeric and handle NAs before filtering
                filtered_df['c_rate'] = pd.to_numeric(filtered_df['c_rate'], errors='coerce')
                if min_c is not None:
                    filtered_df = filtered_df[filtered_df['c_rate'] >= min_c]
                if max_c is not None:
                    filtered_df = filtered_df[filtered_df['c_rate'] <= max_c]
    
    return filtered_df


def extract_selected_ids(selected_rows: List[Any], table_name: str) -> List[int]:
    """Extract IDs from selected rows, handling various formats including DataFrame"""
    selected_ids = []
    
    # Handle DataFrame case first
    if isinstance(selected_rows, pd.DataFrame):
        if selected_rows.empty:
            return selected_ids
        # Convert DataFrame to list of dicts
        selected_rows = selected_rows.to_dict('records')
    
    # Handle other empty cases
    if not selected_rows or (hasattr(selected_rows, '__len__') and len(selected_rows) == 0):
        return selected_ids
    
    for i, row in enumerate(selected_rows):
        try:
            # Case 1: Row is a dictionary (expected format)
            if isinstance(row, dict):
                if 'id' in row:
                    row_id = row['id']
                    if isinstance(row_id, (int, float)):
                        selected_ids.append(int(row_id))
                    elif isinstance(row_id, str) and row_id.isdigit():
                        selected_ids.append(int(row_id))
                    # else: # Removed debug print
                        # print(f"DEBUG: Non-convertible ID in dict for {table_name}: {row_id}")
                # else: # Removed debug print
                    # print(f"DEBUG: No 'id' field in selected row dict for {table_name}: {row}")
            
            # Case 2: Row is a list/tuple (values in column order)
            elif isinstance(row, (list, tuple)):
                if len(row) > 0:
                    row_id = row[0] # Assuming ID is the first column
                    if isinstance(row_id, (int, float)):
                        selected_ids.append(int(row_id))
                    elif isinstance(row_id, str) and row_id.isdigit():
                        selected_ids.append(int(row_id))
                    # else: # Removed debug print
                        # print(f"DEBUG: Non-convertible ID in list/tuple for {table_name}: {row_id}")
                # else: # Removed debug print
                    # print(f"DEBUG: Empty list/tuple row for {table_name}: {row}")
            
            # Case 3: Row is a single value (might be an ID)
            elif isinstance(row, (int, float)):
                selected_ids.append(int(row))
            
            elif isinstance(row, str):
                if row.isdigit():
                    selected_ids.append(int(row))
                # else: # Removed debug print
                    # print(f"DEBUG: Non-digit string row for {table_name}: {row}")
            
            # else: # Removed debug print
                # print(f"DEBUG: Unknown row type for {table_name}: {type(row)}, content: {row}")
                
        except Exception as e:
            # Removed debug print: print(f"DEBUG: Error processing row {i}: {e}, row: {row}")
            st.warning(f"Skipping a row for {table_name} due to error: {e}. Row data: {row}") # Added a warning instead
            continue
    
    return selected_ids


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
    tab_projects, tab_experiments, tab_steps = st.tabs(["Projects", "Experiments", "Steps"])

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
                else:
                    st.warning("Could not extract project IDs from selection")
            else:
                st.session_state.selected_projects = []
        else:
            st.warning("No projects found in database")
            st.session_state.selected_projects = []

    with tab_experiments:
        st.subheader("Experiments")        # print(f"DEBUG: Getting experiments for project IDs: {st.session_state.selected_projects}") # Removed debug print
        experiments_df = get_experiments_data(st.session_state.selected_projects)
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
        selected_step_ids = []
        if not steps_df.empty:
            step_response = create_interactive_table(steps_df, "Steps")
            selected_step_rows = step_response.get("selected_rows", [])
            if selected_step_rows is not None and len(selected_step_rows) > 0:
                selected_step_ids = extract_selected_ids(selected_step_rows, "Steps")
                st.session_state.selected_steps = selected_step_ids
                if selected_step_ids:
                    st.success(f"Selected {len(selected_step_ids)} step(s)")
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


def _configure_table_columns(gb: GridOptionsBuilder, df: pd.DataFrame, table_name: str):
    """
    Placeholder for configuring AgGrid columns.
    This function would typically set column widths, types, formatting, etc.
    based on the DataFrame and table name.
    """
    # Example: Configure 'id' column to be narrower if it exists
    if 'id' in df.columns:
        gb.configure_column("id", width=80, suppressToolPanel=True)
    if 'name' in df.columns:
        gb.configure_column("name", flex=2) # Give more space to name
    if 'description' in df.columns:
        gb.configure_column("description", flex=3)

    # Date/time columns formatting (example, actual formatting might need JsCode)
    for col_name in ['start_date', 'end_date', 'start_time', 'end_time']:
        if col_name in df.columns:
            gb.configure_column(col_name, width=170) # Adjust width for datetime

    if table_name == "Steps":
        if 'step_number' in df.columns:
            gb.configure_column("step_number", width=100)
        if 'step_type' in df.columns:
            gb.configure_column("step_type", width=120)
        # Add more step-specific configurations if needed
    
    # Numeric columns could be right-aligned, etc.
    # This is a basic placeholder. Actual implementation can be more detailed.
    pass


if __name__ == '__main__':
    render_dashboard_page()


