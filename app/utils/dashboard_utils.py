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


def apply_filters(df: pd.DataFrame, table_type: str) -> pd.DataFrame:
    """Apply filters to dataframe based on table type"""
    filters = st.session_state.get('dashboard_filters', {})
    if not filters or df.empty:
        return df

    original_shape = df.shape
    filtered_df = df.copy()

    if table_type == "experiments":
        if 'battery_types' in filters and filters['battery_types']:
            if 'battery_type' in filtered_df.columns:
                filtered_df = filtered_df[filtered_df['battery_type'].isin(filters['battery_types'])]

        if 'capacity_range' in filters:
            min_cap, max_cap = filters['capacity_range']
            if 'nominal_capacity' in filtered_df.columns:                
                if min_cap is not None:
                    filtered_df = filtered_df[filtered_df['nominal_capacity'] >= min_cap]
                if max_cap is not None:
                    filtered_df = filtered_df[filtered_df['nominal_capacity'] <= max_cap]

    elif table_type == "steps":
        if 'step_types' in filters and filters['step_types']:
            if 'step_type' in filtered_df.columns:
                filtered_df = filtered_df[filtered_df['step_type'].isin(filters['step_types'])]

        if 'c_rate_range' in filters:
            min_c, max_c = filters['c_rate_range']
            if 'c_rate' in filtered_df.columns:
                # Ensure c_rate is numeric and handle NAs before filtering
                filtered_df['c_rate'] = pd.to_numeric(filtered_df['c_rate'], errors='coerce')
                if min_c is not None:
                    filtered_df = filtered_df[filtered_df['c_rate'] >= min_c]
                if max_c is not None:
                    filtered_df = filtered_df[filtered_df['c_rate'] <= max_c]

    elif table_type == "cells":
        if 'cell_chemistries' in filters and filters['cell_chemistries']:
            if 'chemistry' in filtered_df.columns:
                filtered_df = filtered_df[filtered_df['chemistry'].isin(filters['cell_chemistries'])]

        if 'cell_capacity_range' in filters:
            min_cap, max_cap = filters['cell_capacity_range']
            if 'nominal_capacity' in filtered_df.columns:
                # Ensure capacity is numeric and handle NAs before filtering
                filtered_df['nominal_capacity'] = pd.to_numeric(filtered_df['nominal_capacity'], errors='coerce')
                if min_cap is not None:
                    filtered_df = filtered_df[filtered_df['nominal_capacity'] >= min_cap]
                if max_cap is not None:
                    filtered_df = filtered_df[filtered_df['nominal_capacity'] <= max_cap]

        if 'cell_form_factors' in filters and filters['cell_form_factors']:
            if 'form_factor' in filtered_df.columns:
                filtered_df = filtered_df[filtered_df['form_factor'].isin(filters['cell_form_factors'])]

    return filtered_df


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
                    # else: # Removed debug print
                        # print(f"DEBUG: Non-convertible ID in dict for {table_name}: {row_id}")
                # else: # Removed debug print
                    # print(f"DEBUG: No 'id' field in selected row dict for {table_name}: {row}")

            # Case 2: Row is a list/tuple (values in column order)
            elif isinstance(row, (list, tuple)):
                if len(row) > 0:
                    row_id = row[0] # Assuming ID is the first column
                    if isinstance(row_id, (int, float)):
                        selected_ids.append(int(row_id))
                    elif isinstance(row_id, str) and row_id.isdigit():
                        selected_ids.append(int(row_id))
                    # else: # Removed debug print
                        # print(f"DEBUG: Non-convertible ID in list/tuple for {table_name}: {row_id}")
                # else: # Removed debug print
                    # print(f"DEBUG: Empty list/tuple row for {table_name}: {row}")

            # Case 3: Row is a single value (might be an ID)
            elif isinstance(row, (int, float)):
                selected_ids.append(int(row))

            elif isinstance(row, str):
                if row.isdigit():
                    selected_ids.append(int(row))
                # else: # Removed debug print
                    # print(f"DEBUG: Non-digit string row for {table_name}: {row}")

            # else: # Removed debug print
                # print(f"DEBUG: Unknown row type for {table_name}: {type(row)}, content: {row}")

        except Exception as e:
            # Removed debug print: print(f"DEBUG: Error processing row {i}: {e}, row: {row}")
            st.warning(f"Skipping a row for {table_name} due to error: {e}. Row data: {row}") # Added a warning instead
            continue

    return selected_ids