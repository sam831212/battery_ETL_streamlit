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
                return pd.DataFrame(columns=['id', 'name', 'description', 'start_date', 'end_date', 'experiment_count'])
            
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
        return pd.DataFrame(columns=['id', 'name', 'description', 'start_date', 'end_date', 'experiment_count'])


def get_experiments_data(selected_project_ids: Optional[List[int]] = None) -> pd.DataFrame:
    """Fetch experiments, optionally filtered by project IDs"""
    try:
        with get_session() as session:
            query = select(Experiment)            if selected_project_ids:
                query = query.where(col(Experiment.project_id).in_(selected_project_ids))
            
            experiments = session.exec(query).all()
            
            if not experiments:
                return pd.DataFrame(columns=['id', 'name', 'project_id', 'project_name', 'battery_type', 
                                           'nominal_capacity', 'temperature', 'operator', 'start_date', 
                                           'end_date', 'step_count'])
            
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
                    'operator': experiment.operator,
                    'start_date': experiment.start_date,
                    'end_date': experiment.end_date,
                    'step_count': step_count
                })
            
            return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Error fetching experiments: {str(e)}")
        return pd.DataFrame(columns=['id', 'name', 'project_id', 'project_name', 'battery_type', 
                                   'nominal_capacity', 'temperature', 'operator', 'start_date', 
                                   'end_date', 'step_count'])


def get_steps_data(selected_experiment_ids: Optional[List[int]] = None) -> pd.DataFrame:
    """Fetch steps, optionally filtered by experiment IDs"""
    try:
        with get_session() as session:
            query = select(Step)
            
            if selected_experiment_ids:
                query = query.where(Step.experiment_id.in_(selected_experiment_ids))
            
            steps = session.exec(query).all()
            
            if not steps:
                return pd.DataFrame(columns=['id', 'experiment_id', 'experiment_name', 'step_number', 
                                           'step_type', 'start_time', 'end_time', 'duration', 
                                           'voltage_start', 'voltage_end', 'current', 'capacity', 
                                           'energy', 'temperature', 'c_rate', 'soc_start', 'soc_end'])
            
            data = []
            for step in steps:
                experiment_name = step.experiment.name if step.experiment else 'Unknown'
                
                data.append({
                    'id': step.id,
                    'experiment_id': step.experiment_id,
                    'experiment_name': experiment_name,
                    'step_number': step.step_number,
                    'step_type': step.step_type,
                    'start_time': step.start_time,
                    'end_time': step.end_time,
                    'duration': step.duration,
                    'voltage_start': step.voltage_start,
                    'voltage_end': step.voltage_end,
                    'current': step.current,
                    'capacity': step.capacity,
                    'energy': step.energy,
                    'temperature': step.temperature,
                    'c_rate': step.c_rate,
                    'soc_start': step.soc_start,
                    'soc_end': step.soc_end
                })
            
            return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Error fetching steps: {str(e)}")
        return pd.DataFrame(columns=['id', 'experiment_id', 'experiment_name', 'step_number', 
                                   'step_type', 'start_time', 'end_time', 'duration', 
                                   'voltage_start', 'voltage_end', 'current', 'capacity', 
                                   'energy', 'temperature', 'c_rate', 'soc_start', 'soc_end'])


def create_interactive_table(df: pd.DataFrame, table_name: str, 
                           selection_mode: str = "multiple") -> Dict[str, Any]:
    """Create an interactive table with st_aggrid"""
    if df.empty:
        st.warning(f"No data available for {table_name}")
        return {"selected_rows": []}
    
    # Configure grid options
    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_pagination(paginationAutoPageSize=True)
    gb.configure_side_bar()
    gb.configure_selection(selection_mode=selection_mode, use_checkbox=True)
    
    # Configure columns
    for col in df.columns:
        if col in ['id', 'project_id', 'experiment_id']:
            gb.configure_column(col, hide=True)
        elif col in ['start_date', 'end_date', 'start_time', 'end_time']:
            gb.configure_column(col, type=["dateColumnFilter", "customDateTimeFormat"], 
                              custom_format_string='dd/MM/yyyy HH:mm')
        elif col in ['duration', 'voltage_start', 'voltage_end', 'current', 'capacity', 
                     'energy', 'temperature', 'c_rate', 'soc_start', 'soc_end', 'nominal_capacity']:
            gb.configure_column(col, type=["numericColumn", "numberColumnFilter", "customNumericFormat"],
                              precision=3)
    
    grid_options = gb.build()
    
    # Display the grid
    grid_response = AgGrid(
        df,
        gridOptions=grid_options,
        data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
        update_mode=GridUpdateMode.SELECTION_CHANGED,
        fit_columns_on_grid_load=True,
        enable_enterprise_modules=False,
        height=400,
        width='100%'
    )
    
    return grid_response


