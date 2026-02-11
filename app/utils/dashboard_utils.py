import pandas as pd


from typing import Any, List

import streamlit as st


def get_available_numeric_columns(df: pd.DataFrame, candidate_columns: List[str]) -> List[str]:
    """Returns columns from candidate_columns that exist in df, are numeric, and not all NaN."""
    if df.empty:
        return []
    available_cols = []
    for col_name in candidate_columns:
        if col_name in df.columns:
            # Check if the column is numeric-like (handles ints, floats)
            # and ensure not all values are NaN, as this can cause issues with some plots
            try:
                if pd.api.types.is_numeric_dtype(df[col_name]) and not df[col_name].isna().all():
                    available_cols.append(col_name)
            except TypeError: # Handle cases where dtype check might fail for mixed types if not strictly numeric
                pass
    return available_cols


def extract_selected_ids(selected_rows: List[Any], table_name: str) -> List[int]:
    """Extract IDs from selected rows, handling various formats including DataFrame"""
    selected_ids = []

    # Handle DataFrame case first
    if isinstance(selected_rows, pd.DataFrame):
        if selected_rows.empty:
            return selected_ids
        # Convert DataFrame to list of dicts
        selected_rows = selected_rows.to_dict('records')

    # Handle other empty cases
    if not selected_rows or (hasattr(selected_rows, '__len__') and len(selected_rows) == 0):
        return selected_ids

    for i, row in enumerate(selected_rows):
        try:
            # Case 1: Row is a dictionary (expected format)
            if isinstance(row, dict):
                if 'id' in row:
                    row_id = row['id']
                    if isinstance(row_id, (int, float)):
                        selected_ids.append(int(row_id))
                    elif isinstance(row_id, str) and row_id.isdigit():
                        selected_ids.append(int(row_id))

            # Case 2: Row is a list/tuple (values in column order)
            elif isinstance(row, (list, tuple)):
                if len(row) > 0:
                    row_id = row[0] # Assuming ID is the first column
                    if isinstance(row_id, (int, float)):
                        selected_ids.append(int(row_id))
                    elif isinstance(row_id, str) and row_id.isdigit():
                        selected_ids.append(int(row_id))

            # Case 3: Row is a single value (might be an ID)
            elif isinstance(row, (int, float)):
                selected_ids.append(int(row))

            elif isinstance(row, str):
                if row.isdigit():
                    selected_ids.append(int(row))

        except Exception as e:
            st.warning(f"Skipping a row for {table_name} due to error: {e}. Row data: {row}") # Added a warning instead
            continue

    return selected_ids