from typing import List, Optional
from app.models.database import Experiment, Measurement, Project, Step
from app.utils.dashboard_constants import EXPERIMENT_DF_COLUMNS, MEASUREMENT_DF_COLUMNS, PROJECT_DF_COLUMNS, STEP_DF_COLUMNS
from app.utils.database import get_session


import pandas as pd
import streamlit as st
from sqlmodel import col, select


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
                    'experiment_count': experiment_count
                })

            return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Error fetching projects: {str(e)}")
        return pd.DataFrame(columns=PROJECT_DF_COLUMNS)


def get_experiments_data(selected_project_ids: Optional[List[int]] = None, selected_cell_ids: Optional[List[int]] = None) -> pd.DataFrame:
    """Fetch experiments, optionally filtered by project IDs and/or cell IDs"""
    try:
        with get_session() as session:
            query = select(Experiment)
            if selected_project_ids:
                query = query.where(col(Experiment.project_id).in_(selected_project_ids))
            if selected_cell_ids:
                query = query.where(col(Experiment.cell_id).in_(selected_cell_ids))

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


def get_cells_data() -> pd.DataFrame:
    """Fetch all cells from database"""
    from app.models.database import Cell
    from app.utils.dashboard_constants import CELL_DF_COLUMNS
    try:
        with get_session() as session:
            cells = session.exec(select(Cell)).all()
            if not cells:
                return pd.DataFrame(columns=CELL_DF_COLUMNS)
            data = []
            for cell in cells:
                data.append({
                    'id': cell.id,
                    'name': cell.name,
                    'manufacturer': cell.manufacturer,
                    'chemistry': cell.chemistry,
                    'capacity': cell.capacity,
                    'form': cell.form,
                    'nominal_capacity': cell.nominal_capacity,
                    'nominal_voltage': cell.nominal_voltage,
                    'form_factor': cell.form_factor,
                    'serial_number': cell.serial_number,
                    'date_received': cell.date_received,
                    'notes': cell.notes
                })
            return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Error fetching cells: {str(e)}")
        return pd.DataFrame(columns=CELL_DF_COLUMNS)