def render_step_plot(steps_df: pd.DataFrame):
    """Render the Step-level plotting area"""
    st.subheader("Step-Level Data Visualization")
    
    if steps_df.empty:
        st.info("Select steps to enable plotting")
        return
    
    # Plot configuration controls
    col1, col2, col3 = st.columns(3)
    
    with col1:
        numeric_columns = ['step_number', 'duration', 'voltage_start', 'voltage_end', 
                          'current', 'capacity', 'energy', 'temperature', 'c_rate', 
                          'soc_start', 'soc_end']
        available_x_cols = [col for col in numeric_columns if col in steps_df.columns]
        x_axis = st.selectbox("X-axis", available_x_cols, index=0 if available_x_cols else None)
    
    with col2:
        available_y_cols = [col for col in numeric_columns if col in steps_df.columns]
        y_axis = st.selectbox("Y-axis", available_y_cols, 
                             index=1 if len(available_y_cols) > 1 else 0)
    
    with col3:
        categorical_columns = ['step_type', 'experiment_name']
        available_color_cols = ['None'] + [col for col in categorical_columns if col in steps_df.columns]
        color_by = st.selectbox("Color/Group by", available_color_cols)
    
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
        return pd.DataFrame()
    
    try:
        with get_session() as session:
            measurements = session.exec(
                select(Measurement).where(Measurement.step_id.in_(step_ids))
            ).all()
            
            if not measurements:
                return pd.DataFrame()
            
            data = []
            for measurement in measurements:
                data.append({
                    'step_id': measurement.step_id,
                    'timestamp': measurement.timestamp,
                    'voltage': measurement.voltage,
                    'current': measurement.current,
                    'temperature': measurement.temperature,
                    'capacity': measurement.capacity,
                    'energy': measurement.energy,
                    'soc': measurement.soc
                })
            
            return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Error fetching measurements: {str(e)}")
        return pd.DataFrame()


def render_detail_plot(selected_step_ids: List[int]):
    """Render the Detail-level time-series plotting area"""
    st.subheader("Detail-Level Time-Series Visualization")
    
    if not selected_step_ids:
        st.info("Select steps to enable time-series plotting")
        return
    
    measurements_df = get_measurements_for_steps(selected_step_ids)
    
    if measurements_df.empty:
        st.warning("No measurement data available for selected steps")
        return
    
    # Plot configuration
    col1, col2 = st.columns(2)
    
    with col1:
        y_metrics = ['voltage', 'current', 'temperature', 'capacity', 'energy', 'soc']
        available_metrics = [col for col in y_metrics if col in measurements_df.columns]
        selected_metrics = st.multiselect("Select metrics to plot", available_metrics, 
                                        default=available_metrics[:2] if available_metrics else [])
    
    with col2:
        plot_type = st.radio("Plot type", ["Separate subplots", "Combined plot"])
    
    if selected_metrics:
        if plot_type == "Separate subplots":
            # Create subplots
            from plotly.subplots import make_subplots
            
            fig = make_subplots(
                rows=len(selected_metrics), 
                cols=1,
                subplot_titles=selected_metrics,
                shared_xaxes=True
            )
            
            for i, metric in enumerate(selected_metrics, 1):
                for step_id in selected_step_ids:
                    step_data = measurements_df[measurements_df['step_id'] == step_id]
                    if not step_data.empty:
                        fig.add_trace(
                            go.Scatter(
                                x=step_data['timestamp'],
                                y=step_data[metric],
                                mode='lines',
                                name=f"Step {step_id}",
                                showlegend=(i == 1)  # Only show legend for first subplot
                            ),
                            row=i, col=1
                        )
            
            fig.update_layout(height=200 * len(selected_metrics), title="Time-Series Data")
            
        else:
            # Combined plot with secondary y-axis if needed
            fig = go.Figure()
            
            colors = px.colors.qualitative.Set1
            
            for i, metric in enumerate(selected_metrics):
                color = colors[i % len(colors)]
                
                for step_id in selected_step_ids:
                    step_data = measurements_df[measurements_df['step_id'] == step_id]
                    if not step_data.empty:
                        fig.add_trace(
                            go.Scatter(
                                x=step_data['timestamp'],
                                y=step_data[metric],
                                mode='lines',
                                name=f"{metric} - Step {step_id}",
                                line=dict(color=color),
                                yaxis='y2' if i > 0 else 'y'
                            )
                        )
            
            # Configure layout for dual y-axis if multiple metrics
            if len(selected_metrics) > 1:
                fig.update_layout(
                    yaxis=dict(title=selected_metrics[0], side='left'),
                    yaxis2=dict(title=', '.join(selected_metrics[1:]), side='right', overlaying='y')
                )
            
            fig.update_layout(height=500, title="Combined Time-Series Data")
        
        st.plotly_chart(fig, use_container_width=True)


