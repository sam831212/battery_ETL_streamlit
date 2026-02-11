"""
Extraction module for battery test data

This module provides functions for parsing and extracting data from
ChromaLex battery test files (Step.csv and Detail.csv).
"""
import os
import hashlib
import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional, Union, Any, cast
from datetime import datetime


# Helper function to detect header row and format

# Helper function to detect header row and format
def find_header_row(file_path: str, max_lines: int = 20, forced_format: Optional[str] = None) -> Tuple[int, str, List[str], str]:
    """
    Find the header row in a CSV file, detecting encoding and format.
    
    Args:
        file_path: Path to the CSV file
        max_lines: Number of lines to scan (default: 20)
        forced_format: Optional format to force ('chromalex' or 'chroma2')
        
    Returns:
        Tuple containing:
        - header_row_index: Index of the header row (0-based)
        - encoding: Detected encoding
        - headers: List of hedaers found
        - format_type: 'chromalex', 'chroma2', or 'unknown'
    """
    encodings = ['utf-8-sig', 'utf-8', 'big5', 'gbk']
    
    # Common headers to look for
    chromalex_markers = ['工步執行時間(秒)', '截止電壓(V)']
    chroma2_markers = ['工步執行時間(毫秒)', '執行時間(毫秒)']
    
    chroma2_markers = ['工步執行時間(毫秒)', '執行時間(毫秒)']
    
    # If forced_format is provided, we can optimize or validate against it
    # But we still need to find the header row
    
    for encoding in encodings:
        try:
            # Read first N lines as a dataframe without header
            # Use names to ensure all lines are read even if column counts vary
            # Remove on_bad_lines='skip' to see errors
            df = pd.read_csv(file_path, header=None, nrows=max_lines, encoding=encoding, names=list(range(200)))
            
            # Scan rows for headers
            for i, row in df.iterrows():
                # Convert row to string list, filtering out NaNs
                row_values = [str(x).strip() for x in row.tolist() if pd.notna(x)]
                full_line = " ".join(row_values)
                
                # Check for ChromaLex
                if any(marker in full_line for marker in chromalex_markers):
                    match_count = sum(1 for h in row_values if any(m in h for m in chromalex_markers))
                    if match_count >= 2:
                        return i, encoding, row_values, 'chromalex'

                # Check for Chroma2
                # Update markers to include fields present in Step file (e.g. 工步開始時間)
                if any(marker in full_line for marker in chroma2_markers + ['工步開始時間']):
                    # Check for existence of any key markers
                    # Relaxed check: if we see "工步執行時間(毫秒)" or "執行時間(毫秒)", it's likely Chroma 2
                    if '工步執行時間(毫秒)' in row_values or '執行時間(毫秒)' in row_values:
                         return i, encoding, row_values, 'chroma2'
                    
                    # Fallback strict check if primary markers missing (unlikely if loop entered)
                    match_count = sum(1 for h in row_values if h in chroma2_markers or any(m in h for m in chroma2_markers))
                    if match_count >= 1: # Relaxed from 2 to 1 as file might only have one of them
                         return i, encoding, row_values, 'chroma2'
                
                # If forced_format is specified, check against relevant markers regardless of full match count
                if forced_format:
                    if forced_format == 'chroma2':
                        # Validating against Chroma 2 markers specifically
                        if any(marker in full_line for marker in chroma2_markers):
                             return i, encoding, row_values, 'chroma2'
                    elif forced_format == 'chromalex':
                        # Validating against ChromaLex markers specifically
                        if any(marker in full_line for marker in chromalex_markers):
                             return i, encoding, row_values, 'chromalex'
                             
        except Exception as e:
            # Log error
            print(f"Error checking encoding {encoding}: {e}")
            # Try next encoding
            continue
            
    # Default fallback if detection fails
    return 0, 'utf-8', [], 'unknown'

