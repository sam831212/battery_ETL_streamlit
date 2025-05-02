"""
Unit tests for the ETL transformation module

Tests the functionality of app.etl.transformation to ensure that
calculations and data transformations are performed correctly.
"""
import os
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from app.etl.transformation import (
    calculate_c_rate,
    calculate_soc,
    _interpolate_soc,
    extract_ocv_values,
    calculate_temperature_metrics,
    transform_data
)


# Fixtures
@pytest.fixture
def sample_steps_df():
    """Create a sample step DataFrame for testing transformations"""
    return pd.DataFrame({
        'step_number': [1, 2, 3, 4],
        'step_type': ['charge', 'rest', 'discharge', 'rest'],
        'start_time': [
            datetime(2023, 1, 1, 10, 0, 0),
            datetime(2023, 1, 1, 11, 0, 0),
            datetime(2023, 1, 1, 12, 0, 0),
            datetime(2023, 1, 1, 13, 0, 0)
        ],
        'end_time': [
            datetime(2023, 1, 1, 11, 0, 0),
            datetime(2023, 1, 1, 12, 0, 0),
            datetime(2023, 1, 1, 13, 0, 0),
            datetime(2023, 1, 1, 14, 0, 0)
        ],
        'duration': [3600, 3600, 3600, 3600],
        'voltage_start': [3.3, 4.1, 4.0, 3.3],
        'voltage_end': [4.1, 4.0, 3.3, 3.4],
        'current': [1.0, 0.0, -1.0, 0.0],
        'capacity': [3.0, 3.0, 0.0, 0.0],  # Assuming cumulative capacity
        'energy': [12.0, 12.0, 0.0, 0.0],
        'temperature': [25.0, 25.5, 26.0, 25.0]
    })


@pytest.fixture
def sample_details_df(sample_steps_df):
    """Create a sample details DataFrame with measurements at different time points"""
    details = []
    
    # Create detail measurements for each step
    for idx, step in sample_steps_df.iterrows():
        step_num = step['step_number']
        start_time = step['start_time']
        end_time = step['end_time']
        v_start = step['voltage_start']
        v_end = step['voltage_end']
        current = step['current']
        
        # Create 10 measurements per step
        for i in range(10):
            # Calculate interpolated time and voltage
            t = start_time + (end_time - start_time) * i / 9
            v = v_start + (v_end - v_start) * i / 9
            
            # For charge/discharge steps, calculate capacity proportionally
            if step['step_type'] in ['charge', 'discharge']:
                capacity = step['capacity'] * i / 9
                energy = step['energy'] * i / 9
            else:
                capacity = step['capacity']  # No change in capacity during rest
                energy = step['energy']
            
            details.append({
                'step_number': step_num,
                'timestamp': t,
                'voltage': v,
                'current': current,
                'temperature': step['temperature'] + 0.1 * i,  # Small temperature variation
                'capacity': capacity,
                'energy': energy
            })
    
    return pd.DataFrame(details)


# Tests for calculate_c_rate
def test_calculate_c_rate_normal():
    """Test C-rate calculation with normal values"""
    # Test charge (positive current)
    assert calculate_c_rate(1.0, 2.0) == 0.5
    # Test discharge (negative current)
    assert calculate_c_rate(-1.0, 2.0) == 0.5
    # Test higher rates
    assert calculate_c_rate(10.0, 2.0) == 5.0


def test_calculate_c_rate_edge_cases():
    """Test C-rate calculation with edge cases"""
    # Test with zero current
    assert calculate_c_rate(0.0, 2.0) == 0.0
    # Test with small current
    assert abs(calculate_c_rate(0.001, 2.0) - 0.0005) < 1e-10
    # Test with small capacity
    assert calculate_c_rate(1.0, 0.1) == 10.0


def test_calculate_c_rate_invalid():
    """Test C-rate calculation with invalid inputs"""
    # Test with zero capacity (should raise ValueError)
    with pytest.raises(ValueError, match="Nominal capacity must be positive"):
        calculate_c_rate(1.0, 0.0)
    
    # Test with negative capacity (should raise ValueError)
    with pytest.raises(ValueError, match="Nominal capacity must be positive"):
        calculate_c_rate(1.0, -1.0)


# Tests for calculate_soc and _interpolate_soc
def test_calculate_soc_explicit_reference(sample_steps_df, sample_details_df):
    """Test SOC calculation with an explicit reference step"""
    # Use step 3 (discharge) as the reference (0% SOC)
    steps_result, details_result = calculate_soc(sample_steps_df, sample_details_df, full_discharge_step_idx=2)
    
    # Check SOC values in steps DataFrame
    assert 'soc_start' in steps_result.columns
    assert 'soc_end' in steps_result.columns
    
    # Discharge step (index 2) should end at 0% SOC
    assert abs(steps_result.at[2, 'soc_end'] - 0.0) < 1e-6
    
    # Capacity difference between charge and discharge should be reflected in SOC
    assert steps_result.at[0, 'soc_end'] > 0  # Charge step should have positive SOC
    
    # Check SOC values in details DataFrame
    assert 'soc' in details_result.columns
    assert not details_result['soc'].isna().any()


