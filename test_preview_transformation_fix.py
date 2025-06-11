#!/usr/bin/env python3
"""
測試修復後的 preview_page.py 中的 apply_transformations 函數
確認 pre_test_rest_time 現在是否被正確計算並包含在結果中
"""

import pandas as pd
import sys
import os

# 添加項目根目錄到路徑
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_apply_transformations_with_pre_test_rest_time():
    """測試 apply_transformations 函數現在是否包含 pre_test_rest_time 計算"""
    
    # 創建測試數據
    steps_data = pd.DataFrame({
        'step_number': [1, 2, 3, 4, 5],
        'step_type': ['rest', 'charge', 'rest', 'discharge', 'rest'],
        'start_time': pd.to_datetime([
            '2023-01-01 10:00:00',
            '2023-01-01 10:30:00', 
            '2023-01-01 11:30:00',
            '2023-01-01 12:00:00',
            '2023-01-01 13:00:00'
        ]),
        'end_time': pd.to_datetime([
            '2023-01-01 10:30:00',
            '2023-01-01 11:30:00',
            '2023-01-01 12:00:00', 
            '2023-01-01 13:00:00',
            '2023-01-01 13:30:00'
        ]),
        'duration': [1800, 3600, 1800, 3600, 1800],  # 30min, 60min, 30min, 60min, 30min
        'voltage_start': [4.2, 4.2, 4.0, 4.0, 3.0],
        'voltage_end': [4.2, 4.0, 4.0, 3.0, 3.0],
        'current': [0.0, 1.0, 0.0, -1.0, 0.0],
        'capacity': [0.0, 3.0, 3.0, 0.0, 0.0],
        'total_capacity': [0.0, 3.0, 3.0, 0.0, 0.0],
        'energy': [0.0, 12.0, 12.0, 0.0, 0.0],
        'temperature': [25.0, 25.5, 26.0, 26.5, 25.0],
        'original_step_type': ['静置', 'CC充電', '静置', 'CC放電', '静置']
    })
    
    # 創建簡單的測量數據
    details_data = pd.DataFrame({
        'step_number': [1, 1, 2, 2, 3, 3, 4, 4, 5, 5],
        'timestamp': pd.to_datetime([
            '2023-01-01 10:00:00', '2023-01-01 10:15:00',
            '2023-01-01 10:30:00', '2023-01-01 11:00:00', 
            '2023-01-01 11:30:00', '2023-01-01 11:45:00',
            '2023-01-01 12:00:00', '2023-01-01 12:30:00',
            '2023-01-01 13:00:00', '2023-01-01 13:15:00'
        ]),
        'voltage': [4.2, 4.2, 4.1, 4.0, 4.0, 4.0, 3.5, 3.0, 3.0, 3.0],
        'current': [0.0, 0.0, 1.0, 1.0, 0.0, 0.0, -1.0, -1.0, 0.0, 0.0],
        'temperature': [25.0, 25.0, 25.2, 25.5, 26.0, 26.0, 26.2, 26.5, 25.2, 25.0],
        'capacity': [0.0, 0.0, 1.5, 3.0, 3.0, 3.0, 1.5, 0.0, 0.0, 0.0],
        'energy': [0.0, 0.0, 6.0, 12.0, 12.0, 12.0, 6.0, 0.0, 0.0, 0.0]
    })
    
    print("=== 測試修復後的 apply_transformations 函數 ===")
    print(f"測試資料: {len(steps_data)} 個工步, {len(details_data)} 個細節資料點")
    print(f"工步編號: {steps_data['step_number'].tolist()}")
    print(f"工步持續時間: {steps_data['duration'].tolist()}")
    
    # 模擬測試 transform_data 函數 (不使用 UI)
    try:
        from app.etl.transformation import transform_data
        
        print("\n=== 直接測試 transform_data 函數 ===")
        transformed_steps, transformed_details = transform_data(
            steps_data.copy(), 
            details_data.copy(), 
            nominal_capacity=3.0
        )
        
        print(f"\n變換後的工步數據欄位: {transformed_steps.columns.tolist()}")
        
        # 檢查 pre_test_rest_time 欄位
        if 'pre_test_rest_time' in transformed_steps.columns:
            print(f"✓ pre_test_rest_time 欄位存在於變換後的數據中")
            non_null_count = transformed_steps['pre_test_rest_time'].notna().sum()
            print(f"✓ {non_null_count}/{len(transformed_steps)} 個工步有 pre_test_rest_time 值")
            
            if non_null_count > 0:
                print(f"✓ pre_test_rest_time 值範例:")
                for _, row in transformed_steps.iterrows():
                    step_num = row['step_number']
                    duration = row['duration'] 
                    pre_rest = row['pre_test_rest_time']
                    print(f"  工步 {step_num}: duration={duration}, pre_test_rest_time={pre_rest}")
        else:
            print("✗ pre_test_rest_time 欄位不存在於變換後的數據中")
            
        # 檢查其他重要欄位
        expected_columns = ['c_rate', 'soc_start', 'soc_end', 'pre_test_rest_time']
        for col in expected_columns:
            if col in transformed_steps.columns:
                print(f"✓ {col} 欄位存在")
            else:
                print(f"✗ {col} 欄位不存在")
                
        return True
        
    except Exception as e:
        print(f"✗ 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_apply_transformations_with_pre_test_rest_time()
    if success:
        print("\n🎉 測試成功！transform_data 函數現在應該包含 pre_test_rest_time 計算")
    else:
        print("\n❌ 測試失敗，需要進一步調試")
