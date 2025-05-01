"""
Validation functions for battery test data

This module provides functions for validating battery test data,
identifying anomalies, and generating validation reports.
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Any, Union, Optional


def validate_soc_range(df: pd.DataFrame, tolerance: float = 2.0) -> Dict[str, Any]:
    """Validate that State of Charge (SOC) values are within expected range

    Args:
        df: DataFrame containing SOC values
        tolerance: Tolerance percentage above 100% or below 0% (default: 2.0)

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


def generate_validation_report(df: pd.DataFrame, step_type: Optional[str] = None) -> Dict[str, Any]:
    """Generate a comprehensive validation report for battery data

    Args:
        df: DataFrame containing battery test data
        step_type: Optional step type for specialized validation (charge, discharge, rest)

    Returns:
        Dict containing validation report with keys:
        - 'valid': Boolean indicating if all validations passed
        - 'summary': Summary of validation results
        - 'validations': Dict of individual validation results
        - 'issues_count': Total number of issues found
        - 'affected_rows_count': Total number of unique affected rows
        - 'affected_rows': List of unique indices where issues were detected
        - 'issues_by_severity': Dict of issues categorized by severity
    """
    validations = {}
    all_affected_rows = []
    
    # Run validations
    if 'soc' in df.columns:
        validations['soc_range'] = validate_soc_range(df)
        all_affected_rows.extend(validations['soc_range']['affected_rows'])
    
    if 'c_rate' in df.columns:
        validations['c_rate'] = validate_c_rate(df)
        all_affected_rows.extend(validations['c_rate']['affected_rows'])
    
    if 'timestamp' in df.columns:
        validations['data_continuity'] = validate_data_continuity(df)
        all_affected_rows.extend(validations['data_continuity']['affected_rows'])
    
    # Voltage jump validation
    if 'voltage' in df.columns:
        validations['voltage_jumps'] = validate_value_jumps(df, 'voltage', max_jump_percent=5.0)
        all_affected_rows.extend(validations['voltage_jumps']['affected_rows'])
    
    # Current jump validation (different thresholds for different step types)
    if 'current' in df.columns:
        max_jump = 20.0  # Default
        if step_type == 'rest':
            max_jump = 1.0  # Stricter for rest steps
        
        validations['current_jumps'] = validate_value_jumps(df, 'current', max_jump_percent=max_jump)
        all_affected_rows.extend(validations['current_jumps']['affected_rows'])
    
    # Temperature jump validation
    if 'temperature' in df.columns:
        validations['temperature_jumps'] = validate_value_jumps(df, 'temperature', max_jump_percent=10.0)
        all_affected_rows.extend(validations['temperature_jumps']['affected_rows'])
    
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
            
            issues_by_severity[severity].append({
                'validation': validation_name,
                'issue': issue
            })
    
    # Prepare summary
    total_rows = len(df)
    affected_pct = (len(unique_affected_rows) / total_rows * 100) if total_rows > 0 else 0
    
    summary = {
        'total_rows': total_rows,
        'affected_rows_count': len(unique_affected_rows),
        'affected_percentage': affected_pct,
        'total_issues': issues_count,
        'critical_issues': len(issues_by_severity['critical']),
        'warning_issues': len(issues_by_severity['warning']),
        'info_issues': len(issues_by_severity['info'])
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
    }
    
    return report