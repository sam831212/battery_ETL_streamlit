"""
Data editing service for the Battery ETL Dashboard
Provides functions to update database records through the UI
"""

from typing import Dict, Any, Optional, List
from sqlmodel import Session, select
from datetime import datetime, UTC
import streamlit as st

from app.models.database import Project, Cell, Experiment, Step, Measurement
from app.utils.database import get_session


def update_project(project_id: int, updates: Dict[str, Any]) -> bool:
    """Update a project record"""
    try:
        with get_session() as session:
            project = session.get(Project, project_id)
            if not project:
                st.error(f"Project with ID {project_id} not found")
                return False
            
            # Update fields
            for field, value in updates.items():
                if hasattr(project, field):
                    setattr(project, field, value)
            
            session.add(project)
            session.commit()
            session.refresh(project)
            return True
    except Exception as e:
        st.error(f"Error updating project: {str(e)}")
        return False


def update_cell(cell_id: int, updates: Dict[str, Any]) -> bool:
    """Update a cell record"""
    try:
        with get_session() as session:
            cell = session.get(Cell, cell_id)
            if not cell:
                st.error(f"Cell with ID {cell_id} not found")
                return False
            
            # Update fields
            for field, value in updates.items():
                if hasattr(cell, field):
                    setattr(cell, field, value)
            
            session.add(cell)
            session.commit()
            session.refresh(cell)
            return True
    except Exception as e:
        st.error(f"Error updating cell: {str(e)}")
        return False


def update_experiment(experiment_id: int, updates: Dict[str, Any]) -> bool:
    """Update an experiment record"""
    try:
        with get_session() as session:
            experiment = session.get(Experiment, experiment_id)
            if not experiment:
                st.error(f"Experiment with ID {experiment_id} not found")
                return False
            
            # Update fields
            for field, value in updates.items():
                if hasattr(experiment, field):
                    setattr(experiment, field, value)
            
            session.add(experiment)
            session.commit()
            session.refresh(experiment)
            return True
    except Exception as e:
        st.error(f"Error updating experiment: {str(e)}")
        return False


def update_step(step_id: int, updates: Dict[str, Any]) -> bool:
    """Update a step record"""
    try:
        with get_session() as session:
            step = session.get(Step, step_id)
            if not step:
                st.error(f"Step with ID {step_id} not found")
                return False
            
            # Update fields
            for field, value in updates.items():
                if hasattr(step, field):
                    setattr(step, field, value)
            
            session.add(step)
            session.commit()
            session.refresh(step)
            return True
    except Exception as e:
        st.error(f"Error updating step: {str(e)}")
        return False


def update_measurement(measurement_id: int, updates: Dict[str, Any]) -> bool:
    """Update a measurement record"""
    try:
        with get_session() as session:
            measurement = session.get(Measurement, measurement_id)
            if not measurement:
                st.error(f"Measurement with ID {measurement_id} not found")
                return False
            
            # Update fields
            for field, value in updates.items():
                if hasattr(measurement, field):
                    setattr(measurement, field, value)
            
            session.add(measurement)
            session.commit()
            session.refresh(measurement)
            return True
    except Exception as e:
        st.error(f"Error updating measurement: {str(e)}")
        return False


def get_editable_fields(table_name: str) -> List[str]:
    """Get list of editable fields for each table"""
    editable_fields = {
        "projects": ["name", "description", "start_date"],
        "cells": ["name", "manufacturer", "chemistry", "nominal_capacity", "nominal_voltage", 
                 "form_factor", "serial_number", "date_received", "notes"],
        "experiments": ["name", "description", "battery_type", "nominal_capacity", 
                       "temperature", "operator", "start_date"],
        "steps": ["step_type", "voltage_start", "voltage_end", "current", "capacity", 
                 "energy", "temperature_start", "temperature_end", "c_rate", 
                 "soc_start", "soc_end", "pre_test_rest_time", "data_meta"],
        "measurements": ["voltage", "current", "temperature", "capacity", "energy"]
    }
    return editable_fields.get(table_name.lower(), [])


def get_field_type(field_name: str) -> str:
    """Get the expected data type for a field"""
    numeric_fields = [
        "nominal_capacity", "nominal_voltage", "temperature", "voltage_start", 
        "voltage_end", "current", "capacity", "energy", "temperature_start", 
        "temperature_end", "c_rate", "soc_start", "soc_end", "pre_test_rest_time",
        "voltage", "execution_time"
    ]
    
    datetime_fields = ["start_date", "date_received"]
    
    if field_name in numeric_fields:
        return "numeric"
    elif field_name in datetime_fields:
        return "datetime"
    else:
        return "text"