def test_calculate_soc_auto_reference(sample_steps_df, sample_details_df):
    """Test SOC calculation with automatic reference detection"""
    # No reference provided, should find lowest voltage step automatically
    steps_result, details_result = calculate_soc(sample_steps_df, sample_details_df)
    
    # All steps should have SOC values
    assert not steps_result['soc_start'].isna().any()
    assert not steps_result['soc_end'].isna().any()
    
    # Lowest voltage step should have SOC near 0%
    min_voltage_idx = sample_steps_df['voltage_end'].idxmin()
    assert abs(steps_result.at[min_voltage_idx, 'soc_end']) < 20  # Should be close to 0%
    
    # Detail SOC values should be within range of step SOC values
    min_step_soc = min(steps_result['soc_start'].min(), steps_result['soc_end'].min())
    max_step_soc = max(steps_result['soc_start'].max(), steps_result['soc_end'].max())
    
    assert details_result['soc'].min() >= min_step_soc - 1  # Allow small numerical differences
    assert details_result['soc'].max() <= max_step_soc + 1


def test_calculate_soc_missing_discharge(sample_steps_df, sample_details_df):
    """Test SOC calculation when there are no discharge steps"""
    # Remove the discharge step
    charge_only_df = sample_steps_df[sample_steps_df['step_type'] != 'discharge'].copy().reset_index(drop=True)
    details_subset = sample_details_df[sample_details_df['step_number'].isin(charge_only_df['step_number'])].copy()
    
    # This should raise a ValueError because no discharge step is available for reference
    with pytest.raises(ValueError, match="No discharge steps found"):
        calculate_soc(charge_only_df, details_subset)


def test_interpolate_soc():
    """Test the _interpolate_soc helper function"""
    # Test with time-based interpolation
    row = pd.Series({
        'timestamp': datetime(2023, 1, 1, 10, 30, 0),
        'capacity': 1.5
    })
    
    step_soc = {
        'soc_start': 20.0,
        'soc_end': 60.0,
        'start_time': datetime(2023, 1, 1, 10, 0, 0),
        'end_time': datetime(2023, 1, 1, 11, 0, 0),
        'capacity_start': 0.0,
        'capacity_end': 3.0
    }
    
    # Time is halfway through, so SOC should be halfway between start and end
    # (10:30 is halfway between 10:00 and 11:00)
    interpolated_soc = _interpolate_soc(row, step_soc, 3.0)
    assert abs(interpolated_soc - 40.0) < 1e-6  # Should be 40% (halfway between 20% and 60%)
    
    # Test with capacity-based interpolation
    row_no_time = pd.Series({
        'capacity': 1.5,  # Halfway through capacity change
        'timestamp': None
    })
    
    step_soc_no_time = {
        'soc_start': 20.0,
        'soc_end': 60.0,
        'capacity_start': 0.0,
        'capacity_end': 3.0
    }
    
    # Capacity is halfway through, so SOC should be halfway between start and end
    interpolated_soc = _interpolate_soc(row_no_time, step_soc_no_time, 3.0)
    assert abs(interpolated_soc - 40.0) < 1e-6  # Should be 40% (halfway between 20% and 60%)


# Tests for extract_ocv_values
def test_extract_ocv_values(sample_steps_df):
    """Test extraction of OCV values from rest steps"""
    result_df = extract_ocv_values(sample_steps_df)
    
    # Check that OCV column was added
    assert 'ocv' in result_df.columns
    
    # Rest steps should have OCV values equal to their end voltage
    rest_steps = result_df[result_df['step_type'] == 'rest']
    for idx, step in rest_steps.iterrows():
        assert step['ocv'] == step['voltage_end']
    
    # Non-rest steps should have OCV from the next rest step
    charge_step = result_df[result_df['step_type'] == 'charge'].iloc[0]
    next_rest = rest_steps[rest_steps['start_time'] > charge_step['end_time']].iloc[0]
    assert charge_step['ocv'] == next_rest['ocv']


# Tests for calculate_temperature_metrics
def test_calculate_temperature_metrics(sample_details_df):
    """Test calculation of temperature statistics per step"""
    result_df = calculate_temperature_metrics(sample_details_df)
    
    # Check that temperature metrics columns were added
    assert 'temperature_avg' in result_df.columns
    assert 'temperature_min' in result_df.columns
    assert 'temperature_max' in result_df.columns
    assert 'temperature_std' in result_df.columns
    
    # Check results for each step
    for step_num in sample_details_df['step_number'].unique():
        step_details = sample_details_df[sample_details_df['step_number'] == step_num]
        step_metrics = result_df[result_df['step_number'] == step_num].iloc[0]
        
        # Check that metrics match actual data
        assert abs(step_metrics['temperature_avg'] - step_details['temperature'].mean()) < 1e-6
        assert abs(step_metrics['temperature_min'] - step_details['temperature'].min()) < 1e-6
        assert abs(step_metrics['temperature_max'] - step_details['temperature'].max()) < 1e-6
        
        # If there's only one data point, std should be 0
        if len(step_details) == 1:
            assert step_metrics['temperature_std'] == 0
        else:
            # Otherwise, check standard deviation
            assert abs(step_metrics['temperature_std'] - step_details['temperature'].std()) < 1e-6