# Helper function to convert numpy types to Python native types
def convert_numpy_types(obj):
    """
    Convert numpy data types to Python native types for compatibility with database storage.
    
    Args:
        obj: Object containing numpy data types
        
    Returns:
        Object with numpy types converted to Python native types
    """
    if isinstance(obj, (np.integer, np.int64, np.int32, np.int16, np.int8)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float64, np.float32, np.float16)):
        return float(obj)
    elif isinstance(obj, (np.ndarray, )):
        return convert_numpy_types(obj.tolist())
    elif isinstance(obj, (dict, )):
        return {key: convert_numpy_types(value) for key, value in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [convert_numpy_types(item) for item in obj]
    elif hasattr(obj, 'isoformat'):  # Handle datetime-like objects
        return obj.isoformat()
    return obj


# Define constants for required headers in ChromaLex format
# Chinese version headers from the provided CSV files
STEP_REQUIRED_HEADERS_CHROMALEX = [
    '工步',  # Step number
    '工步種類',  # Step type
    '日期時間',  # Start time
    '工步執行時間(秒)',  # Step duration
    '截止電壓(V)',  # Ending voltage
    '能量(Wh)',  # Energy
    '截止電量(Ah)',  # Capacity
    '總電量(Ah)',  # Total capacity
    '功率(W)',  # Power
    'Aux T1',  # Temperature
]

DETAIL_REQUIRED_HEADERS_CHROMALEX = [
    '工步',  # Step number
    '執行時間(秒)',
    '工步執行時間(秒)',  # Execution time
    '電壓(V)',  # Voltage
    '電流(A)',  # Current
    'Aux T1',  # Temperature
    '電量(Ah)',  # Capacity
    '能量(Wh)',  # Energy
]

# Chroma 2 English version headers
# Chroma 2 English version headers (Actually Chinese headers with ms units)
STEP_REQUIRED_HEADERS_CHROMA2 = [
    '工步',
    '工步種類',
    '工步開始時間',
    '工步執行時間(毫秒)',
    '截止電壓(V)',
    '截止電流(A)',
    '截止電量(Ah)',
    '瓦小時',
]

DETAIL_REQUIRED_HEADERS_CHROMA2 = [
    '工步',
    '工步種類',
    '測試時間',
    '執行時間(毫秒)',
    '電壓(V)',
    '電流(A)',
    '電量(Ah)',
    '瓦小時',
]

# Use the ChromaLex headers as default
# Default required headers (will be determined dynamically)
STEP_REQUIRED_HEADERS = STEP_REQUIRED_HEADERS_CHROMALEX
DETAIL_REQUIRED_HEADERS = DETAIL_REQUIRED_HEADERS_CHROMALEX

# Chinese version column mappings based on the provided CSV files
STEP_COLUMN_MAPPING_CHROMALEX = {
    '工步': 'step_number',  # Alternative column name
    '工步種類': 'step_type',
    '日期時間': 'start_time',
    '工步執行時間(秒)': 'duration',
    '截止電壓(V)': 'voltage_end',
    '截止電流(A)': 'current',
    '能量(Wh)': 'energy',
    '截止電量(Ah)': 'capacity',
    '總電量(Ah)': 'total_capacity',
    '功率(W)': 'power',
    'Aux T1': 'temperature',
}

DETAIL_COLUMN_MAPPING_CHROMALEX = {
    '工步': 'step_number',  # Step number
    '執行時間(秒)': 'execution_time_alt',  # Alternative name for execution time
    '工步執行時間(秒)': 'execution_time',  # Step execution time in seconds
    '電壓(V)': 'voltage', 
    '電流(A)': 'current',
    'Aux T1': 'temperature',
    '電量(Ah)': 'capacity',
    '能量(Wh)': 'energy',
}



# Chroma 2 English version column mappings
# Chroma 2 English version column mappings
STEP_COLUMN_MAPPING_CHROMA2 = {
    '工步': 'step_number',
    '工步種類': 'step_type',
    '工步開始時間': 'start_time',
    '工步執行時間(毫秒)': 'duration', # Will convert from ms to s
    '截止電壓(V)': 'voltage_end',
    '截止電流(A)': 'current',
    '截止電量(Ah)': 'capacity',
    '瓦小時': 'energy',
    '總電量(Ah)': 'total_capacity',
    '狀態': 'status',
}

DETAIL_COLUMN_MAPPING_CHROMA2 = {
    '工步': 'step_number',
    '工步種類': 'step_type', # Map step type for coloring plots
    '測試時間': 'timestamp', # Map test time for time-axis
    '執行時間(毫秒)': 'execution_time', # Will convert from ms to s
    '工步執行時間(毫秒)': 'execution_time_alt', # Use as alternative time column for plotting (Relative time)
    '電壓(V)': 'voltage',
    '電流(A)': 'current',
    '電量(Ah)': 'capacity',
    '瓦小時': 'energy',
    'Param1': 'temperature',
}

# Use ChromaLex mappings as default
# Default mappings (will be determined dynamically)
STEP_COLUMN_MAPPING = STEP_COLUMN_MAPPING_CHROMALEX
DETAIL_COLUMN_MAPPING = DETAIL_COLUMN_MAPPING_CHROMALEX

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
    # Chroma 2 English types
    'REST': 'rest',
    'CC-CV Charge': 'charge',
    'CC Charge': 'charge',
    'CC Discharge': 'discharge',
    'CP Charge': 'charge',
    'CP Discharge': 'discharge',
    # Chinese step types from the sample data
    'CC-CV充電': 'charge',
    'CC放電': 'discharge',
    'CC充電': 'charge',
    '靜置': 'rest',
    '溫箱控制': 'rest',
    'CP充電': 'charge',
    'CP放電': 'discharge',
    '超級CP充電': 'charge',
    '超級CP放電': 'discharge',
    '電流波形': 'waveform',
    '功率波形': 'waveform'
}


