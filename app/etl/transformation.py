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
    - If not provided, find the 2nd discharge step (CC放電) as the reference
    - Calculate SOC based on formula: SOC = (Total Capacity - Reference Total Capacity) / |Capacity of full discharge step|
    - All steps have SOC values calculated relative to the reference point
    - Steps before the reference point will have null SOC values
    
    Args:
        steps_df: DataFrame containing step data
        details_df: DataFrame containing detailed measurement data (not used for SOC calculation anymore)
        full_discharge_step_idx: Optional index or step number of a full discharge step to use as reference
            
    Returns:
        Tuple containing:
        - Updated steps DataFrame with SOC values
        - Unchanged details DataFrame
    """
    # Make a copy of the input DataFrame to avoid modifying original
    steps = steps_df.copy()
    
    # Initialize SOC columns with NaN/None
    steps['soc_start'] = None
    steps['soc_end'] = None
    
    # First find the reference step (discharge step to use as 0% SOC reference)
    discharge_steps = steps[steps['step_type'] == 'discharge']
    if len(discharge_steps) == 0:
        raise ValueError("No discharge steps found for SOC calculation")
    
    # If no reference step is provided, find the 2nd discharge step
    if full_discharge_step_idx is None:
        if len(discharge_steps) >= 2:
            # Sort discharge steps by step_number and get the 2nd one
            discharge_steps_sorted = discharge_steps.sort_values('step_number')
            reference_step_idx = discharge_steps_sorted.index[1]  # 2nd discharge step (0-indexed)
        else:
            # If there's only one discharge step, use it
            reference_step_idx = discharge_steps.index[0]
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
    
    # Get the reference discharge step's total capacity and capacity
    if 'total_capacity' not in reference_step:
        raise ValueError("Column 'total_capacity' not found. Please ensure the 'total_capacity' column is correctly imported from '總電壓(Ah)'.")
    
    reference_total_capacity = reference_step['total_capacity']
    reference_capacity = reference_step['capacity']
    reference_step_number = reference_step['step_number']
    
    # Set the reference discharge step's SOC_end to 0%
    steps.at[reference_step_idx, 'soc_end'] = 0.0
    
    # Get sorted step indices for processing in chronological order
    steps_sorted = steps.sort_values('start_time')
    step_indices = list(steps_sorted.index)
    reference_step_pos = step_indices.index(reference_step_idx)
    
    # Calculate SOC for all steps after the reference step based on the formula:
    # SOC = (Total Capacity - Reference Total Capacity) / |Reference Capacity|
    for i, idx in enumerate(step_indices):
        if i >= reference_step_pos:  # Only calculate for steps at or after the reference step
            step = steps.loc[idx]
            if 'total_capacity' in step and pd.notna(step['total_capacity']):
                steps.at[idx, 'soc_end'] = 100 * (step['total_capacity'] - reference_total_capacity) / abs(reference_capacity)
    
    # Calculate soc_start for each step based on the end SOC of the previous step
    for i, current_idx in enumerate(step_indices):
        if i == 0 or i <= reference_step_pos:  
            # Skip steps before or at the reference step for soc_start since they may have null soc_end
            continue
        else:
            # For steps after reference, start SOC is the end SOC of the previous step
            previous_idx = step_indices[i - 1]
            if pd.notna(steps.loc[previous_idx, 'soc_end']):
                steps.at[current_idx, 'soc_start'] = steps.loc[previous_idx, 'soc_end']
    
    # For the reference step, set soc_start to a small negative value if previous step exists
    if reference_step_pos > 0:
        previous_idx = step_indices[reference_step_pos - 1]
        if 'total_capacity' in steps.loc[previous_idx] and pd.notna(steps.loc[previous_idx, 'total_capacity']):
            previous_total_capacity = steps.loc[previous_idx, 'total_capacity']
            steps.at[reference_step_idx, 'soc_start'] = 100 * (previous_total_capacity - reference_total_capacity) / abs(reference_capacity)
    
    # Return updated steps and unchanged details
    return steps, details_df


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
    if nominal_capacity > 0:
        steps['c_rate'] = steps['current'].apply(
            lambda current: calculate_c_rate(current, nominal_capacity)
        )
        details['c_rate'] = details['current'].apply(
            lambda current: calculate_c_rate(current, nominal_capacity)
        )
    else:
        steps['c_rate'] = 0.0
        details['c_rate'] = 0.0
    
    # 2. Calculate temperature metrics for steps
    temp_metrics = calculate_temperature_metrics(details)
    steps = pd.merge(steps, temp_metrics, on='step_number', how='left')
    
    # 3. Calculate SOC
    steps, details = calculate_soc(steps, details)
    
    # 4. Extract OCV values
    steps = extract_ocv_values(steps)
    
    return steps, details