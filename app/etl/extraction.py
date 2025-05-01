"""
Extraction module for battery test data

This module provides functions for parsing and extracting data from
ChromaLex battery test files (Step.csv and Detail.csv).
"""
import os
import hashlib
import pandas as pd
from typing import List, Dict, Tuple, Optional, Union, Any
from datetime import datetime


# Define constants for required headers in ChromaLex format
# These are the column names in the original files
STEP_REQUIRED_HEADERS = [
    'Step Index',             # Step number
    'Step Type',              # Charge, discharge, rest
    'Start DateTime [s]',     # Start time (s since epoch)
    'End DateTime [s]',       # End time (s since epoch)
    'Start Voltage [V]',      # Initial voltage
    'End Voltage [V]',        # Final voltage
    'Current [A]',            # Current
    'Capacity [Ah]',          # Capacity
    'Energy [Wh]',            # Energy
    'Aux T1 [oC]',            # Temperature
]

DETAIL_REQUIRED_HEADERS = [
    'Step Index',             # Step number
    'DateTime [s]',           # Timestamp (s since epoch)
    'Voltage [V]',            # Voltage
    'Current [A]',            # Current
    'Aux T1 [oC]',            # Temperature
    'Capacity [Ah]',          # Capacity
    'Energy [Wh]',            # Energy
]

# Define mappings for standardized column names
STEP_COLUMN_MAPPING = {
    'Step Index': 'step_number',
    'Step Type': 'step_type',
    'Start DateTime [s]': 'start_time',
    'End DateTime [s]': 'end_time',
    'Start Voltage [V]': 'voltage_start',
    'End Voltage [V]': 'voltage_end',
    'Current [A]': 'current',
    'Capacity [Ah]': 'capacity',
    'Energy [Wh]': 'energy',
    'Aux T1 [oC]': 'temperature',
}

DETAIL_COLUMN_MAPPING = {
    'Step Index': 'step_number',
    'DateTime [s]': 'timestamp',
    'Voltage [V]': 'voltage',
    'Current [A]': 'current',
    'Aux T1 [oC]': 'temperature',
    'Capacity [Ah]': 'capacity',
    'Energy [Wh]': 'energy',
}

# Step type mapping (standardize different names for the same step types)
STEP_TYPE_MAPPING = {
    'CC_Chg': 'charge',
    'CC_DChg': 'discharge',
    'CCCV_Chg': 'charge',
    'Rest': 'rest',
    'Pause': 'rest',
    'charge': 'charge',
    'discharge': 'discharge',
    'rest': 'rest',
}


def validate_csv_format(file_path: str, expected_headers: List[str]) -> Tuple[bool, List[str], List[str]]:
    """
    Validate that a CSV file has the required headers.

    Args:
        file_path: Path to the CSV file
        expected_headers: List of required headers

    Returns:
        Tuple containing:
        - Boolean indicating if validation passed
        - List of missing headers
        - List of all headers found in the file
    """
    try:
        # Read only the header row to save memory
        df_headers = pd.read_csv(file_path, nrows=0)
        headers = df_headers.columns.tolist()
        
        # Find missing headers
        missing_headers = [h for h in expected_headers if h not in headers]
        
        # Return validation results
        return len(missing_headers) == 0, missing_headers, headers
    except Exception as e:
        # If file can't be read, return validation failure
        return False, expected_headers, [f"Error: {str(e)}"]


def map_step_types(df: pd.DataFrame, step_type_col: str = 'step_type') -> pd.DataFrame:
    """
    Map step types to standardized categories (charge, discharge, rest).

    Args:
        df: DataFrame containing step data
        step_type_col: Name of the column containing step types

    Returns:
        DataFrame with standardized step types
    """
    if step_type_col not in df.columns:
        raise ValueError(f"Column '{step_type_col}' not found in DataFrame")
    
    # Map step types
    df[step_type_col] = df[step_type_col].apply(
        lambda x: STEP_TYPE_MAPPING.get(x, 'unknown')
    )
    
    return df