def test_calculate_temperature_metrics_missing_column():
    """Test temperature metrics calculation with missing temperature column"""
    df = pd.DataFrame({
        'step_number': [1, 1, 2, 2],
        'other_column': [1, 2, 3, 4]
    })
    
    with pytest.raises(ValueError, match="Temperature column 'temperature' not found"):
        calculate_temperature_metrics(df)


# Tests for transform_data
def test_transform_data_integrated(sample_steps_df, sample_details_df):
    """Test full transformation pipeline on sample data"""
    # Transform the data
    nominal_capacity = 3.0
    steps_result, details_result = transform_data(sample_steps_df, sample_details_df, nominal_capacity)
    
    # Check that all expected columns were added
    for column in ['c_rate', 'temperature_avg', 'temperature_min', 'temperature_max', 
                   'temperature_std', 'soc_start', 'soc_end', 'ocv']:
        assert column in steps_result.columns
    
    for column in ['c_rate', 'soc']:
        assert column in details_result.columns
    
    # Check C-rate calculation
    for idx, step in steps_result.iterrows():
        expected_c_rate = abs(step['current']) / nominal_capacity
        assert abs(step['c_rate'] - expected_c_rate) < 1e-6
    
    # Check that temperature metrics were calculated properly
    assert not steps_result['temperature_avg'].isna().any()
    assert not steps_result['temperature_min'].isna().any()
    assert not steps_result['temperature_max'].isna().any()
    
    # Check that SOC was calculated
    assert not steps_result['soc_start'].isna().any()
    assert not steps_result['soc_end'].isna().any()
    
    # Check that OCV values were extracted for rest steps
    rest_steps = steps_result[steps_result['step_type'] == 'rest']
    assert not rest_steps['ocv'].isna().any()


def test_transform_data_invalid_capacity():
    """Test transformation with invalid capacity value"""
    # Create minimal step and detail DataFrames
    steps_df = pd.DataFrame({'step_number': [1], 'current': [1.0]})
    details_df = pd.DataFrame({'step_number': [1], 'current': [1.0]})
    
    # Zero capacity should raise ValueError in calculate_c_rate
    with pytest.raises(ValueError, match="Nominal capacity must be positive"):
        transform_data(steps_df, details_df, 0.0)
    
    # Negative capacity should raise ValueError in calculate_c_rate
    with pytest.raises(ValueError, match="Nominal capacity must be positive"):
        transform_data(steps_df, details_df, -1.0)


# Integration tests that verify the transformation process with real data
def test_transformation_integration():
    """Integration test for transformation module with extracted data"""
    # First extract data from real files
    from app.etl.extraction import load_and_preprocess_files
    
    # Get path to example files
    example_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                              "example_csv_chromaLex")
    step_csv = os.path.join(example_dir, "EVE_M41_CLC_FCV_M-table_Peak_charge_60s_0220_Step.csv")
    detail_csv = os.path.join(example_dir, "EVE_M41_CLC_FCV_M-table_Peak_charge_60s_0220_Detail.csv")
    
    # Load data without transformations first
    step_df, detail_df, _ = load_and_preprocess_files(
        step_csv,
        detail_csv,
        apply_transformations=False
    )
    
    # Apply transformations manually
    nominal_capacity = 3.5  # Example value
    steps_result, details_result = transform_data(step_df, detail_df, nominal_capacity)
    
    # Verify transformed data
    assert 'c_rate' in steps_result.columns
    assert 'soc_start' in steps_result.columns
    assert 'soc_end' in steps_result.columns
    assert 'ocv' in steps_result.columns
    
    # Check c_rate calculation
    charge_steps = steps_result[steps_result['step_type'] == 'charge']
    if not charge_steps.empty:
        for _, step in charge_steps.iterrows():
            expected_c_rate = abs(step['current']) / nominal_capacity
            assert abs(step['c_rate'] - expected_c_rate) < 1e-6
    
    # Check SOC consistency
    if 'soc_end' in steps_result.columns:
        # Maximum SOC should be greater than minimum SOC if there are charge/discharge cycles
        if len(steps_result) > 1:
            assert steps_result['soc_end'].max() > steps_result['soc_end'].min()
    
    # Check details DataFrame
    assert 'c_rate' in details_result.columns
    
    # If SOC was calculated, it should be in the details DataFrame
    if 'soc_end' in steps_result.columns:
        assert 'soc' in details_result.columns