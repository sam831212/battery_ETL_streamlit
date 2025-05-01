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
# These are the column names in the original files for English version
STEP_REQUIRED_HEADERS_EN = [
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

DETAIL_REQUIRED_HEADERS_EN = [
    'Step Index',             # Step number
    'DateTime [s]',           # Timestamp (s since epoch)
    'Voltage [V]',            # Voltage
    'Current [A]',            # Current
    'Aux T1 [oC]',            # Temperature
    'Capacity [Ah]',          # Capacity
    'Energy [Wh]',            # Energy
]

# Chinese version headers from the provided CSV files
STEP_REQUIRED_HEADERS_ZH = [
    '工步編號',               # Step number
    '工步種類',               # Step type
    '日期時間',               # Start time
    '工步執行時間(秒)',       # Step duration
    '截止電壓(V)',            # Ending voltage
    '能量(Wh)',               # Energy
    '截止電量(Ah)',           # Capacity
    '功率(W)',                # Power
    'Aux T1',                 # Temperature
]

DETAIL_REQUIRED_HEADERS_ZH = [
    '工步編號',               # Step number
    '實際開始時間',           # Start time
    '電壓(V)',                # Voltage
    '電流(A)',                # Current
    'Aux T1',                 # Temperature
    '電量(Ah)',               # Capacity
    '能量(Wh)',               # Energy
]

# Use the English headers as default, but include Chinese as alternatives
STEP_REQUIRED_HEADERS = STEP_REQUIRED_HEADERS_EN
DETAIL_REQUIRED_HEADERS = DETAIL_REQUIRED_HEADERS_EN

# Define mappings for standardized column names
STEP_COLUMN_MAPPING_EN = {
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

DETAIL_COLUMN_MAPPING_EN = {
    'Step Index': 'step_number',
    'DateTime [s]': 'timestamp',
    'Voltage [V]': 'voltage',
    'Current [A]': 'current',
    'Aux T1 [oC]': 'temperature',
    'Capacity [Ah]': 'capacity',
    'Energy [Wh]': 'energy',
}

# Chinese version column mappings based on the provided CSV files
STEP_COLUMN_MAPPING_ZH = {
    '工步編號': 'step_number',
    '工步': 'step_number',  # Alternative column name
    '工步種類': 'step_type',
    '日期時間': 'start_time',
    '工步執行時間(秒)': 'duration',
    '截止電壓(V)': 'voltage_end',
    '截止電流(A)': 'current',
    '能量(Wh)': 'energy',
    '截止電量(Ah)': 'capacity',
    '功率(W)': 'power',
    'Aux T1': 'temperature',
}

DETAIL_COLUMN_MAPPING_ZH = {
    '工步編號': 'step_number',
    '工步': 'step_number',  # Alternative column name
    '實際開始時間': 'timestamp',
    '電壓(V)': 'voltage',
    '電流(A)': 'current',
    'Aux T1': 'temperature',
    '電量(Ah)': 'capacity',
    '能量(Wh)': 'energy',
}

# Use English mappings as default
STEP_COLUMN_MAPPING = STEP_COLUMN_MAPPING_EN
DETAIL_COLUMN_MAPPING = DETAIL_COLUMN_MAPPING_EN

# Step type mapping (standardize different names for the same step types)
STEP_TYPE_MAPPING = {
    # English step types
    'CC_Chg': 'charge',
    'CC_DChg': 'discharge',
    'CCCV_Chg': 'charge',
    'Rest': 'rest',
    'Pause': 'rest',
    'charge': 'charge',
    'discharge': 'discharge',
    'rest': 'rest',
    # Chinese step types from the sample data
    'CC-CV充電': 'charge',
    'CC放電': 'discharge',
    '靜置': 'rest',
    '溫箱控制': 'rest',
    'CP充電': 'charge',
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
    # Try to read the CSV file to determine format (Chinese or English)
    try:
        df = pd.read_csv(file_path)
        headers = df.columns.tolist()
        
        # Determine if this is Chinese format or English format
        chinese_format = any('工步' in h for h in headers) or any('循環' in h for h in headers)
        
        if chinese_format:
            # Use Chinese mappings for this file
            column_mapping = STEP_COLUMN_MAPPING_ZH
            expected_headers = STEP_REQUIRED_HEADERS_ZH
        else:
            # Use English mappings
            column_mapping = STEP_COLUMN_MAPPING_EN
            expected_headers = STEP_REQUIRED_HEADERS_EN
            
        # Validate that the file has the required headers for its format
        required_headers_found = all(h in headers for h in expected_headers)
        
        if not required_headers_found:
            missing = [h for h in expected_headers if h not in headers]
            raise ValueError(f"Missing required headers for format: {', '.join(missing)}")
        
        # Now we rename columns based on the detected format
        df_renamed = df.rename(columns=column_mapping)
        
        # Filter to keep only mapped columns that exist in our mapping
        mapped_columns = set(column_mapping.keys()).intersection(set(headers))
        standardized_columns = [column_mapping[col] for col in mapped_columns if col in headers]
        df_filtered = df_renamed[standardized_columns].copy()
        
        # Special processing for Chinese format
        if chinese_format:
            # In Chinese format, date is a string like '02/20/2025 09:20:54'
            # We need to convert to datetime
            if 'start_time' in df_filtered.columns:
                df_filtered['start_time'] = pd.to_datetime(df_filtered['start_time'])
            
            # Check if we have end_time or need to calculate it from start_time and duration
            if 'end_time' not in df_filtered.columns and 'duration' in df_filtered.columns:
                # Calculate end_time from start_time + duration
                df_filtered['end_time'] = df_filtered['start_time'] + pd.to_timedelta(df_filtered['duration'], unit='s')
            
            # If we miss voltage_start, set it to None
            if 'voltage_start' not in df_filtered.columns:
                df_filtered['voltage_start'] = None
                
        else:
            # For English format, convert timestamps to datetime if they're in epoch format
            if 'start_time' in df_filtered.columns:
                df_filtered['start_time'] = pd.to_datetime(df_filtered['start_time'], unit='s')
            
            if 'end_time' in df_filtered.columns:
                df_filtered['end_time'] = pd.to_datetime(df_filtered['end_time'], unit='s')
        
        # Calculate duration if it's not already present
        if 'duration' not in df_filtered.columns and 'start_time' in df_filtered.columns and 'end_time' in df_filtered.columns:
            df_filtered['duration'] = (df_filtered['end_time'] - df_filtered['start_time']).dt.total_seconds()
        
        # Map step types to standardized categories if step_type column exists
        if 'step_type' in df_filtered.columns:
            df_filtered = map_step_types(df_filtered)
        else:
            df_filtered['step_type'] = 'unknown'
        
        # Add temperature_avg if temperature exists
        if 'temperature' in df_filtered.columns:
            df_filtered['temperature_avg'] = df_filtered['temperature']
        else:
            df_filtered['temperature_avg'] = None
        
        # Drop duplicates if any
        if 'step_number' in df_filtered.columns:
            df_filtered = df_filtered.drop_duplicates(subset=['step_number']).reset_index(drop=True)
        
        return df_filtered
        
    except Exception as e:
        raise ValueError(f"Error parsing Step.csv: {str(e)}")


def parse_detail_csv(file_path: str) -> pd.DataFrame:
    """
    Parse Detail.csv file from ChromaLex format.

    Args:
        file_path: Path to the Detail.csv file

    Returns:
        DataFrame containing parsed detail data with standardized column names
    """
    # Try to read the CSV file to determine format (Chinese or English)
    try:
        df = pd.read_csv(file_path)
        headers = df.columns.tolist()
        
        # Determine if this is Chinese format or English format
        chinese_format = any('工步' in h for h in headers) or any('循環' in h for h in headers)
        
        if chinese_format:
            # Use Chinese mappings for this file
            column_mapping = DETAIL_COLUMN_MAPPING_ZH
            expected_headers = DETAIL_REQUIRED_HEADERS_ZH
        else:
            # Use English mappings
            column_mapping = DETAIL_COLUMN_MAPPING_EN
            expected_headers = DETAIL_REQUIRED_HEADERS_EN
            
        # Validate that the file has the required headers for its format
        required_headers_found = all(h in headers for h in expected_headers)
        
        if not required_headers_found:
            missing = [h for h in expected_headers if h not in headers]
            raise ValueError(f"Missing required headers for format: {', '.join(missing)}")
        
        # Now we rename columns based on the detected format
        df_renamed = df.rename(columns=column_mapping)
        
        # Filter to keep only mapped columns that exist in our mapping
        mapped_columns = set(column_mapping.keys()).intersection(set(headers))
        standardized_columns = [column_mapping[col] for col in mapped_columns if col in headers]
        df_filtered = df_renamed[standardized_columns].copy()
        
        # Special processing for Chinese format
        if chinese_format:
            # In Chinese format, date is a string like '02/20/2025 09:20:54'
            # We need to convert to datetime
            if 'timestamp' in df_filtered.columns:
                df_filtered['timestamp'] = pd.to_datetime(df_filtered['timestamp'])
        else:
            # For English format, convert timestamp to datetime if it's in epoch format
            if 'timestamp' in df_filtered.columns:
                df_filtered['timestamp'] = pd.to_datetime(df_filtered['timestamp'], unit='s')
        
        # Sort by step number and timestamp if both columns exist
        if 'step_number' in df_filtered.columns and 'timestamp' in df_filtered.columns:
            df_filtered = df_filtered.sort_values(['step_number', 'timestamp']).reset_index(drop=True)
        
        return df_filtered
        
    except Exception as e:
        raise ValueError(f"Error parsing Detail.csv: {str(e)}")


def load_and_preprocess_files(step_file_path: str, detail_file_path: str, 
                         nominal_capacity: float = None,
                         apply_transformations: bool = True) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
    """
    Load and preprocess both Step.csv and Detail.csv files.

    Args:
        step_file_path: Path to the Step.csv file
        detail_file_path: Path to the Detail.csv file
        nominal_capacity: Optional nominal capacity of the battery in Ah
            Required for transformation calculations such as C-rate
        apply_transformations: Whether to apply transformation functions (default: True)
            Set to False if you only want to parse the files without additional calculations

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
    
    # Apply transformation functions if requested and we have nominal_capacity
    if apply_transformations and nominal_capacity is not None and nominal_capacity > 0:
        try:
            # Import here to avoid circular imports
            from app.etl.transformation import transform_data
            step_df, detail_df = transform_data(step_df, detail_df, nominal_capacity)
        except Exception as e:
            # Log the error but continue with the parsing
            print(f"Error applying transformations: {str(e)}")
    
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
    
    # Add transformation metadata if available
    if apply_transformations and nominal_capacity is not None:
        metadata['experiment']['nominal_capacity'] = nominal_capacity
        
        # Add SOC range if available
        if 'soc_end' in step_df.columns:
            metadata['experiment']['soc_min'] = step_df['soc_end'].min()
            metadata['experiment']['soc_max'] = step_df['soc_end'].max()
        
        # Add C-rate information if available
        if 'c_rate' in step_df.columns:
            metadata['experiment']['c_rate_min'] = step_df['c_rate'].min()
            metadata['experiment']['c_rate_max'] = step_df['c_rate'].max()
            metadata['experiment']['c_rate_avg'] = step_df['c_rate'].mean()
    
    return step_df, detail_df, metadata