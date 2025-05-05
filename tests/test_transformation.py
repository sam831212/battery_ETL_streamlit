"""
Test module for transformation functions

This module contains unit tests for the transformation functions in the ETL pipeline.
"""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from app.etl.transformation import (
    calculate_c_rate,
    calculate_soc,
    transform_data
)

def create_test_step_data():
    """
    Create test step data similar to the Excel example provided.
    """
    # Create a DataFrame similar to the Excel example
    steps_data = [
        # step_number, step_type, start_time, end_time, capacity, current, voltage_start, voltage_end, original_step_type
        (1, 'rest', '2023-01-01 10:00:00', '2023-01-01 10:01:00', 0.0, 0.0, 4.2, 4.2, '静置'),
        (2, 'charge', '2023-01-01 10:01:00', '2023-01-01 10:38:00', 10.9, 5.0, 3.5, 4.2, 'CC-CV充電'),
        (3, 'rest', '2023-01-01 10:38:00', '2023-01-01 11:08:00', 10.9, 0.0, 4.2, 4.2, '静置'),
        (4, 'discharge', '2023-01-01 11:08:00', '2023-01-01 12:07:00', -8.4, -5.4, 4.2, 3.0, 'CC放電'),
        (5, 'rest', '2023-01-01 12:07:00', '2023-01-01 12:37:00', -8.4, 0.0, 3.0, 3.0, '静置'),
        (6, 'charge', '2023-01-01 12:37:00', '2023-01-01 13:14:00', 10.9, 5.4, 3.0, 4.2, 'CC-CV充電'),
        (7, 'rest', '2023-01-01 13:14:00', '2023-01-01 13:44:00', 10.9, 0.0, 4.2, 4.2, '静置'),
        (8, 'discharge', '2023-01-01 13:44:00', '2023-01-01 14:44:00', -8.4, -5.4, 4.2, 3.0, 'CC放電'),
        (9, 'rest', '2023-01-01 14:44:00', '2023-01-01 15:14:00', -8.4, 0.0, 3.0, 3.0, '静置'),
        (10, 'charge', '2023-01-01 15:14:00', '2023-01-01 15:51:00', 10.9, 5.4, 3.0, 4.2, 'CC-CV充電'),
        (11, 'rest', '2023-01-01 15:51:00', '2023-01-01 16:21:00', 10.9, 0.0, 4.2, 4.2, '静置'),
        (12, 'discharge', '2023-01-01 16:21:00', '2023-01-01 17:20:00', -8.5, -5.4, 4.2, 2.5, 'CC放電'),  # Reference discharge step
        (13, 'rest', '2023-01-01 17:20:00', '2023-01-01 17:50:00', -8.5, 0.0, 2.5, 2.5, '静置'),
        (14, 'charge', '2023-01-01 17:50:00', '2023-01-01 18:15:00', 6.1, 5.4, 2.5, 3.8, 'CC-CV充電'),  # 75% SOC
        (15, 'rest', '2023-01-01 18:15:00', '2023-01-01 19:15:00', 6.1, 0.0, 3.8, 3.8, '温控控制'),
        (16, 'rest', '2023-01-01 19:15:00', '2023-01-01 20:15:00', 6.1, 0.0, 3.8, 3.8, '静置'),
        (17, 'charge', '2023-01-01 20:15:00', '2023-01-01 20:16:00', 6.4, 0.3, 3.8, 3.9, '超级CP充電')  # 77% SOC
    ]
    
    columns = ['step_number', 'step_type', 'start_time', 'end_time', 'capacity', 
               'current', 'voltage_start', 'voltage_end', 'original_step_type']
    
    df = pd.DataFrame(steps_data, columns=columns)
    
    # Convert string dates to datetime
    df['start_time'] = pd.to_datetime(df['start_time'])
    df['end_time'] = pd.to_datetime(df['end_time'])
    
    return df

def create_test_detail_data(steps_df):
    """
    Create test detail data based on the steps DataFrame.
    This is a simplified version with fewer points for testing.
    """
    detail_rows = []
    
    # For each step, create some detail measurements
    for _, step in steps_df.iterrows():
        step_number = step['step_number']
        start_time = step['start_time']
        end_time = step['end_time']
        duration = (end_time - start_time).total_seconds()
        
        # Create 5 measurement points per step
        for i in range(5):
            point_time = start_time + timedelta(seconds=duration * i / 4)
            
            # For simplicity, linearly interpolate between start and end values
            progress = i / 4
            voltage = step['voltage_start'] + progress * (step['voltage_end'] - step['voltage_start'])
            current = step['current']  # Keep current constant within a step
            
            # Calculate cumulative capacity
            # For simplicity, we'll just use the step's capacity value
            capacity = step['capacity']
            
            detail_rows.append((
                step_number,
                point_time,
                voltage,
                current,
                capacity,
                step['step_type']
            ))
    
    columns = ['step_number', 'timestamp', 'voltage', 'current', 'capacity', 'step_type']
    return pd.DataFrame(detail_rows, columns=columns)

