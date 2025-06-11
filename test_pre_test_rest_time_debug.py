#!/usr/bin/env python3
"""
Debug 測試腳本：測試 pre_test_rest_time 自動設定功能

這個腳本會：
1. 建立測試資料
2. 執行 ETL 流程中的 transform_data
3. 檢查 pre_test_rest_time 欄位是否正確計算
4. 模擬 UI 流程中的資料處理
"""

import pandas as pd
from datetime import datetime, timedelta
import sys
import os

# 新增專案路徑到 Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.etl.transformation import transform_data, calculate_pre_test_rest_time

def create_test_data():
    """建立測試用的工步資料"""
    print("[INFO] 建立測試資料...")
    
    base_time = datetime(2025, 6, 11, 10, 0, 0)
    
    # 建立 5 個測試工步
    steps_data = []
    for i in range(5):
        start_time = base_time + timedelta(hours=i)
        end_time = start_time + timedelta(minutes=30 + i*10)  # 每個工步不同的持續時間
        duration = (end_time - start_time).total_seconds()
        
        step = {
            'step_number': i + 1,
            'step_type': ['charge', 'rest', 'discharge', 'rest', 'charge'][i],
            'start_time': start_time,
            'end_time': end_time,
            'duration': duration,
            'voltage_start': 3.0 + i * 0.2,
            'voltage_end': 3.2 + i * 0.2,
            'current': [1.0, 0.0, -1.0, 0.0, 1.0][i],            'capacity': [1.0, 1.0, 0.0, 0.0, 2.0][i],
            'energy': [3.0, 3.0, 0.0, 0.0, 6.0][i],
            'temperature': 25.0 + i * 0.5,
            'total_capacity': [1.0, 2.0, 2.0, 2.0, 4.0][i],  # 累積總容量
        }
        steps_data.append(step)
    
    steps_df = pd.DataFrame(steps_data)
    
    # 建立簡單的細節資料（每個工步 3 個資料點）
    details_data = []
    for _, step in steps_df.iterrows():
        for j in range(3):
            detail = {
                'step_number': step['step_number'],
                'timestamp': step['start_time'] + timedelta(minutes=j*10),
                'voltage': step['voltage_start'] + j * 0.05,
                'current': step['current'],
                'temperature': step['temperature'] + j * 0.1,                'capacity': step['capacity'] * j / 2,
                'energy': step['energy'] * j / 2,
                'total_capacity': step['total_capacity'] + j * 0.1,
            }
            details_data.append(detail)
    
    details_df = pd.DataFrame(details_data)
    
    print(f"[INFO] 建立完成: {len(steps_df)} 個工步, {len(details_df)} 個細節資料點")
    return steps_df, details_df

def test_calculate_pre_test_rest_time():
    """測試 calculate_pre_test_rest_time 函數"""
    print("\n=== 測試 calculate_pre_test_rest_time 函數 ===")
    
    steps_df, _ = create_test_data()
    
    print("原始 duration 值:")
    for _, row in steps_df.iterrows():
        print(f"  工步 {row['step_number']}: duration = {row['duration']}")
    
    # 測試 calculate_pre_test_rest_time
    result_df = calculate_pre_test_rest_time(steps_df)
    
    print("\n計算後的 pre_test_rest_time 值:")
    for _, row in result_df.iterrows():
        print(f"  工步 {row['step_number']}: pre_test_rest_time = {row['pre_test_rest_time']}")
    
    # 驗證結果
    print("\n驗證結果:")
    # 第一個工步應該是 None
    assert pd.isna(result_df.iloc[0]['pre_test_rest_time']), "第一個工步的 pre_test_rest_time 應該是 None"
    print("  ✓ 第一個工步的 pre_test_rest_time 正確為 None")
    
    # 其他工步應該等於前一個工步的 duration
    for i in range(1, len(result_df)):
        expected = result_df.iloc[i-1]['duration']
        actual = result_df.iloc[i]['pre_test_rest_time']
        assert actual == expected, f"工步 {i+1} 的 pre_test_rest_time 應該是 {expected}，但實際是 {actual}"
        print(f"  ✓ 工步 {i+1} 的 pre_test_rest_time 正確 ({actual})")