def calculate_file_hash(file_path: str) -> str:
    """
    Calculate MD5 hash of a file for tracking processed files.

    Args:
        file_path: Path to the file

    Returns:
        MD5 hash as a hexadecimal string
    """
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        # Read file in chunks to handle large files
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def parse_step_csv(file_path: str) -> pd.DataFrame:
    """
    Parse Step.csv file from ChromaLex format.

    Args:
        file_path: Path to the Step.csv file

    Returns:
        DataFrame containing parsed step data with standardized column names
    """
    # Validate file format
    is_valid, missing_headers, found_headers = validate_csv_format(
        file_path, STEP_REQUIRED_HEADERS
    )
    
    if not is_valid:
        raise ValueError(
            f"Invalid Step.csv format. Missing required headers: {', '.join(missing_headers)}"
        )
    
    # Read the CSV file
    df = pd.read_csv(file_path)
    
    # Rename columns to standardized names
    df_renamed = df.rename(columns=STEP_COLUMN_MAPPING)
    
    # Keep only the columns we need
    columns_to_keep = list(STEP_COLUMN_MAPPING.values())
    df_filtered = df_renamed[columns_to_keep].copy()
    
    # Convert timestamps to datetime
    df_filtered['start_time'] = pd.to_datetime(df_filtered['start_time'], unit='s')
    df_filtered['end_time'] = pd.to_datetime(df_filtered['end_time'], unit='s')
    
    # Calculate duration in seconds
    df_filtered['duration'] = (df_filtered['end_time'] - df_filtered['start_time']).dt.total_seconds()
    
    # Map step types to standardized categories
    df_filtered = map_step_types(df_filtered)
    
    # Add calculated fields
    df_filtered['temperature_avg'] = df_filtered['temperature']
    
    # Drop duplicates (if any)
    df_filtered = df_filtered.drop_duplicates(subset=['step_number']).reset_index(drop=True)
    
    return df_filtered


def parse_detail_csv(file_path: str) -> pd.DataFrame:
    """
    Parse Detail.csv file from ChromaLex format.

    Args:
        file_path: Path to the Detail.csv file

    Returns:
        DataFrame containing parsed detail data with standardized column names
    """
    # Validate file format
    is_valid, missing_headers, found_headers = validate_csv_format(
        file_path, DETAIL_REQUIRED_HEADERS
    )
    
    if not is_valid:
        raise ValueError(
            f"Invalid Detail.csv format. Missing required headers: {', '.join(missing_headers)}"
        )
    
    # Read the CSV file
    df = pd.read_csv(file_path)
    
    # Rename columns to standardized names
    df_renamed = df.rename(columns=DETAIL_COLUMN_MAPPING)
    
    # Keep only the columns we need
    columns_to_keep = list(DETAIL_COLUMN_MAPPING.values())
    df_filtered = df_renamed[columns_to_keep].copy()
    
    # Convert timestamp to datetime
    df_filtered['timestamp'] = pd.to_datetime(df_filtered['timestamp'], unit='s')
    
    # Sort by step number and timestamp
    df_filtered = df_filtered.sort_values(['step_number', 'timestamp']).reset_index(drop=True)
    
    return df_filtered


def load_and_preprocess_files(step_file_path: str, detail_file_path: str) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
    """
    Load and preprocess both Step.csv and Detail.csv files.

    Args:
        step_file_path: Path to the Step.csv file
        detail_file_path: Path to the Detail.csv file

    Returns:
        Tuple containing:
        - DataFrame with processed step data
        - DataFrame with processed detail data
        - Dictionary with metadata about the files
    """
    # Validate files exist
    if not os.path.exists(step_file_path):
        raise FileNotFoundError(f"Step file not found: {step_file_path}")
    
    if not os.path.exists(detail_file_path):
        raise FileNotFoundError(f"Detail file not found: {detail_file_path}")
    
    # Calculate file hashes for tracking
    step_file_hash = calculate_file_hash(step_file_path)
    detail_file_hash = calculate_file_hash(detail_file_path)
    
    # Parse files
    step_df = parse_step_csv(step_file_path)
    detail_df = parse_detail_csv(detail_file_path)
    
    # Gather metadata
    metadata = {
        'step_file': {
            'path': step_file_path,
            'filename': os.path.basename(step_file_path),
            'hash': step_file_hash,
            'rows': len(step_df),
            'processed_at': datetime.now().isoformat(),
        },
        'detail_file': {
            'path': detail_file_path,
            'filename': os.path.basename(detail_file_path),
            'hash': detail_file_hash,
            'rows': len(detail_df),
            'processed_at': datetime.now().isoformat(),
        },
        'experiment': {
            'total_steps': step_df['step_number'].nunique(),
            'step_types': step_df['step_type'].value_counts().to_dict(),
            'start_time': step_df['start_time'].min().isoformat(),
            'end_time': step_df['end_time'].max().isoformat(),
        }
    }
    
    return step_df, detail_df, metadata