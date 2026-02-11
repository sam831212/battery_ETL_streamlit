"""
Validation functions for battery test data

This module provides functions for validating battery test data,
identifying anomalies, and generating validation reports.
It also includes functions for generating summary tables with key statistics.
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Any, Union, Optional


def detect_voltage_anomalies(df: pd.DataFrame, 
                             voltage_col: str = 'voltage',
                             window_size: int = 5,
                             z_threshold: float = 3.0) -> pd.DataFrame:
    """
    Detect anomalies in voltage measurements using statistical methods.
    
    Args:
        df: DataFrame containing voltage data
        voltage_col: Name of the voltage column
        window_size: Size of the rolling window for anomaly detection
        z_threshold: Z-score threshold for anomaly detection
        
    Returns:
        DataFrame with added columns:
        - 'voltage_zscore': Z-score of voltage measurements
        - 'voltage_is_anomaly': Boolean flag for anomalous points
    """
    if voltage_col not in df.columns or len(df) < window_size:
        # Add empty anomaly columns
        df_result = df.copy()
        df_result[f'{voltage_col}_zscore'] = np.nan
        df_result[f'{voltage_col}_is_anomaly'] = False
        return df_result
    
    # Calculate rolling mean and std
    df_result = df.copy()
    df_sorted = df_result.sort_index()
    
    # Calculate rolling stats
    rolling_mean = df_sorted[voltage_col].rolling(window=window_size, center=True).mean()
    rolling_std = df_sorted[voltage_col].rolling(window=window_size, center=True).std()
    
    # Handle edge cases where std is 0
    rolling_std = rolling_std.replace(0, np.nan)
    
    # Calculate z-scores
    df_result[f'{voltage_col}_zscore'] = np.abs((df_sorted[voltage_col] - rolling_mean) / rolling_std)
    
    # Identify anomalies
    df_result[f'{voltage_col}_is_anomaly'] = df_result[f'{voltage_col}_zscore'] > z_threshold
    
    # Fill NaN values in anomaly flag with False
    df_result[f'{voltage_col}_is_anomaly'] = df_result[f'{voltage_col}_is_anomaly'].fillna(False)
    
    return df_result


def detect_capacity_anomalies(df: pd.DataFrame, 
                              capacity_col: str = 'capacity',
                              total_capacity_col: str = 'total_capacity',
                              step_type_col: str = 'step_type',
                              min_capacity_threshold: float = 0.0,
                              max_change_pct: float = 20.0) -> pd.DataFrame:
    """
    Detect anomalies in capacity measurements.
    
    Args:
        df: DataFrame containing capacity data
        capacity_col: Name of the step capacity column
        total_capacity_col: Name of the cumulative capacity column
        step_type_col: Name of the step type column
        min_capacity_threshold: Minimum valid capacity value
        max_change_pct: Maximum allowed percentage change between consecutive steps
        
    Returns:
        DataFrame with added columns:
        - 'capacity_pct_change': Percentage change in capacity
        - 'capacity_is_anomaly': Boolean flag for anomalous capacity values
    """
    if capacity_col not in df.columns or total_capacity_col not in df.columns:
        # Add empty anomaly columns
        df_result = df.copy()
        df_result['capacity_pct_change'] = np.nan
        df_result['capacity_is_anomaly'] = False
        return df_result
    
    # Copy dataframe to avoid modifying original
    df_result = df.copy()
    
    # Check for negative or suspiciously low capacity values
    df_result['capacity_is_anomaly'] = df_result[capacity_col] < min_capacity_threshold
    
    # Calculate capacity changes for each step type
    if step_type_col in df_result.columns:
        # Group by step type and calculate percentage changes
        for step_type in df_result[step_type_col].unique():
            step_mask = df_result[step_type_col] == step_type
            if step_mask.sum() > 1:  # Need at least 2 rows to calculate changes
                df_result.loc[step_mask, 'capacity_pct_change'] = \
                    df_result.loc[step_mask, capacity_col].pct_change().abs() * 100
    else:
        # Calculate overall percentage changes
        df_result['capacity_pct_change'] = df_result[capacity_col].pct_change().abs() * 100
    
    # Flag large changes as anomalies
    capacity_change_anomalies = (df_result['capacity_pct_change'] > max_change_pct) & \
                               (~df_result['capacity_pct_change'].isna())
    
    # Combine anomaly flags
    df_result['capacity_is_anomaly'] = df_result['capacity_is_anomaly'] | capacity_change_anomalies
    
    return df_result



def validate_soc_range(df: pd.DataFrame, tolerance: float = 3.0) -> Dict[str, Any]:
    """Validate that State of Charge (SOC) values are within expected range

    Args:
        df: DataFrame containing SOC values
        tolerance: Tolerance percentage above 100% or below 0% (default: 3.0)

    Returns:
        Dict containing validation results with keys:
        - 'valid': Boolean indicating if validation passed
        - 'issues': List of specific issues found
        - 'affected_rows': DataFrame indices where issues were detected
    """
    if 'soc' not in df.columns:
        return {
            'valid': False,
            'issues': ['SOC column not found in DataFrame'],
            'affected_rows': []
        }
    
    # Filter for non-null SOC values
    soc_df = df[df['soc'].notna()]
    
    # Check for SOC values outside of expected range (considering tolerance)
    low_soc_mask = soc_df['soc'] < (0 - tolerance)
    high_soc_mask = soc_df['soc'] > (100 + tolerance)
    
    # Get affected rows
    low_soc_rows = soc_df[low_soc_mask].index.tolist()
    high_soc_rows = soc_df[high_soc_mask].index.tolist()
    affected_rows = low_soc_rows + high_soc_rows
    
    # Compile issues
    issues = []
    if len(low_soc_rows) > 0:
        min_soc = soc_df['soc'].min()
        issues.append(f"Found {len(low_soc_rows)} rows with SOC below {0-tolerance}% (minimum: {min_soc:.2f}%)")
    
    if len(high_soc_rows) > 0:
        max_soc = soc_df['soc'].max()
        issues.append(f"Found {len(high_soc_rows)} rows with SOC above {100+tolerance}% (maximum: {max_soc:.2f}%)")
    
    # Validation result
    valid = len(affected_rows) == 0
    
    return {
        'valid': valid,
        'issues': issues,
        'affected_rows': affected_rows
    }


def validate_c_rate(df: pd.DataFrame, max_c_rate: float = 10.0) -> Dict[str, Any]:
    """Validate that C-rate values are within expected range

    Args:
        df: DataFrame containing c_rate values
        max_c_rate: Maximum expected C-rate (default: 10.0)

    Returns:
        Dict containing validation results with keys:
        - 'valid': Boolean indicating if validation passed
        - 'issues': List of specific issues found
        - 'affected_rows': DataFrame indices where issues were detected
    """
    if 'c_rate' not in df.columns:
        return {
            'valid': False,
            'issues': ['C-rate column not found in DataFrame'],
            'affected_rows': []
        }
    
    # Filter for non-null C-rate values
    c_rate_df = df[df['c_rate'].notna()]
    
    # Check for negative or excessively high C-rate values
    negative_c_rate_mask = c_rate_df['c_rate'] < 0
    high_c_rate_mask = c_rate_df['c_rate'] > max_c_rate
    
    # Get affected rows
    negative_c_rate_rows = c_rate_df[negative_c_rate_mask].index.tolist()
    high_c_rate_rows = c_rate_df[high_c_rate_mask].index.tolist()
    affected_rows = negative_c_rate_rows + high_c_rate_rows
    
    # Compile issues
    issues = []
    if len(negative_c_rate_rows) > 0:
        min_c_rate = c_rate_df['c_rate'].min()
        issues.append(f"Found {len(negative_c_rate_rows)} rows with negative C-rate values (minimum: {min_c_rate:.2f})")
    
    if len(high_c_rate_rows) > 0:
        max_c_rate_value = c_rate_df['c_rate'].max()
        issues.append(f"Found {len(high_c_rate_rows)} rows with C-rate above {max_c_rate} (maximum: {max_c_rate_value:.2f})")
    
    # Validation result
    valid = len(affected_rows) == 0
    
    return {
        'valid': valid,
        'issues': issues,
        'affected_rows': affected_rows
    }


def validate_data_continuity(df: pd.DataFrame, time_col: str = 'timestamp', max_gap_seconds: float = 10.0) -> Dict[str, Any]:
    """Validate data continuity (check for gaps in time series)

    Args:
        df: DataFrame containing time series data
        time_col: Name of the column containing timestamps (default: 'timestamp')
        max_gap_seconds: Maximum allowed gap in seconds (default: 10.0)

    Returns:
        Dict containing validation results with keys:
        - 'valid': Boolean indicating if validation passed
        - 'issues': List of specific issues found
        - 'affected_rows': DataFrame indices where issues were detected
    """
    if time_col not in df.columns:
        return {
            'valid': False,
            'issues': [f"Timestamp column '{time_col}' not found in DataFrame"],
            'affected_rows': []
        }
    
    # Ensure the dataframe is sorted by timestamp
    df_sorted = df.sort_values(by=time_col).reset_index(drop=False)
    
    # Calculate time differences
    df_sorted['time_diff'] = df_sorted[time_col].diff().dt.total_seconds()
    
    # Check for gaps larger than max_gap_seconds
    gaps = df_sorted[df_sorted['time_diff'] > max_gap_seconds]
    
    # Get original indices of affected rows
    affected_indices = gaps['index'].tolist()
    
    # Compile issues
    issues = []
    if len(gaps) > 0:
        max_gap = gaps['time_diff'].max()
        avg_gap = gaps['time_diff'].mean()
        issues.append(f"Found {len(gaps)} time gaps exceeding {max_gap_seconds} seconds (max: {max_gap:.2f}s, avg: {avg_gap:.2f}s)")
    
    # Validation result
    valid = len(gaps) == 0
    
    return {
        'valid': valid,
        'issues': issues,
        'affected_rows': affected_indices
    }


def validate_value_jumps(df: pd.DataFrame, column: str, max_jump_percent: float = 10.0) -> Dict[str, Any]:
    """Validate that there are no sudden jumps in values

    Args:
        df: DataFrame containing data
        column: Name of the column to check for jumps
        max_jump_percent: Maximum allowed jump in percent (default: 10.0)

    Returns:
        Dict containing validation results with keys:
        - 'valid': Boolean indicating if validation passed
        - 'issues': List of specific issues found
        - 'affected_rows': DataFrame indices where issues were detected
    """
    if column not in df.columns:
        return {
            'valid': False,
            'issues': [f"Column '{column}' not found in DataFrame"],
            'affected_rows': []
        }
    
    # Skip validation if less than 2 rows
    if len(df) < 2:
        return {
            'valid': True,
            'issues': [],
            'affected_rows': []
        }
    
    # Calculate percentage changes
    df_sorted = df.copy()
    df_sorted[f'{column}_pct_change'] = df_sorted[column].pct_change().abs() * 100
    
    # Check for jumps larger than max_jump_percent
    jumps = df_sorted[df_sorted[f'{column}_pct_change'] > max_jump_percent]
    
    # Get affected rows
    affected_rows = jumps.index.tolist()
    
    # Compile issues
    issues = []
    if len(jumps) > 0:
        max_jump = jumps[f'{column}_pct_change'].max()
        issues.append(f"Found {len(jumps)} jumps in '{column}' exceeding {max_jump_percent}% (maximum: {max_jump:.2f}%)")
    
    # Validation result
    valid = len(jumps) == 0
    
    return {
        'valid': valid,
        'issues': issues,
        'affected_rows': affected_rows
    }


def generate_validation_report(df: pd.DataFrame, step_type: Optional[str] = None,
                             detect_anomalies: bool = True) -> Dict[str, Any]:
    """Generate a comprehensive validation report for battery data

    Args:
        df: DataFrame containing battery test data
        step_type: Optional step type for specialized validation (charge, discharge, rest)
        detect_anomalies: Whether to run anomaly detection (default: True)

    Returns:
        Dict containing validation report with keys:
        - 'valid': Boolean indicating if all validations passed
        - 'summary': Summary of validation results
        - 'validations': Dict of individual validation results
        - 'issues_count': Total number of issues found
        - 'affected_rows_count': Total number of unique affected rows
        - 'affected_rows': List of unique indices where issues were detected
        - 'issues_by_severity': Dict of issues categorized by severity
        - 'df_with_anomalies': DataFrame with anomaly detection columns (if detect_anomalies=True)
    """
    validations = {}
    all_affected_rows = []
    
    # Make a copy of the DataFrame to avoid modifying the original
    df_processed = df.copy()
    
    # Run validations
    if 'soc' in df_processed.columns:
        validations['soc_range'] = validate_soc_range(df_processed)
        all_affected_rows.extend(validations['soc_range']['affected_rows'])
    
    if 'c_rate' in df_processed.columns:
        validations['c_rate'] = validate_c_rate(df_processed)
        all_affected_rows.extend(validations['c_rate']['affected_rows'])
    
    if 'timestamp' in df_processed.columns:
        validations['data_continuity'] = validate_data_continuity(df_processed)
        all_affected_rows.extend(validations['data_continuity']['affected_rows'])
    
    # Voltage jump validation
    if 'voltage' in df_processed.columns:
        validations['voltage_jumps'] = validate_value_jumps(df_processed, 'voltage', max_jump_percent=5.0)
        all_affected_rows.extend(validations['voltage_jumps']['affected_rows'])
    
    # Current jump validation (different thresholds for different step types)
    if 'current' in df_processed.columns:
        max_jump = 20.0  # Default
        if step_type == 'rest':
            max_jump = 1.0  # Stricter for rest steps
        
        validations['current_jumps'] = validate_value_jumps(df_processed, 'current', max_jump_percent=max_jump)
        all_affected_rows.extend(validations['current_jumps']['affected_rows'])
    
    # Temperature jump validation
    if 'temperature' in df_processed.columns:
        validations['temperature_jumps'] = validate_value_jumps(df_processed, 'temperature', max_jump_percent=10.0)
        all_affected_rows.extend(validations['temperature_jumps']['affected_rows'])
    
    # Run anomaly detection if requested
    anomaly_counts = {'voltage': 0, 'capacity': 0, 'temperature': 0}
    
    if detect_anomalies:
        # Detect voltage anomalies
        if 'voltage' in df_processed.columns:
            df_processed = detect_voltage_anomalies(df_processed)
            voltage_anomalies = df_processed[df_processed['voltage_is_anomaly']].index.tolist()
            anomaly_counts['voltage'] = len(voltage_anomalies)
            all_affected_rows.extend(voltage_anomalies)
            
            if anomaly_counts['voltage'] > 0:
                validations['voltage_anomalies'] = {
                    'valid': anomaly_counts['voltage'] == 0,
                    'issues': [f"Found {anomaly_counts['voltage']} voltage anomalies using statistical analysis"],
                    'affected_rows': voltage_anomalies
                }
        
        # Detect capacity anomalies
        if 'capacity' in df_processed.columns:
            df_processed = detect_capacity_anomalies(df_processed)
            capacity_anomalies = df_processed[df_processed['capacity_is_anomaly']].index.tolist()
            anomaly_counts['capacity'] = len(capacity_anomalies)
            all_affected_rows.extend(capacity_anomalies)
            
            if anomaly_counts['capacity'] > 0:
                validations['capacity_anomalies'] = {
                    'valid': anomaly_counts['capacity'] == 0,
                    'issues': [f"Found {anomaly_counts['capacity']} capacity anomalies"],
                    'affected_rows': capacity_anomalies
                }
            
    # Get unique affected rows
    unique_affected_rows = list(set(all_affected_rows))
    
    # Determine if all validations passed
    all_valid = all(v.get('valid', False) for v in validations.values())
    
    # Count total issues
    issues_count = sum(len(v.get('issues', [])) for v in validations.values())
    
    # Categorize issues by severity
    issues_by_severity = {
        'critical': [],
        'warning': [],
        'info': []
    }
    
    # Categorize issues
    for validation_name, validation in validations.items():
        for issue in validation.get('issues', []):
            # Determine severity based on validation type and content
            severity = 'warning'  # Default severity
            
            if 'SOC column not found' in issue or 'C-rate column not found' in issue:
                severity = 'info'
            elif 'negative C-rate' in issue or 'SOC below' in issue or 'SOC above' in issue:
                severity = 'critical'
            elif 'time gaps' in issue and 'exceeding 60' in issue:
                severity = 'critical'
            elif 'time gaps' in issue:
                severity = 'warning'
            elif 'anomalies' in issue:
                severity = 'warning'  # Anomalies are typically warnings
            
            issues_by_severity[severity].append({
                'validation': validation_name,
                'issue': issue
            })
    
    # Prepare summary
    total_rows = len(df_processed)
    affected_pct = (len(unique_affected_rows) / total_rows * 100) if total_rows > 0 else 0
    
    summary = {
        'total_rows': total_rows,
        'affected_rows_count': len(unique_affected_rows),
        'affected_percentage': affected_pct,
        'total_issues': issues_count,
        'critical_issues': len(issues_by_severity['critical']),
        'warning_issues': len(issues_by_severity['warning']),
        'info_issues': len(issues_by_severity['info']),
        'anomaly_counts': anomaly_counts
    }
    
    # Prepare the final report
    report = {
        'valid': all_valid,
        'summary': summary,
        'validations': validations,
        'issues_count': issues_count,
        'affected_rows_count': len(unique_affected_rows),
        'affected_rows': unique_affected_rows,
        'issues_by_severity': issues_by_severity,
        'df_with_anomalies': df_processed
    }
    
    return report


def generate_summary_table(selected_steps: pd.DataFrame,
                          include_stats: List[str] = ['min', 'max', 'mean', 'median', 'std'],
                          include_validation: bool = True) -> pd.DataFrame:
    """
    Generate a summary table with key statistics for selected steps.
    
    Args:
        selected_steps: DataFrame containing step data
        include_stats: List of statistics to include
        include_validation: Whether to include validation information
        
    Returns:
        DataFrame containing summary statistics
    """
    if selected_steps.empty:
        return pd.DataFrame()
    
    # Copy dataframe to avoid modifying original
    df = selected_steps.copy()
    
    # Prepare summary table
    summary_data = []
    
    # Group by step type and step number
    if 'step_type' in df.columns and 'step_number' in df.columns:
        grouped = df.groupby(['step_type', 'step_number'])
    elif 'step_number' in df.columns:
        grouped = df.groupby('step_number')
    else:
        # No grouping possible
        grouped = [(None, df)]
    
    # Calculate statistics for each group
    for group_key, group_df in grouped:
        row_data = {}
        
        # Add step information
        if isinstance(group_key, tuple):
            row_data['step_type'] = group_key[0]
            row_data['step_number'] = group_key[1]
        elif group_key is not None:
            row_data['step_number'] = group_key
            row_data['step_type'] = group_df['step_type'].iloc[0] if 'step_type' in group_df.columns else 'Unknown'
        else:
            row_data['step_type'] = 'All'
            row_data['step_number'] = 'All'
        
        # Add original step type if available
        if 'original_step_type' in group_df.columns:
            row_data['original_step_type'] = group_df['original_step_type'].iloc[0]
        
        # Add key metrics with requested statistics
        numeric_columns = ['voltage', 'current', 'capacity', 'c_rate', 'temperature', 'soc']
        
        for col in numeric_columns:
            if col in group_df.columns:
                # Skip columns with all NaN values
                if group_df[col].isna().all():
                    continue
                
                for stat in include_stats:
                    if stat == 'min':
                        row_data[f'{col}_min'] = group_df[col].min()
                    elif stat == 'max':
                        row_data[f'{col}_max'] = group_df[col].max()
                    elif stat == 'mean':
                        row_data[f'{col}_mean'] = group_df[col].mean()
                    elif stat == 'median':
                        row_data[f'{col}_median'] = group_df[col].median()
                    elif stat == 'std':
                        row_data[f'{col}_std'] = group_df[col].std()
        
        # Calculate capacity retention if possible
        if 'capacity' in group_df.columns and row_data['step_type'] == 'discharge':
            # Add discharge capacity values
            row_data['discharge_capacity'] = group_df['capacity'].abs().max()
            
            # Calculate retention compared to nominal capacity if available
            if 'nominal_capacity' in group_df.columns:
                nominal_cap = group_df['nominal_capacity'].iloc[0]
                if nominal_cap > 0:
                    row_data['capacity_retention'] = (row_data['discharge_capacity'] / nominal_cap) * 100
        
        # Add time duration if timestamp is available
        if 'timestamp' in group_df.columns:
            timestamps = group_df['timestamp'].sort_values()
            row_data['duration_seconds'] = (timestamps.iloc[-1] - timestamps.iloc[0]).total_seconds()
        
        # Add validation status if requested
        if include_validation:
            # Check if any anomalies exist
            has_anomalies = False
            
            for col in numeric_columns:
                anomaly_col = f'{col}_is_anomaly'
                if anomaly_col in group_df.columns and group_df[anomaly_col].any():
                    has_anomalies = True
                    row_data[f'{col}_anomalies'] = group_df[anomaly_col].sum()
            
            row_data['has_anomalies'] = has_anomalies
        
        summary_data.append(row_data)
    
    # Create summary dataframe
    summary_df = pd.DataFrame(summary_data)
    
    # Sort by step number if available
    if 'step_number' in summary_df.columns:
        summary_df = summary_df.sort_values('step_number')
    
    return summary_df