def validate_csv_format(
        file_path: str,
        expected_headers: List[str],
        forced_format: Optional[str] = None) -> Tuple[bool, List[str], List[str]]:
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
        # Detect header row and format
        header_row, encoding, headers, detected_format = find_header_row(file_path, forced_format=forced_format)
        
        # Override format if forced
        if forced_format:
            detected_format = forced_format
        
        # If headers were found during detection, use them
        if not headers:
             # Fallback to reading first row if detection failed
             df_headers = pd.read_csv(file_path, nrows=0)
             headers = df_headers.columns.tolist()
        
        # Determine which headers to check against
        headers_to_check = expected_headers
        if detected_format == 'chroma2':
            # Identify if this is likely Step or Detail file based on markers
            # Detail file has '測試時間', Step file has '工步開始時間'
            if '工步開始時間' in headers or '截止電壓(V)' in headers:
                headers_to_check = STEP_REQUIRED_HEADERS_CHROMA2
            else:
                headers_to_check = DETAIL_REQUIRED_HEADERS_CHROMA2
        elif detected_format == 'chromalex':
             if '日期時間' in headers or '截止電壓(V)' in headers:
                 headers_to_check = STEP_REQUIRED_HEADERS_CHROMALEX
             else:
                 headers_to_check = DETAIL_REQUIRED_HEADERS_CHROMALEX
                 
        # Try alternate validation method - check if all required fields exist by prefix/semantic meaning
        # rather than exact match, to handle encoding issues
        critical_missing = []
        for expected in headers_to_check:
            found_match = False
            # Try exact match first
            if expected in headers:
                found_match = True
            # If exact match fails, try finding headers with similar meaning
            else:
                # Create mapping of semantic meaning -> actual header
                if expected == '工步':  # Step number
                    if any('工步' in h or 'step' in h.lower() or 'index' in h.lower() for h in headers):
                        found_match = True
                elif expected == '工步種類':  # Step type
                    if any('種類' in h or 'type' in h.lower() or 'mode' in h.lower() for h in headers):
                        found_match = True
                elif expected == '日期時間':  # Start time
                    if any('時間' in h or 'date' in h.lower() or 'time' in h.lower() or 'start' in h.lower() for h in headers):
                        found_match = True
                # Add more mappings as needed for other critical headers
            
            if not found_match:
                critical_missing.append(expected)
        
        # Find missing headers - standard way
        missing_headers = [h for h in headers_to_check if h not in headers]
        
        # If semantic validation worked but standard validation failed,
        # it might be an encoding issue - proceed with caution
        if not critical_missing and missing_headers:
            print("Warning: Some headers didn't match exactly but similar fields were found.")
            
        # Return validation results based on critical missing headers
        if not critical_missing:
            return True, [], headers  # Return success if we found semantic matches
        else:
            return False, missing_headers, headers  # Return the full list for user info
            
    except Exception as e:
        # If file can't be read, return validation failure with detailed error
        print(f"Error validating CSV format: {str(e)}")
        return False, expected_headers, [f"Error: {str(e)}"]


