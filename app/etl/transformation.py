"""
Transformation module for battery test data

This module provides functions for calculating derived metrics from
battery test data, such as SOC, C-rate, OCV, and temperature statistics.
"""
from typing import List, Dict, Tuple, Optional, Union, Any, cast
import pandas as pd
import numpy as np
from datetime import datetime

# Type aliases for improved readability
StepDataFrame = pd.DataFrame
DetailDataFrame = pd.DataFrame


def calculate_c_rate(current: float, nominal_capacity: float) -> float:
    """
    Calculate C-rate based on current and nominal capacity.

    C-rate = |Current (A)| / Nominal Capacity (Ah)
    
    Args:
        current: Current in Amperes (A)
        nominal_capacity: Nominal capacity in Ampere-hours (Ah)

    Returns:
        C-rate value (dimensionless)
    """
    if nominal_capacity <= 0:
        raise ValueError("Nominal capacity must be positive")
    
    # Take absolute value of current for both charge and discharge
    return abs(current) / nominal_capacity


def calculate_soc(steps_df: pd.DataFrame, details_df: pd.DataFrame, full_discharge_step_idx: Optional[int] = None) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Calculate State of Charge (SOC) for all steps using Coulomb counting method.
    
    SOC calculation method:
    - If full_discharge_step_idx is provided, use that step as the 0% SOC reference point
    - If not provided, find the step with the lowest ending voltage as the reference
    - Calculate SOC based on capacity relative to the full discharge capacity
    
    Args:
        steps_df: DataFrame containing step data
        details_df: DataFrame containing detailed measurement data
        full_discharge_step_idx: Optional index of a full discharge step to use as reference
            
    Returns:
        Tuple containing:
        - Updated steps DataFrame with SOC values
        - Updated details DataFrame with SOC values
    """
    # Make copies of the input DataFrames to avoid modifying originals
    steps = steps_df.copy()
    details = details_df.copy()
    
    # If no reference step is provided, find the step with the lowest ending voltage
    # which is likely a full discharge step
    if full_discharge_step_idx is None:
        discharge_steps = steps[steps['step_type'] == 'discharge']
        if len(discharge_steps) == 0:
            raise ValueError("No discharge steps found for SOC calculation")
        
        # Get the step with the lowest ending voltage
        full_discharge_step_idx = discharge_steps['voltage_end'].idxmin()
    
    # Get the total capacity at the end of the discharge step
    # This is the reference capacity representing 0% SOC
    try:
        reference_step = steps.loc[full_discharge_step_idx]
        reference_capacity = reference_step['capacity']
    except KeyError:
        raise ValueError(f"Reference step index {full_discharge_step_idx} not found")
    
    # Calculate SOC for each step based on the reference
    for idx, step in steps.iterrows():
        # Calculate SOC at end of step relative to reference
        soc_end = 100 * (step['capacity'] - reference_capacity) / abs(reference_capacity)
        steps.at[idx, 'soc_end'] = soc_end
        
        # Find the previous chronological step for the start SOC
        previous_steps = steps[steps['end_time'] < step['start_time']]
        
        if len(previous_steps) > 0:
            # Use the end SOC of the most recent step
            prev_step = previous_steps.iloc[-1]
            steps.at[idx, 'soc_start'] = prev_step['soc_end']
        else:
            # If this is the first step, estimate based on ending SOC and capacity
            # This is an approximation since we don't have data before this step
            capacity_change = step['capacity']
            if capacity_change != 0:
                soc_start = soc_end - (100 * capacity_change / abs(reference_capacity))
            else:
                soc_start = soc_end
            
            steps.at[idx, 'soc_start'] = soc_start
    
    # Now calculate SOC for every detail measurement
    # We'll interpolate between step start and end SOC values
    
    # First, create a mapping of step number to SOC values
    step_soc_map = {}
    for idx, step in steps.iterrows():
        step_num = step['step_number']
        step_soc_map[step_num] = {
            'soc_start': step['soc_start'],
            'soc_end': step['soc_end'],
            'start_time': step['start_time'],
            'end_time': step['end_time'],
            'capacity_start': step['capacity'] - step['capacity'],  # Capacity at start of step
            'capacity_end': step['capacity'],  # Capacity at end of step
        }
    
    # Now calculate SOC for each detail record
    details['soc'] = details.apply(
        lambda row: _interpolate_soc(
            row,
            step_soc_map.get(row['step_number'], {}),
            reference_capacity
        ),
        axis=1
    )
    
    return steps, details


def _interpolate_soc(row: pd.Series, step_soc: Dict[str, Any], reference_capacity: float) -> Optional[float]:
    """
    Helper function to interpolate SOC for a specific detail measurement.
    
    Args:
        row: Row from the details DataFrame
        step_soc: Dictionary with step SOC data
        reference_capacity: Reference capacity used for SOC calculation
    
    Returns:
        Interpolated SOC value or None if interpolation is not possible
    """
    if not step_soc:
        return 0.0  # Default to 0% if no step SOC data
    
    # Get the start and end SOC for this step
    soc_start = step_soc.get('soc_start')
    soc_end = step_soc.get('soc_end')
    
    if soc_start is None or soc_end is None:
        return 0.0  # Default to 0% if SOC values are missing
    
    # If time data is available, interpolate based on time
    start_time = step_soc.get('start_time')
    end_time = step_soc.get('end_time')
    timestamp = row['timestamp']
    
    if start_time and end_time and (end_time - start_time).total_seconds() > 0:
        # Calculate time-based interpolation factor
        time_ratio = (timestamp - start_time).total_seconds() / (end_time - start_time).total_seconds()
        soc = soc_start + (soc_end - soc_start) * time_ratio
    else:
        # If time interpolation is not possible, use capacity-based interpolation
        capacity_start = step_soc.get('capacity_start', 0)
        capacity_end = step_soc.get('capacity_end', 0)
        capacity = row['capacity']
        
        if capacity_end != capacity_start:
            # Calculate capacity-based interpolation factor
            capacity_ratio = (capacity - capacity_start) / (capacity_end - capacity_start)
            soc = soc_start + (soc_end - soc_start) * capacity_ratio
        else:
            # If neither time nor capacity interpolation is possible, use the average
            soc = (soc_start + soc_end) / 2
    
    return float(soc)


def extract_ocv_values(steps_df: pd.DataFrame) -> pd.DataFrame:
    """
    Extract Open Circuit Voltage (OCV) values from rest steps.
    
    OCV is extracted from the voltage at the end of rest steps, which typically
    follows charge or discharge steps.
    
    Args:
        steps_df: DataFrame containing step data with 'step_type' column
        
    Returns:
        Updated DataFrame with OCV values
    """
    steps = steps_df.copy()
    
    # Initialize OCV column
    steps['ocv'] = None
    
    # First pass: extract OCV from rest steps
    rest_steps = steps[steps['step_type'] == 'rest']
    
    for idx, rest_step in rest_steps.iterrows():
        # Use the end voltage of the rest step as the OCV
        steps.at[idx, 'ocv'] = rest_step['voltage_end']
    
    # Second pass: propagate OCV values to charge/discharge steps
    for idx, step in steps.iterrows():
        if step['step_type'] != 'rest':
            # Find the next rest step (if any)
            next_steps = steps[(steps['start_time'] > step['end_time']) & (steps['step_type'] == 'rest')]
            
            if len(next_steps) > 0:
                # Use the OCV from the nearest following rest step
                next_rest = next_steps.iloc[0]
                steps.at[idx, 'ocv'] = next_rest['ocv']
    
    return steps


def calculate_temperature_metrics(df: pd.DataFrame, temp_column: str = 'temperature') -> pd.DataFrame:
    """
    Calculate temperature statistics per step.
    
    Args:
        df: DataFrame containing temperature data
        temp_column: Name of the column containing temperature values
        
    Returns:
        Updated DataFrame with temperature metrics columns
    """
    if temp_column not in df.columns:
        raise ValueError(f"Temperature column '{temp_column}' not found in DataFrame")
    
    result_df = df.copy()
    
    # Calculate temperature metrics for each step
    metrics = df.groupby('step_number')[temp_column].agg([
        ('temperature_avg', 'mean'),
        ('temperature_min', 'min'),
        ('temperature_max', 'max'),
        ('temperature_std', 'std')
    ]).reset_index()
    
    # Replace NaN values in standard deviation with 0
    metrics['temperature_std'] = metrics['temperature_std'].fillna(0)
    
    # Merge metrics with original DataFrame if needed
    # (Only needed if we're computing temp metrics for detail data)
    if len(metrics) < len(df):
        return pd.merge(result_df, metrics, on='step_number', how='left')
    else:
        return metrics


def transform_data(steps_df: pd.DataFrame, details_df: pd.DataFrame, 
                   nominal_capacity: float) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Apply all transformation functions to the step and detail data.
    
    Args:
        steps_df: DataFrame containing step data
        details_df: DataFrame containing detailed measurement data
        nominal_capacity: Nominal capacity of the battery in Ampere-hours (Ah)
        
    Returns:
        Tuple containing:
        - Transformed steps DataFrame
        - Transformed details DataFrame
    """
    # Make copies of the input DataFrames
    steps = steps_df.copy()
    details = details_df.copy()
    
    # 1. Calculate C-rate
    steps['c_rate'] = steps['current'].apply(
        lambda current: calculate_c_rate(current, nominal_capacity)
    )
    details['c_rate'] = details['current'].apply(
        lambda current: calculate_c_rate(current, nominal_capacity)
    )
    
    # 2. Calculate temperature metrics for steps
    temp_metrics = calculate_temperature_metrics(details)
    steps = pd.merge(steps, temp_metrics, on='step_number', how='left')
    
    # 3. Calculate SOC
    steps, details = calculate_soc(steps, details)
    
    # 4. Extract OCV values
    steps = extract_ocv_values(steps)
    
    return steps, details