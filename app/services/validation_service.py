"""Logic for validating file formats and data"""


import pandas as pd
import streamlit as st


from typing import Any, Dict, List, Tuple


def validate_files(
    step_file_path: str,
    detail_file_path: str
) -> Tuple[bool, bool, List[str], List[str], List[str], List[str]]:
    """
    Validate the format of step and detail files.

    Args:
        step_file_path: Path to the step file
        detail_file_path: Path to the detail file

    Returns:
        Tuple containing:
        - Whether step file is valid
        - Whether detail file is valid
        - Missing headers in step file
        - Missing headers in detail file
        - All headers in step file
        - All headers in detail file
    """
    # Required headers for each file type
    REQUIRED_STEP_HEADERS = ["Step_Index", "Step_Type", "Step_Name", "Status"]
    REQUIRED_DETAIL_HEADERS = ["Date_Time", "Voltage", "Current"]

    try:
        # Read the first few rows to get headers
        step_df = pd.read_csv(step_file_path, nrows=1)
        detail_df = pd.read_csv(detail_file_path, nrows=1)

        # Get all headers
        step_headers = step_df.columns.tolist()
        detail_headers = detail_df.columns.tolist()

        # Check for missing required headers
        step_missing = [h for h in REQUIRED_STEP_HEADERS if h not in step_headers]
        detail_missing = [h for h in REQUIRED_DETAIL_HEADERS if h not in detail_headers]

        # Determine if files are valid
        step_valid = len(step_missing) == 0
        detail_valid = len(detail_missing) == 0

        return step_valid, detail_valid, step_missing, detail_missing, step_headers, detail_headers

    except Exception as e:
        st.error(f"Error validating files: {str(e)}")
        return False, False, REQUIRED_STEP_HEADERS, REQUIRED_DETAIL_HEADERS, [], []


def generate_validation_results(
    step_df: pd.DataFrame,
    detail_df: pd.DataFrame
) -> Tuple[bool, Dict[str, Any], Dict[str, Any]]:
    """
    Generate validation reports for step and detail data.

    Args:
        step_df: Step data DataFrame
        detail_df: Detail data DataFrame

    Returns:
        Tuple containing:
        - Overall validation status
        - Step validation report
        - Detail validation report
    """
    step_report = {}
    detail_report = {}

    # Step validation
    step_report["row_count"] = len(step_df)
    step_report["column_count"] = len(step_df.columns)
    step_report["columns"] = step_df.columns.tolist()

    # Check for required step columns
    required_step_cols = ["Step_Index", "Step_Type", "Step_Name"]
    step_report["missing_columns"] = [col for col in required_step_cols if col not in step_df.columns]
    step_report["has_required_columns"] = len(step_report["missing_columns"]) == 0

    # Check step types
    if "Step_Type" in step_df.columns:
        step_report["step_types"] = step_df["Step_Type"].value_counts().to_dict()
    else:
        step_report["step_types"] = {}

    # Time range check
    if "Date_Time" in step_df.columns:
        try:
            step_report["start_time"] = step_df["Date_Time"].min()
            step_report["end_time"] = step_df["Date_Time"].max()
            step_report["time_range_valid"] = True
        except Exception:
            step_report["time_range_valid"] = False
    else:
        step_report["time_range_valid"] = False

    # Detail validation
    detail_report["row_count"] = len(detail_df)
    detail_report["column_count"] = len(detail_df.columns)
    detail_report["columns"] = detail_df.columns.tolist()

    # Check for required detail columns
    required_detail_cols = ["Date_Time", "Voltage", "Current"]
    detail_report["missing_columns"] = [col for col in required_detail_cols if col not in detail_df.columns]
    detail_report["has_required_columns"] = len(detail_report["missing_columns"]) == 0

    # Check value ranges
    for col in ["Voltage", "Current", "Capacity"]:
        if col in detail_df.columns:
            try:
                detail_report[f"{col}_min"] = float(detail_df[col].min())
                detail_report[f"{col}_max"] = float(detail_df[col].max())
                detail_report[f"{col}_mean"] = float(detail_df[col].mean())
            except Exception:
                detail_report[f"{col}_valid"] = False
        else:
            detail_report[f"{col}_valid"] = False

    # Time range check for detail file
    if "Date_Time" in detail_df.columns:
        try:
            detail_report["start_time"] = detail_df["Date_Time"].min()
            detail_report["end_time"] = detail_df["Date_Time"].max()
            detail_report["time_range_valid"] = True
        except Exception:
            detail_report["time_range_valid"] = False
    else:
        detail_report["time_range_valid"] = False

    # Overall validation status
    validation_status = (
        step_report.get("has_required_columns", False) and
        detail_report.get("has_required_columns", False) and
        step_report.get("row_count", 0) > 0 and
        detail_report.get("row_count", 0) > 0
    )

    return validation_status, step_report, detail_report