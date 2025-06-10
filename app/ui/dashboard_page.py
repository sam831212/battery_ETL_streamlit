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
STEP_DF_COLUMNS = ['id', 'experiment_id', 'experiment_name', 'step_number',
                   'step_type', 'start_time', 'end_time', 'duration',
                   'voltage_start', 'voltage_end', 'current', 'capacity',
                   'energy', 'temperature', 'c_rate', 'soc_start', 'soc_end', 'data_meta']
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
                # Use temperature_start if temperature attribute doesn't exist
                temperature = getattr(step, 'temperature', step.temperature_start if hasattr(step, 'temperature_start') else None)
                # 取得 data_meta 欄位，若不存在則為 None
                data_meta = getattr(step, 'data_meta', None)
                
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
                    'temperature': temperature,
                    'c_rate': step.c_rate,
                    'soc_start': step.soc_start,
                    'soc_end': step.soc_end,
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

    preferred_cols = ['name', 'step_number', 'step_type', 'experiment_name']
    checkbox_col = next((col for col in preferred_cols if col in df.columns and col != 'id'), None)
    if not checkbox_col:
        checkbox_col = next((col for col in df.columns if col != 'id'), None)
    
    if checkbox_col:
        gb.configure_column(checkbox_col, checkboxSelection=True)    # Configure columns based on table type and column characteristics
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
            from st_aggrid import JsCode            # 添加 onGridReady 回調來強制調整列寬
            onGridReady = JsCode("""
            function(params) {
                // 自動調整所有列寬以適應內容，不限制最大寬度
                params.columnApi.autoSizeAllColumns(false);
            }
            """)
            

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
        # Ensure y_axis default is valid and different from x_axis if possible
        y_default_index = 0
        if available_y_cols:
            if x_axis and x_axis in available_y_cols and len(available_y_cols) > 1:
                y_default_index = 1 if available_y_cols[0] == x_axis else 0
            # Try to find a different default y_axis
            if x_axis and x_axis == available_y_cols[y_default_index] and len(available_y_cols) > y_default_index +1:
                 y_default_index +=1
            elif x_axis and x_axis == available_y_cols[y_default_index] and y_default_index > 0:
                 y_default_index -=1


        y_axis = st.selectbox("Y-axis", available_y_cols, 
                             index=y_default_index if available_y_cols else None, key="step_plot_y_axis")
    
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


def render_detail_plot(selected_step_ids: List[int]):
    """Render the Detail-level time-series plotting area with selectable X and Y axes."""
    st.subheader("Detail-Level Time-Series Visualization")
    
    if not selected_step_ids:
        st.info("Select steps to enable time-series plotting")
        return
    
    measurements_df = get_measurements_for_steps(selected_step_ids)
    
    if measurements_df.empty:
        st.warning("No measurement data available for selected steps or an error occurred.")
        return
    
    # 取得 step_id 對應的 data_meta
    steps_meta_map = {}
    try:
        all_steps_df = get_steps_data()
        if 'data_meta' in all_steps_df.columns:
            steps_meta_map = dict(zip(all_steps_df['id'], all_steps_df['data_meta']))
    except Exception:
        steps_meta_map = {}
    
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

    # Y-axis candidates should be numeric and different from the selected X-axis
    y_axis_candidate_cols = [col for col in numeric_cols_for_x if col != x_axis_detail]

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
                    else:
                        print(f"DEBUG: Invalid ID type in dict: {row_id} ({type(row_id)})")
                else:
                    print(f"DEBUG: No 'id' key in dict row: {list(row.keys())}")
            
            # Case 2: Row is a list/tuple (values in column order)
            elif isinstance(row, (list, tuple)):
                if len(row) > 0:
                    # Assume first column is ID
                    potential_id = row[0]
                    if isinstance(potential_id, (int, float)):
                        selected_ids.append(int(potential_id))
                    elif isinstance(potential_id, str) and potential_id.isdigit():
                        selected_ids.append(int(potential_id))
                    else:
                        print(f"DEBUG: Invalid ID in list: {potential_id} ({type(potential_id)})")
                else:
                    print(f"DEBUG: Empty list/tuple row")
            
            # Case 3: Row is a single value (might be an ID)
            elif isinstance(row, (int, float)):
                selected_ids.append(int(row))
            
            elif isinstance(row, str):
                if row.isdigit():
                    selected_ids.append(int(row))
                else:
                    print(f"DEBUG: Non-numeric string value: {row}")
            
            else:
                print(f"DEBUG: Unhandled row type: {type(row)}, value: {row}")
                
        except Exception as e:
            print(f"DEBUG: Error processing row {i}: {e}, row: {row}")
            continue
    
    return selected_ids