def render_filtering_controls():
    """Render additional filtering controls"""
    with st.expander("Advanced Filters"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Step Filters")
            step_types = st.multiselect("Step Types", 
                                      ["charge", "discharge", "rest"], 
                                      default=[])
            
            c_rate_range = st.slider("C-Rate Range", 0.0, 5.0, (0.0, 5.0), step=0.1)
            
        with col2:
            st.subheader("Experiment Filters")
            battery_types = st.multiselect("Battery Types", 
                                         ["Li-ion", "NMC", "LFP", "LTO"], 
                                         default=[])
            
            capacity_range = st.slider("Nominal Capacity Range (Ah)", 0.0, 10.0, (0.0, 10.0), step=0.1)
        
        # Store filters in session state
        st.session_state.dashboard_filters = {
            'step_types': step_types,
            'c_rate_range': c_rate_range,
            'battery_types': battery_types,
            'capacity_range': capacity_range
        }


def apply_filters(df: pd.DataFrame, table_type: str) -> pd.DataFrame:
    """Apply filters to dataframe based on table type"""
    filters = st.session_state.dashboard_filters
    
    if table_type == "experiments" and not df.empty:
        if filters.get('battery_types'):
            df = df[df['battery_type'].isin(filters['battery_types'])]
        
        if filters.get('capacity_range'):
            min_cap, max_cap = filters['capacity_range']
            df = df[(df['nominal_capacity'] >= min_cap) & (df['nominal_capacity'] <= max_cap)]
    
    elif table_type == "steps" and not df.empty:
        if filters.get('step_types'):
            df = df[df['step_type'].isin(filters['step_types'])]
        
        if filters.get('c_rate_range'):
            min_rate, max_rate = filters['c_rate_range']
            df = df[(df['c_rate'] >= min_rate) & (df['c_rate'] <= max_rate)]
    
    return df


def render_dashboard_page():
    """Main function to render the dashboard page"""
    st.title("Battery ETL Dashboard")
    st.markdown("Explore and visualize battery test data across projects, experiments, and steps.")
    
    # Initialize session state
    init_session_state()
    
    # Render filtering controls
    render_filtering_controls()
    
    # Create three columns for the hierarchical tables
    st.header("Data Selection")
    
    # Project Table
    st.subheader("1. Projects")
    projects_df = get_projects_data()
    
    if not projects_df.empty:
        project_response = create_interactive_table(projects_df, "Projects")
        selected_project_rows = project_response.get("selected_rows", [])
        
        if selected_project_rows:
            selected_project_ids = [row['id'] for row in selected_project_rows]
            st.session_state.selected_projects = selected_project_ids
            st.success(f"Selected {len(selected_project_ids)} project(s)")
        else:
            st.session_state.selected_projects = []
    else:
        st.warning("No projects found in database")
        st.session_state.selected_projects = []
    
    # Experiment Table (filtered by selected projects)
    st.subheader("2. Experiments")
    experiments_df = get_experiments_data(st.session_state.selected_projects)
    experiments_df = apply_filters(experiments_df, "experiments")
    
    if not experiments_df.empty:
        experiment_response = create_interactive_table(experiments_df, "Experiments")
        selected_experiment_rows = experiment_response.get("selected_rows", [])
        
        if selected_experiment_rows:
            selected_experiment_ids = [row['id'] for row in selected_experiment_rows]
            st.session_state.selected_experiments = selected_experiment_ids
            st.success(f"Selected {len(selected_experiment_ids)} experiment(s)")
        else:
            st.session_state.selected_experiments = []
    else:
        if st.session_state.selected_projects:
            st.warning("No experiments found for selected projects")
        else:
            st.info("Select projects to view experiments")
        st.session_state.selected_experiments = []
    
    # Step Table (filtered by selected experiments)
    st.subheader("3. Steps")
    steps_df = get_steps_data(st.session_state.selected_experiments)
    steps_df = apply_filters(steps_df, "steps")
    
    selected_step_ids = []
    if not steps_df.empty:
        step_response = create_interactive_table(steps_df, "Steps")
        selected_step_rows = step_response.get("selected_rows", [])
        
        if selected_step_rows:
            selected_step_ids = [row['id'] for row in selected_step_rows]
            st.session_state.selected_steps = selected_step_ids
            st.success(f"Selected {len(selected_step_ids)} step(s)")
            
            # Create filtered dataframe for plotting
            selected_steps_df = steps_df[steps_df['id'].isin(selected_step_ids)]
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
                mime="text/csv"
            )


if __name__ == "__main__":
    render_dashboard_page()