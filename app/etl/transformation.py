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
    - Calculate SOC based on formula: SOC = (Current Capacity - Reference Capacity) / |Reference Discharge Capacity|
    - All steps have SOC values calculated relative to the reference point
    
    Args:
        steps_df: DataFrame containing step data
        details_df: DataFrame containing detailed measurement data
        full_discharge_step_idx: Optional index or step number of a full discharge step to use as reference
            
    Returns:
        Tuple containing:
        - Updated steps DataFrame with SOC values
        - Updated details DataFrame with SOC values
    """
    # Make copies of the input DataFrames to avoid modifying originals
    steps = steps_df.copy()
    details = details_df.copy()
    
    # Initialize SOC columns with NaN/None
    steps['soc_start'] = None
    steps['soc_end'] = None
    
    # First find the reference step (discharge step to use as 0% SOC reference)
    discharge_steps = steps[steps['step_type'] == 'discharge']
    if len(discharge_steps) == 0:
        raise ValueError("No discharge steps found for SOC calculation")
    
    # If no reference step is provided, find the step with the lowest ending voltage
    if full_discharge_step_idx is None:
        # Find the step with the lowest ending voltage and get its index
        min_voltage_idx = discharge_steps['voltage_end'].idxmin()
        reference_step_idx = min_voltage_idx
    else:
        # Use the provided reference step index
        reference_step_idx = full_discharge_step_idx
    
    # Validate the reference step index exists
    try:
        reference_step = steps.loc[reference_step_idx]
    except KeyError:
        # Try to handle case where step number was provided instead of index
        if isinstance(full_discharge_step_idx, int) and 'step_number' in steps.columns:
            matching_steps = steps[steps['step_number'] == full_discharge_step_idx]
            if not matching_steps.empty:
                reference_step_idx = matching_steps.index[0]
                reference_step = steps.loc[reference_step_idx]
            else:
                raise ValueError(f"Reference step {full_discharge_step_idx} not found")
        else:
            raise ValueError(f"Reference step index {full_discharge_step_idx} not found")
    
    # Ensure the reference step is a discharge step
    if reference_step['step_type'] != 'discharge':
        raise ValueError(f"Reference step must be a discharge step, but step {reference_step.get('step_number', reference_step_idx)} is a {reference_step['step_type']} step")
    
    # Find the reference discharge step's capacity and the previous step
    reference_capacity = reference_step['capacity']
    reference_step_number = reference_step['step_number']
    
    # Find the discharge capacity (the amount discharged during the reference step)
    # We need to find the previous step to calculate the capacity difference
    steps_sorted = steps.sort_values('start_time')
    step_indices = list(steps_sorted.index)
    reference_step_pos = step_indices.index(reference_step_idx)
    
    # If reference step is not the first step, get the previous step's capacity
    if reference_step_pos > 0:
        previous_step_idx = step_indices[reference_step_pos - 1]
        previous_step = steps.loc[previous_step_idx]
        previous_capacity = previous_step['capacity']
        # Calculate the discharge amount (should be negative for a discharge step)
        discharge_capacity = reference_capacity - previous_capacity
    else:
        # If reference step is the first step, we use its capacity directly
        # This is not ideal but we have no previous capacity to reference
        discharge_capacity = reference_capacity
    
    # The reference discharge capacity must be negative for a discharge step
    # We take its absolute value for SOC calculations
    reference_discharge_capacity = abs(discharge_capacity)
    if reference_discharge_capacity == 0:
        raise ValueError("Reference discharge capacity cannot be zero")
    
    # Set the reference discharge step's SOC_end to 0%
    steps.at[reference_step_idx, 'soc_end'] = 0.0
    
    # Calculate SOC for all steps based on the Excel formula: SOC = (Current Capacity - Reference Capacity) / |Reference Discharge Capacity|
    for idx, step in steps.iterrows():
        # Calculate the end SOC for each step
        steps.at[idx, 'soc_end'] = 100 * (step['capacity'] - reference_capacity) / reference_discharge_capacity
    
    # Now calculate SOC_start for each step based on the end SOC of the previous step
    for i, current_idx in enumerate(step_indices):
        if i == 0:  # First step has no previous step
            # For the first step, we calculate based on extrapolation
            # Assume constant rate of change within the step
            current_step = steps.loc[current_idx]
            next_idx = step_indices[i + 1] if i + 1 < len(step_indices) else current_idx
            next_step = steps.loc[next_idx]
            
            if next_idx != current_idx:
                # Extrapolate back based on the SOC difference between current and next step
                soc_change = next_step['soc_end'] - current_step['soc_end']
                steps.at[current_idx, 'soc_start'] = current_step['soc_end'] - soc_change
            else:
                # If there's only one step, set start SOC to same as end SOC
                steps.at[current_idx, 'soc_start'] = current_step['soc_end']
        else:
            # For other steps, start SOC is the end SOC of the previous step
            previous_idx = step_indices[i - 1]
            steps.at[current_idx, 'soc_start'] = steps.loc[previous_idx, 'soc_end']
    
    # Now calculate SOC for every detail measurement
    # Create a mapping of step number to SOC values
    step_soc_map = {}
    for idx, step in steps.iterrows():
        if pd.notna(step.get('soc_start')) and pd.notna(step.get('soc_end')):
            step_num = step['step_number']
            step_soc_map[step_num] = {
                'soc_start': step['soc_start'],
                'soc_end': step['soc_end'],
                'start_time': step['start_time'],
                'end_time': step['end_time'],
                'capacity_start': step['capacity'] - discharge_capacity if step['step_type'] == 'discharge' else step['capacity'],
                'capacity_end': step['capacity'],
            }
    
    # Calculate SOC for each detail record
    details['soc'] = details.apply(
        lambda row: _interpolate_soc(row, step_soc_map.get(row['step_number'], {}), reference_discharge_capacity),
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