def test_transform_data():
    """測試完整的 transform_data 流程"""
    print("\n=== 測試 transform_data 流程 ===")
    
    steps_df, details_df = create_test_data()
    nominal_capacity = 3.0
    
    # 執行 transform_data
    transformed_steps, transformed_details = transform_data(steps_df, details_df, nominal_capacity)
    
    # 檢查 pre_test_rest_time 欄位
    assert 'pre_test_rest_time' in transformed_steps.columns, "transform_data 結果應該包含 pre_test_rest_time 欄位"
    print("  ✓ transform_data 結果包含 pre_test_rest_time 欄位")
    
    # 檢查值
    non_null_count = transformed_steps['pre_test_rest_time'].notna().sum()
    expected_count = len(transformed_steps) - 1  # 除了第一個工步
    assert non_null_count == expected_count, f"應該有 {expected_count} 個工步有 pre_test_rest_time 值，但實際有 {non_null_count} 個"
    print(f"  ✓ 正確有 {non_null_count} 個工步有 pre_test_rest_time 值")
    
    return transformed_steps, transformed_details

def test_ui_data_processing():
    """模擬 UI 端的資料處理"""
    print("\n=== 模擬 UI 端資料處理 ===")
    
    # 取得 transformed 資料
    transformed_steps, _ = test_transform_data()
    
    # 模擬選擇部分工步（選擇工步 2, 3, 4）
    selected_step_numbers = [2, 3, 4]
    selected_steps_data = []
    
    for _, row in transformed_steps.iterrows():
        if row['step_number'] in selected_step_numbers:
            # 模擬 UI 端建立的 selected_steps 資料結構
            step_dict = {
                'step_number': row['step_number'],
                'step_type': row['step_type'],
                'start_time': row['start_time'],
                'end_time': row['end_time'],
                'duration': row['duration'],
                'voltage_start': row['voltage_start'],
                'voltage_end': row['voltage_end'],
                'current': row['current'],
                'capacity': row['capacity'],
                'energy': row['energy'],
                'temperature': row['temperature'],
                'c_rate': row['c_rate'],
                'pre_test_rest_time': row['pre_test_rest_time'],
                'data_meta': f"Test step {row['step_number']}"
            }
            selected_steps_data.append(step_dict)
    
    print(f"模擬選擇了 {len(selected_steps_data)} 個工步:")
    for step in selected_steps_data:
        print(f"  工步 {step['step_number']}: pre_test_rest_time = {step['pre_test_rest_time']}")
    
    # 驗證選擇的工步都有正確的 pre_test_rest_time 值
    for step in selected_steps_data:
        if step['step_number'] == 2:
            # 工步 2 的 pre_test_rest_time 應該是工步 1 的 duration
            expected = transformed_steps[transformed_steps['step_number'] == 1]['duration'].iloc[0]
            assert step['pre_test_rest_time'] == expected, f"工步 2 的 pre_test_rest_time 不正確"
            print(f"  ✓ 工步 2 的 pre_test_rest_time 正確: {step['pre_test_rest_time']}")
        elif step['step_number'] == 3:
            # 工步 3 的 pre_test_rest_time 應該是工步 2 的 duration
            expected = transformed_steps[transformed_steps['step_number'] == 2]['duration'].iloc[0]
            assert step['pre_test_rest_time'] == expected, f"工步 3 的 pre_test_rest_time 不正確"
            print(f"  ✓ 工步 3 的 pre_test_rest_time 正確: {step['pre_test_rest_time']}")
        elif step['step_number'] == 4:
            # 工步 4 的 pre_test_rest_time 應該是工步 3 的 duration
            expected = transformed_steps[transformed_steps['step_number'] == 3]['duration'].iloc[0]
            assert step['pre_test_rest_time'] == expected, f"工步 4 的 pre_test_rest_time 不正確"
            print(f"  ✓ 工步 4 的 pre_test_rest_time 正確: {step['pre_test_rest_time']}")

def main():
    """主要測試流程"""
    print("開始 pre_test_rest_time Debug 測試")
    print("=" * 50)
    
    try:
        # 測試 1: calculate_pre_test_rest_time 函數
        test_calculate_pre_test_rest_time()
        
        # 測試 2: transform_data 流程
        test_transform_data()
        
        # 測試 3: UI 端資料處理
        test_ui_data_processing()
        
        print("\n" + "=" * 50)
        print("🎉 所有測試通過！pre_test_rest_time 功能正常運作")
        print("\n建議下一步：")
        print("1. 在實際的 web 應用中上傳測試檔案")
        print("2. 選擇工步並載入資料庫")
        print("3. 觀察 console log 中的 [DEBUG] 訊息")
        print("4. 檢查資料庫中 Step 表的 pre_test_rest_time 欄位值")
        
    except Exception as e:
        print(f"\n❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