def map_step_types(df: pd.DataFrame,
                   step_type_col: str = 'step_type') -> pd.DataFrame:
    """
    Map step types to standardized categories (charge, discharge, rest).
    Preserves original step type in original_step_type column.

    Args:
        df: DataFrame containing step data
        step_type_col: Name of the column containing step types

    Returns:
        DataFrame with standardized step types and original step types preserved
    """
    if step_type_col not in df.columns:
        raise ValueError(f"Column '{step_type_col}' not found in DataFrame")

    # Save original step types
    df['original_step_type'] = df[step_type_col].copy()

    # Map step types
    df[step_type_col] = df[step_type_col].apply(
        lambda x: STEP_TYPE_MAPPING.get(x, 'unknown'))

    return df



def parse_step_csv(file_path: str, forced_format: Optional[str] = None) -> pd.DataFrame:
    """
    Parse Step.csv file from ChromaLex format.

    Args:
        file_path: Path to the Step.csv file

    Returns:
        DataFrame containing parsed step data with standardized column names
    """
    try:
        # Detect header row and encoding
        header_row, encoding, detected_headers, detected_format = find_header_row(file_path, forced_format=forced_format)
        
        # Override format if forced
        if forced_format:
            detected_format = forced_format
        
        # Read with correct encoding and header row
        df = pd.read_csv(file_path, header=header_row, encoding=encoding)
        headers = df.columns.tolist()

        # Use ChromaLex mappings default
        column_mapping = STEP_COLUMN_MAPPING
        expected_headers = STEP_REQUIRED_HEADERS

        # Use validation/detection result
        if detected_format == 'chroma2':
             column_mapping = STEP_COLUMN_MAPPING_CHROMA2
             expected_headers = STEP_REQUIRED_HEADERS_CHROMA2
        elif detected_format == 'chromalex':
             column_mapping = STEP_COLUMN_MAPPING_CHROMALEX
             expected_headers = STEP_REQUIRED_HEADERS_CHROMALEX
             
        # Validate that the file has the required headers
        required_headers_found = all(h in headers for h in expected_headers)

        if not required_headers_found:
             # If detection failed but we are here, try to fallback or error out with details
             missing = [h for h in expected_headers if h not in headers]
             raise ValueError(f"Missing required headers ({detected_format}): {', '.join(missing)}")

        # Rename columns based on the mapping
        df_renamed = df.rename(columns=column_mapping)

        # Filter to keep only mapped columns that exist in our mapping
        mapped_columns = set(column_mapping.keys()).intersection(set(headers))
        standardized_columns = [
            column_mapping[col] for col in mapped_columns if col in headers
        ]
        df_filtered = df_renamed[standardized_columns].copy()

        # Process date/time fields - ChromaLex format has date as string
        # 已移除 start_time/end_time 處理
        
        # Handle Chroma 2 unit conversion (ms -> s)
        if detected_format == 'chroma2':
            if 'duration' in df_filtered.columns:
                df_filtered['duration'] = df_filtered['duration'].astype(float) / 1000.0

        # If we miss voltage_start, add it from previous step's voltage_end
        if 'voltage_start' not in df_filtered.columns:
            df_filtered['voltage_start'] = None

            # Sort by step_number to ensure correct order
            if 'step_number' in df_filtered.columns:
                df_filtered = df_filtered.sort_values('step_number')

                # For each step, set voltage_start to the previous step's voltage_end
                for i in range(1, len(df_filtered)):
                    prev_idx = df_filtered.index[i - 1]
                    current_idx = df_filtered.index[i]
                    df_filtered.at[current_idx,
                                   'voltage_start'] = df_filtered.at[
                                       prev_idx, 'voltage_end']

        # Calculate duration if it's not already present
        # 已移除 duration 依賴 start_time/end_time 的計算

        # Map step types to standardized categories if step_type column exists
        if 'step_type' in df_filtered.columns:
            df_filtered = map_step_types(df_filtered)
        else:
            df_filtered['step_type'] = 'unknown'

        # Add temperature_end and temperature_start columns
        if 'temperature' in df_filtered.columns:
            df_filtered = df_filtered.rename(columns={'temperature': 'temperature_end'})
            df_filtered['temperature_start'] = None
            if 'step_number' in df_filtered.columns:
                df_filtered = df_filtered.sort_values('step_number')
                for i in range(1, len(df_filtered)):
                    prev_idx = df_filtered.index[i - 1]
                    current_idx = df_filtered.index[i]
                    df_filtered.at[current_idx, 'temperature_start'] = df_filtered.at[prev_idx, 'temperature_end']
                    first_idx = df_filtered.index[0]
                    if pd.isnull(df_filtered.at[first_idx, 'temperature_start']):
                        df_filtered.at[first_idx, 'temperature_start'] = df_filtered.at[first_idx, 'temperature_end']
        else:
            df_filtered['temperature_end'] = None
            df_filtered['temperature_start'] = None

        # Drop duplicates if any
        if 'step_number' in df_filtered.columns:
            df_filtered = df_filtered.drop_duplicates(
                subset=['step_number']).reset_index(drop=True)

        return df_filtered

    except Exception as e:
        raise ValueError(f"Error parsing Step.csv: {str(e)}")