def test_calculate_c_rate():
    """Test the C-rate calculation function"""
    # Test with positive current (using approximate equality)
    assert abs(calculate_c_rate(5.4, 8.5) - 0.635) < 0.001
    
    # Test with negative current (absolute value should be used)
    assert abs(calculate_c_rate(-5.4, 8.5) - 0.635) < 0.001
    
    # Test with zero nominal capacity should raise an error
    with pytest.raises(ValueError):
        calculate_c_rate(5.4, 0)
    
    # Test with zero current
    assert calculate_c_rate(0, 8.5) == 0

def test_calculate_soc_with_reference_step():
    """Test SOC calculation with a reference discharge step specified"""
    # Create test data
    steps_df = create_test_step_data()
    details_df = create_test_detail_data(steps_df)
    
    # The discharge step 12 is our reference (0% SOC)
    reference_step_idx = steps_df[steps_df['step_number'] == 12].index[0]
    discharge_capacity = abs(steps_df.loc[reference_step_idx, 'capacity'] - 
                            steps_df.loc[reference_step_idx-1, 'capacity'])
    
    # Execute SOC calculation
    steps_with_soc, details_with_soc = calculate_soc(steps_df, details_df, reference_step_idx)
    
    # Verify SOC calculation for specific steps
    # Reference discharge step should be 0% SOC
    assert steps_with_soc.loc[reference_step_idx, 'soc_end'] == 0.0
    
    # Step 14 should be approximately 75% SOC (partial charge)
    step_14_idx = steps_df[steps_df['step_number'] == 14].index[0]
    assert abs(steps_with_soc.loc[step_14_idx, 'soc_end'] - 75.0) < 2.0
    
    # Step 17 should be approximately 77% SOC
    step_17_idx = steps_df[steps_df['step_number'] == 17].index[0]
    assert abs(steps_with_soc.loc[step_17_idx, 'soc_end'] - 77.0) < 2.0
    
    # All steps should have SOC values
    assert steps_with_soc['soc_end'].notna().all()
    
    # Check that detail records also have SOC values
    assert 'soc' in details_with_soc.columns
    assert details_with_soc['soc'].notna().any()

def test_calculate_soc_auto_reference():
    """Test SOC calculation with automatic reference step detection"""
    # Create test data
    steps_df = create_test_step_data()
    details_df = create_test_detail_data(steps_df)
    
    # Execute SOC calculation without specifying reference step
    steps_with_soc, details_with_soc = calculate_soc(steps_df, details_df)
    
    # The discharge step with lowest voltage should be chosen (step 12)
    reference_step_idx = steps_df[steps_df['step_number'] == 12].index[0]
    
    # Verify the reference step has 0% SOC
    assert steps_with_soc.loc[reference_step_idx, 'soc_end'] == 0.0
    
    # Step 14 should still be approximately 75% SOC
    step_14_idx = steps_df[steps_df['step_number'] == 14].index[0]
    assert abs(steps_with_soc.loc[step_14_idx, 'soc_end'] - 75.0) < 2.0

def test_calculate_soc_edge_cases():
    """Test SOC calculation edge cases"""
    # Create test data with no discharge steps
    steps_data = [
        (1, 'rest', '2023-01-01 10:00:00', '2023-01-01 10:01:00', 0.0, 0.0, 4.2, 4.2, '静置'),
        (2, 'charge', '2023-01-01 10:01:00', '2023-01-01 10:38:00', 10.9, 5.0, 3.5, 4.2, 'CC-CV充電'),
        (3, 'rest', '2023-01-01 10:38:00', '2023-01-01 11:08:00', 10.9, 0.0, 4.2, 4.2, '静置')
    ]
    
    columns = ['step_number', 'step_type', 'start_time', 'end_time', 'capacity', 
               'current', 'voltage_start', 'voltage_end', 'original_step_type']
    
    no_discharge_df = pd.DataFrame(steps_data, columns=columns)
    no_discharge_df['start_time'] = pd.to_datetime(no_discharge_df['start_time'])
    no_discharge_df['end_time'] = pd.to_datetime(no_discharge_df['end_time'])
    
    details_df = create_test_detail_data(no_discharge_df)
    
    # SOC calculation should raise an error with no discharge steps
    with pytest.raises(ValueError, match="No discharge steps found"):
        calculate_soc(no_discharge_df, details_df)
    
    # Test with invalid reference step index
    steps_df = create_test_step_data()
    details_df = create_test_detail_data(steps_df)
    
    with pytest.raises(ValueError, match="Reference step .* not found"):
        calculate_soc(steps_df, details_df, 999)  # Non-existent index