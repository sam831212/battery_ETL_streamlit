"""
Transformation module for battery test data

This module provides functions for calculating derived metrics from
battery test data, such as SOC, C-rate, and temperature statistics.
"""
from typing import List, Dict, Tuple, Optional, Union, Any, cast
import pandas as pd
import numpy as np
from datetime import datetime

# Type aliases for improved readability
StepDataFrame = pd.DataFrame
DetailDataFrame = pd.DataFrame


def calculate_c_rate(current: float, nominal_capacity: float) -> float:
    """
    Calculate C-rate based on current and nominal capacity.

    C-rate = |Current (A)| / Nominal Capacity (Ah)
    
    Args:
        current: Current in Amperes (A)
        nominal_capacity: Nominal capacity in Ampere-hours (Ah)

    Returns:
        C-rate value (dimensionless)
    """
    if nominal_capacity <= 0:
        raise ValueError("Nominal capacity must be positive")
    
    # Take absolute value of current for both charge and discharge
    return round(abs(current) / nominal_capacity, 2)


def calculate_soc(steps_df: pd.DataFrame, details_df: pd.DataFrame, full_discharge_step_idx: Optional[int] = None) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Calculate State of Charge (SOC) for all steps using Coulomb counting method.
    
    SOC calculation method:
    - If full_discharge_step_idx is provided, use that step as the 0% SOC reference point
    - If not provided, find the 2nd discharge step (CC放電) as the reference
    - Calculate SOC based on formula: SOC = (Total Capacity - Reference Total Capacity) / |Capacity of full discharge step|
    - All steps have SOC values calculated relative to the reference point
    - Steps before the reference point will have null SOC values
    
    Args:
        steps_df: DataFrame containing step data
        details_df: DataFrame containing detailed measurement data (not used for SOC calculation anymore)
        full_discharge_step_idx: Optional index or step number of a full discharge step to use as reference
            
    Returns:
        Tuple containing:
        - Updated steps DataFrame with SOC values
        - Unchanged details DataFrame
    """
    # Make a copy of the input DataFrame to avoid modifying original
    steps = steps_df.copy()
    
    # Initialize SOC columns with NaN/None
    steps['soc_start'] = None
    steps['soc_end'] = None
    
    # First find the reference step (discharge step to use as 0% SOC reference)
    discharge_steps = steps[steps['step_type'] == 'discharge']
    if len(discharge_steps) == 0:
        raise ValueError("No discharge steps found for SOC calculation")
    
    # If no reference step is provided, find the 2nd discharge step
    if full_discharge_step_idx is None:
        if len(discharge_steps) >= 2:
            # Sort discharge steps by step_number and get the 2nd one
            discharge_steps_sorted = discharge_steps.sort_values('step_number')
            reference_step_idx = discharge_steps_sorted.index[1]  # 2nd discharge step (0-indexed)
        else:
            # If there's only one discharge step, use it
            reference_step_idx = discharge_steps.index[0]
    else:
        # Use the provided reference step index
        reference_step_idx = full_discharge_step_idx
    
    # Validate the reference step index exists
    try:
        reference_step = steps.loc[reference_step_idx]
    except KeyError:
        # Try to handle case where step number was provided instead of index
        if isinstance(full_discharge_step_idx, int) and 'step_number' in steps.columns:
            matching_steps = steps[steps['step_number'] == full_discharge_step_idx]
            if not matching_steps.empty:
                reference_step_idx = matching_steps.index[0]
                reference_step = steps.loc[reference_step_idx]
            else:
                raise ValueError(f"Reference step {full_discharge_step_idx} not found")
        else:
            raise ValueError(f"Reference step index {full_discharge_step_idx} not found")
    
    # Ensure the reference step is a discharge step
    if reference_step['step_type'] != 'discharge':
        raise ValueError(f"Reference step must be a discharge step, but step {reference_step.get('step_number', reference_step_idx)} is a {reference_step['step_type']} step")
      # Get the reference discharge step's total capacity and capacity
    if 'total_capacity' not in reference_step:
        raise ValueError("Column 'total_capacity' not found. Please ensure the 'total_capacity' column is correctly imported from '總電壓(Ah)'.")
    
    # Handle capacity column name variations (capacity, capacity_x, etc.)
    capacity_column = None
    for col in reference_step.index:
        if col == 'capacity' or col.startswith('capacity'):
            capacity_column = col
            break
    
    if capacity_column is None:
        raise ValueError(f"No capacity column found. Available columns: {list(reference_step.index)}")
    
    reference_total_capacity = reference_step['total_capacity']
    reference_capacity = reference_step[capacity_column]
    reference_step_number = reference_step['step_number']
    
    # Set the reference discharge step's SOC_end to 0%
    steps.at[reference_step_idx, 'soc_end'] = 0.0

    # Get sorted step indices for processing in chronological order
    steps_sorted = steps.sort_values('start_time')
    step_indices = list(steps_sorted.index)
    reference_step_pos = step_indices.index(reference_step_idx)
    
    # Calculate SOC for all steps after the reference step based on the formula:
    # SOC = (Total Capacity - Reference Total Capacity) / |Reference Capacity|
    for i, idx in enumerate(step_indices):
        if i >= reference_step_pos:  # Only calculate for steps at or after the reference step
            step = steps.loc[idx]
            if 'total_capacity' in step and pd.notna(step['total_capacity']):
                soc_end = 100 * (step['total_capacity'] - reference_total_capacity) / abs(reference_capacity)
                steps.at[idx, 'soc_end'] = round(soc_end, 2)

    # Calculate soc_start for each step based on the end SOC of the previous step
    for i, current_idx in enumerate(step_indices):
        if i == 0 or i <= reference_step_pos:  
            # Skip steps before or at the reference step for soc_start since they may have null soc_end
            continue
        else:
            # For steps after reference, start SOC is the end SOC of the previous step
            previous_idx = step_indices[i - 1]
            if pd.notna(steps.loc[previous_idx, 'soc_end']):
                steps.at[current_idx, 'soc_start'] = round(steps.loc[previous_idx, 'soc_end'], 2)

    # For the reference step, set soc_start to a small negative value if previous step exists
    if reference_step_pos > 0:
        previous_idx = step_indices[reference_step_pos - 1]
        if 'total_capacity' in steps.loc[previous_idx] and pd.notna(steps.loc[previous_idx, 'total_capacity']):
            previous_total_capacity = steps.loc[previous_idx, 'total_capacity']
            if isinstance(previous_total_capacity, pd.Series):
                previous_total_capacity = previous_total_capacity.iloc[0]
            if isinstance(reference_total_capacity, pd.Series):
                reference_total_capacity = reference_total_capacity.iloc[0]
            soc_start = 100 * (float(previous_total_capacity) - float(reference_total_capacity)) / abs(float(reference_capacity))
            steps.at[reference_step_idx, 'soc_start'] = round(soc_start, 2)

    # Return updated steps and unchanged details
    return steps, details_df

def transform_data(steps_df: pd.DataFrame, details_df: pd.DataFrame, 
                   nominal_capacity: float) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Transform step and detail data with calculated fields.
    
    This function:
    1. Calculates C-rate based on current and nominal capacity
    2. Calculates SOC (State of Charge) for steps
    3. Calculates pre_test_rest_time for each step
    
    Args:
        steps_df: DataFrame containing step data
        details_df: DataFrame containing measurement details
        nominal_capacity: Nominal capacity in Ah
        
    Returns:
        Tuple of (transformed_steps_df, transformed_details_df)
    """
    # 製作副本以避免修改原始資料
    steps = steps_df.copy()
    details = details_df.copy()
    
    print(f"[DEBUG] transform_data 開始: {len(steps)} 個工步, {len(details)} 個細節資料點")
    
    # 1. Calculate C-rate
    if nominal_capacity > 0:
        steps['c_rate'] = steps['current'].apply(
            lambda current: calculate_c_rate(current, nominal_capacity)
        )
        details['c_rate'] = details['current'].apply(
            lambda current: calculate_c_rate(current, nominal_capacity)
        )
    else:
        steps['c_rate'] = 0.0
        details['c_rate'] = 0.0
    
    # 2. Calculate SOC
    steps, details = calculate_soc(steps, details)
      # 3. Calculate pre_test_rest_time
    print(f"[DEBUG] transform_data: 開始計算 pre_test_rest_time")
    print(f"[DEBUG] 工步資料排序前 step_number: {steps['step_number'].tolist()}")
    steps = calculate_pre_test_rest_time(steps)
    
    # DEBUG: 檢查 pre_test_rest_time 欄位是否存在且有值
    if 'pre_test_rest_time' in steps.columns:
        non_null_count = steps['pre_test_rest_time'].notna().sum()
        print(f"[DEBUG] transform_data 完成: pre_test_rest_time 欄位存在, {non_null_count}/{len(steps)} 個工步有值")
        if non_null_count > 0:
            print(f"[DEBUG] pre_test_rest_time 值範例: {steps['pre_test_rest_time'].dropna().head(3).tolist()}")
        
        # 顯示每個工步的詳細資訊
        print(f"[DEBUG] 每個工步的 pre_test_rest_time 詳細資訊:")
        for _, row in steps.iterrows():
            print(f"[DEBUG]   工步 {row['step_number']}: duration={row['duration']}, pre_test_rest_time={row['pre_test_rest_time']}")
    else:
        print(f"[DEBUG] transform_data 警告: pre_test_rest_time 欄位不存在！")
    
    return steps, details