def parse_detail_csv(file_path: str, forced_format: Optional[str] = None) -> pd.DataFrame:
    """
    Parse Detail.csv file from ChromaLex format.

    Args:
        file_path: Path to the Detail.csv file

    Returns:
        DataFrame containing parsed detail data with standardized column names
    """
    try:
        # Detect header row and encoding
        header_row, encoding, detected_headers, detected_format = find_header_row(file_path, forced_format=forced_format)
        
        # Override format if forced
        if forced_format:
            detected_format = forced_format
        
        # Read with correct encoding and header row
        df = pd.read_csv(file_path, header=header_row, encoding=encoding)
        headers = df.columns.tolist()
        
        # Use ChromaLex mappings default
        column_mapping = DETAIL_COLUMN_MAPPING
        expected_headers = DETAIL_REQUIRED_HEADERS
        
        # Use validation/detection result
        if detected_format == 'chroma2':
            column_mapping = DETAIL_COLUMN_MAPPING_CHROMA2
            expected_headers = DETAIL_REQUIRED_HEADERS_CHROMA2
        elif detected_format == 'chromalex':
            column_mapping = DETAIL_COLUMN_MAPPING_CHROMALEX
            expected_headers = DETAIL_REQUIRED_HEADERS_CHROMALEX

        # Validate that the file has the required headers
        required_headers_found = all(h in headers for h in expected_headers)

        if not required_headers_found:
             missing = [h for h in expected_headers if h not in headers]
             raise ValueError(f"Missing required headers ({detected_format}): {', '.join(missing)}")

        # Rename columns based on the mapping
        df_renamed = df.rename(columns=column_mapping)

        # Filter to keep only mapped columns that exist in our mapping
        mapped_columns = set(column_mapping.keys()).intersection(set(headers))
        standardized_columns = [
            column_mapping[col] for col in mapped_columns if col in headers
        ]
        df_filtered = df_renamed[standardized_columns].copy()

        # Process execution_time - make sure it's a float value
        if 'execution_time' in df_filtered.columns:
            # Ensure execution_time is stored as a float representing seconds
            df_filtered['execution_time'] = df_filtered['execution_time'].astype(float)
            
            # Sort by step number and execution_time
            if 'step_number' in df_filtered.columns:
                df_filtered = df_filtered.sort_values(['step_number', 'execution_time']).reset_index(drop=True)
                
        # Handle Chroma 2 unit conversion (ms -> s)
        if detected_format == 'chroma2':
            if 'execution_time' in df_filtered.columns:
                df_filtered['execution_time'] = df_filtered['execution_time'] / 1000.0
            
            if 'execution_time_alt' in df_filtered.columns:
                df_filtered['execution_time_alt'] = df_filtered['execution_time_alt'] / 1000.0
                
            # Parse timestamp for Chroma 2
            if 'timestamp' in df_filtered.columns:
                try:
                    df_filtered['timestamp'] = pd.to_datetime(df_filtered['timestamp'])
                except Exception as e:
                    print(f"Warning: Failed to parse timestamp in Detail file: {e}")
            
            # Map step types if step_type column exists (Chroma 2 has '工步種類' -> 'step_type')
            if 'step_type' in df_filtered.columns:
                df_filtered = map_step_types(df_filtered, step_type_col='step_type')
        
        return df_filtered

    except Exception as e:
        raise ValueError(f"Error parsing Detail.csv: {str(e)}")