def render_dashboard_page():
    """Main function to render the dashboard page"""
    st.title("Battery ETL Dashboard")
    st.markdown("Explore and visualize battery test data across projects, experiments, and steps.")
    
    # Initialize session state
    init_session_state()
    
    # DEBUG: Print session state
    print("=== DEBUG: Session State ===")
    print(f"selected_projects: {st.session_state.selected_projects}")
    print(f"selected_experiments: {st.session_state.selected_experiments}")
    print(f"selected_steps: {st.session_state.selected_steps}")
    print(f"dashboard_filters: {st.session_state.dashboard_filters}")
    print("=" * 30)
    
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
        st.subheader("Experiments")
        print(f"DEBUG: Getting experiments for project IDs: {st.session_state.selected_projects}")
        experiments_df = get_experiments_data(st.session_state.selected_projects)
        print(f"DEBUG: Experiments before filter: {len(experiments_df)} rows")
        print(f"DEBUG: Experiments columns: {experiments_df.columns.tolist() if not experiments_df.empty else 'Empty'}")
        experiments_df = apply_filters(experiments_df, "experiments")
        print(f"DEBUG: Experiments after filter: {len(experiments_df)} rows")
        if not experiments_df.empty:
            experiment_response = create_interactive_table(experiments_df, "Experiments")
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
        print(f"DEBUG: Getting steps for experiment IDs: {st.session_state.selected_experiments}")
        steps_df = get_steps_data(st.session_state.selected_experiments)
        print(f"DEBUG: Steps before filter: {len(steps_df)} rows")
        print(f"DEBUG: Steps columns: {steps_df.columns.tolist() if not steps_df.empty else 'Empty'}")
        steps_df = apply_filters(steps_df, "steps")
        print(f"DEBUG: Steps after filter: {len(steps_df)} rows")
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
    
    # Plotting Areas
    st.header("Data Visualization")
    
    # Step-level plotting
    if not selected_steps_df.empty:
        render_step_plot(selected_steps_df)
    else:
        st.info("Select steps to enable Step-level plotting")
    
    st.divider()
    
    # Detail-level plotting
    if selected_step_ids:
        render_detail_plot(selected_step_ids)
    else:
        st.info("Select steps to enable Detail-level time-series plotting")
    
    # Summary information
    st.sidebar.header("Selection Summary")
    st.sidebar.write(f"**Projects selected:** {len(st.session_state.selected_projects)}")
    st.sidebar.write(f"**Experiments selected:** {len(st.session_state.selected_experiments)}")
    st.sidebar.write(f"**Steps selected:** {len(st.session_state.selected_steps)}")
    
    # Data export option
    if selected_step_ids:
        st.sidebar.header("Data Export")
        if st.sidebar.button("Export Selected Steps"):
            csv = selected_steps_df.to_csv(index=False)
            st.sidebar.download_button(
                label="Download CSV",
                data=csv,
                file_name="selected_steps.csv",
                mime="text/csv"            )


def _configure_table_columns(gb: GridOptionsBuilder, df: pd.DataFrame, table_name: str):
    """Configure table columns with appropriate settings for different table types"""
      # Define column categories
    date_columns = ['start_date', 'end_date', 'start_time', 'end_time']
    numeric_columns = [
        'duration', 'voltage_start', 'voltage_end', 'current', 'capacity', 
        'energy', 'temperature', 'c_rate', 'soc_start', 'soc_end', 'nominal_capacity'
    ]    # Special handling for Steps table - force auto-width for all columns
    if table_name == "Steps":
        for col_name in df.columns:
            # 簡化配置，專注於列寬自動調整
            config = {}  # 使用空字典，讓它自動推斷類型
            config['resizable'] = True
            config['sortable'] = True
            config['suppressSizeToFit'] = False
            
            # Apply column type-specific settings for Steps
            if col_name == 'id':
                config['editable'] = False
                config['pinned'] = 'left'
                config['flex'] = 0.5  # Make ID column smaller
            elif col_name in date_columns:
                config['type'] = ["dateColumnFilter", "customDateTimeFormat"]
                config['custom_format_string'] = 'dd/MM/yyyy HH:mm'
            elif col_name in numeric_columns:
                config['type'] = ["numericColumn", "numberColumnFilter", "customNumericFormat"]
                config['precision'] = 3
            
            gb.configure_column(col_name, **config)
        return  # Early return for Steps table
    
    # Table-specific width strategies for other tables
    table_width_config = {
        'Projects': {
            'id': {'width': 40, 'pinned': 'left'},
            'name': {'autoWidth': True, 'minWidth': 120},
            'description': {'autoWidth': True, 'minWidth': 200},
            'default': {'autoWidth': True}
        },
        'Experiments': {
            'id': {'width': 40, 'pinned': 'left'},
            'name': {'autoWidth': True, 'minWidth': 120},
            'project_name': {'autoWidth': True, 'minWidth': 100},
            'battery_type': {'autoWidth': True, 'minWidth': 80},
            'default': {'autoWidth': True}
        },        'Steps': {
            # Steps 表格專門配置：移除所有固定寬度設置，強制使用自動寬度
            'default': {
                'autoWidth': True, 
                'flex': 1,
                'resizable': True,
                'sortable': True,
                'suppressSizeToFit': False
            }
        }
    }
    
    # Get width config for current table
    width_config = table_width_config.get(table_name, {'default': {'autoWidth': True}})
    
    for col_name in df.columns:
        base_config = {}
        
        # Apply column-specific width settings
        if col_name in width_config:
            base_config.update(width_config[col_name])
        else:
            base_config.update(width_config.get('default', {'autoWidth': True}))
        
        # Apply column type-specific settings
        if col_name == 'id':
            base_config.update({
                'editable': False,
                'width': base_config.get('width', 40),
                'pinned': base_config.get('pinned', 'left')
            })
        elif col_name in date_columns:
            base_config.update({
                'type': ["dateColumnFilter", "customDateTimeFormat"],
                'custom_format_string': 'dd/MM/yyyy HH:mm'
            })
        elif col_name in numeric_columns:
            base_config.update({
                'type': ["numericColumn", "numberColumnFilter", "customNumericFormat"],
                'precision': 3
            })
        
        # Configure the column
        gb.configure_column(col_name, **base_config)


if __name__ == "__main__":
    render_dashboard_page()