def calculate_pre_test_rest_time(steps_df: pd.DataFrame) -> pd.DataFrame:
    """
    計算每個工步的前一個工步執行時間 (pre_test_rest_time)
    
    對於每個工步，設定 pre_test_rest_time 為前一個工步的 duration 值：
    - 第一個工步 (step_number = 1)：pre_test_rest_time = None
    - 其他工步：pre_test_rest_time = 前一個工步的 duration 值
    
    Args:
        steps_df: 包含工步資料的資料幀，必須包含 'step_number' 和 'duration' 欄位
        
    Returns:
        更新後的工步資料幀，包含 pre_test_rest_time 欄位
    """
    # 製作輸入資料幀的副本
    steps = steps_df.copy()
    
    # 初始化 pre_test_rest_time 欄位為 None
    steps['pre_test_rest_time'] = None
    
    # DEBUG: 印出輸入資料的基本信息
    print(f"[DEBUG] calculate_pre_test_rest_time: 輸入 {len(steps)} 個工步")
    print(f"[DEBUG] 工步編號範圍: {steps['step_number'].min()} - {steps['step_number'].max()}")
    
    # 檢查必要的欄位是否存在
    if 'step_number' not in steps.columns:
        raise ValueError("步驟資料中缺少 'step_number' 欄位")
    if 'duration' not in steps.columns:
        raise ValueError("步驟資料中缺少 'duration' 欄位")
    
    # 按 step_number 排序以確保正確的順序
    steps = steps.sort_values('step_number').reset_index(drop=True)
    
    # 為每個工步計算 pre_test_rest_time (從第二個工步開始)
    for i in range(1, len(steps)):
        try:
            # 取得前一個工步的 duration
            previous_duration = steps.iloc[i-1]['duration']
            current_step_number = steps.iloc[i]['step_number']
            previous_step_number = steps.iloc[i-1]['step_number']
            
            # 確保 duration 是有效的數值
            if pd.notna(previous_duration) and previous_duration is not None:
                steps.at[i, 'pre_test_rest_time'] = previous_duration
                print(f"[DEBUG] 工步 {current_step_number}: pre_test_rest_time = {previous_duration} (來自工步 {previous_step_number})")
            else:
                print(f"[DEBUG] 工步 {current_step_number}: pre_test_rest_time = None (前一工步 {previous_step_number} 的 duration 無效: {previous_duration})")
        except (ValueError, TypeError, IndexError) as e:
            # 如果出現任何錯誤，保持為 None
            print(f"[DEBUG] 工步 {current_step_number}: 計算 pre_test_rest_time 時發生錯誤: {e}")
            continue
    
    # DEBUG: 印出最終結果摘要
    non_null_count = steps['pre_test_rest_time'].notna().sum()
    print(f"[DEBUG] calculate_pre_test_rest_time 完成: {non_null_count}/{len(steps)} 個工步有 pre_test_rest_time 值")
    if non_null_count > 0:
        print(f"[DEBUG] pre_test_rest_time 範圍: {steps['pre_test_rest_time'].min()} - {steps['pre_test_rest_time'].max()}")
    
    return steps