def load_and_preprocess_files(
    step_file_path: str,
    detail_file_path: str,
    nominal_capacity: Optional[float] = None,
    apply_transformations: bool = True,
    forced_format: Optional[str] = None
) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
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


    # Parse files
    step_df = parse_step_csv(step_file_path, forced_format=forced_format)
    detail_df = parse_detail_csv(detail_file_path, forced_format=forced_format)

    # Apply transformation functions if requested and we have nominal_capacity
    if apply_transformations and nominal_capacity is not None and nominal_capacity > 0:
        try:
            # Import here to avoid circular imports
            from app.etl.transformation import transform_data
            step_df, detail_df = transform_data(step_df, detail_df,
                                                nominal_capacity)
        except Exception as e:
            # Log the error but continue with the parsing
            print(f"Error applying transformations: {str(e)}")
            # 設置默認值
            step_df['c_rate'] = 0.0
            detail_df['c_rate'] = 0.0

    # Gather metadata
    metadata = {
        'step_file': {
            'path': step_file_path,
            'filename': os.path.basename(step_file_path),
            'hash': step_file_hash,
            'rows': int(len(step_df)),
            'processed_at': datetime.now().isoformat(),
        },
        'detail_file': {
            'path': detail_file_path,
            'filename': os.path.basename(detail_file_path),
            'hash': detail_file_hash,
            'rows': int(len(detail_df)),
            'processed_at': datetime.now().isoformat(),
        },
        'experiment': {
            'total_steps':
            int(step_df['step_number'].nunique()),
            'step_types':
            convert_numpy_types(step_df['step_type'].value_counts().to_dict())
        }
    }

    # Add transformation metadata if available
    if apply_transformations and nominal_capacity is not None and nominal_capacity > 0:
        metadata['experiment']['nominal_capacity'] = float(nominal_capacity)

        # Add SOC range if available
        if 'soc_end' in step_df.columns:
            metadata['experiment']['soc_min'] = float(step_df['soc_end'].min())
            metadata['experiment']['soc_max'] = float(step_df['soc_end'].max())

        # Add C-rate information if available
        if 'c_rate' in step_df.columns:
            metadata['experiment']['c_rate_min'] = float(
                step_df['c_rate'].min())
            metadata['experiment']['c_rate_max'] = float(
                step_df['c_rate'].max())
            metadata['experiment']['c_rate_avg'] = float(
                step_df['c_rate'].mean())

    return step_df, detail_df, metadata
