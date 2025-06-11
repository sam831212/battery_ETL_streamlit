#!/usr/bin/env python3
"""
簡化版 Debug 測試腳本：專注測試 pre_test_rest_time 自動設定功能

這個腳本會：
1. 建立測試資料
2. 直接測試 calculate_pre_test_rest_time 函數
3. 模擬 UI 流程中的資料處理（跳過複雜的 SOC 計算）
"""

import pandas as pd
from datetime import datetime, timedelta
import sys
import os

# 新增專案路徑到 Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.etl.transformation import calculate_pre_test_rest_time

def create_simple_test_data():
    """建立簡單的測試用工步資料"""
    print("[INFO] 建立簡單測試資料...")
    
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
            'current': [1.0, 0.0, -1.0, 0.0, 1.0][i],
            'capacity': [1.0, 1.0, 0.0, 0.0, 2.0][i],
            'energy': [3.0, 3.0, 0.0, 0.0, 6.0][i],
            'temperature_start': 25.0 + i * 0.5,
            'temperature_end': 25.0 + i * 0.5 + 0.2,
            'c_rate': [0.33, 0.0, -0.33, 0.0, 0.33][i],
        }
        steps_data.append(step)
    
    steps_df = pd.DataFrame(steps_data)
    
    print(f"[INFO] 建立完成: {len(steps_df)} 個工步")
    return steps_df

def test_calculate_pre_test_rest_time():
    """測試 calculate_pre_test_rest_time 函數"""
    print("\n=== 測試 calculate_pre_test_rest_time 函數 ===")
    
    steps_df = create_simple_test_data()
    
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
    
    return result_df

def test_ui_data_processing_simulation():
    """模擬 UI 端的資料處理（簡化版）"""
    print("\n=== 模擬 UI 端資料處理 ===")
    
    # 取得包含 pre_test_rest_time 的資料
    transformed_steps = test_calculate_pre_test_rest_time()
    
    # 模擬選擇部分工步（選擇工步 2, 3, 4）
    selected_step_numbers = [2, 3, 4]
    selected_steps_data = []
    
    print(f"\n模擬從 {len(transformed_steps)} 個工步中選擇工步: {selected_step_numbers}")
    
    for _, row in transformed_steps.iterrows():
        if row['step_number'] in selected_step_numbers:
            # 模擬 UI 端建立的 selected_steps 資料結構
            step_dict = {
                'step_number': int(row['step_number']),
                'step_type': str(row['step_type']),
                'start_time': row['start_time'],
                'end_time': row['end_time'],
                'duration': float(row['duration']),
                'voltage_start': float(row['voltage_start']),
                'voltage_end': float(row['voltage_end']),
                'current': float(row['current']),
                'capacity': float(row['capacity']),
                'energy': float(row['energy']),
                'temperature_start': float(row['temperature_start']),
                'temperature_end': float(row['temperature_end']),
                'c_rate': float(row['c_rate']),
                'pre_test_rest_time': row['pre_test_rest_time'] if pd.notna(row['pre_test_rest_time']) else None,
                'data_meta': f"Test step {row['step_number']}"
            }
            selected_steps_data.append(step_dict)
            print(f"  選擇工步 {step_dict['step_number']}: pre_test_rest_time = {step_dict['pre_test_rest_time']}")
    
    # 驗證選擇的工步都有正確的 pre_test_rest_time 值
    print("\n驗證選擇的工步:")
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
    
    return selected_steps_data

def test_database_step_creation_simulation():
    """模擬資料庫 Step 物件創建"""
    print("\n=== 模擬資料庫 Step 物件創建 ===")
    
    selected_steps_data = test_ui_data_processing_simulation()
    
    print("\n模擬 handle_selected_steps_save 中的 Step 物件創建:")
    for step_data in selected_steps_data:
        # 模擬 debug print
        print(f"[DEBUG] 工步 {step_data['step_number']}: pre_test_rest_time = {step_data['pre_test_rest_time']} (類型: {type(step_data['pre_test_rest_time'])})")
        
        # 模擬 Step 物件屬性設定
        step_attributes = {
            'step_number': step_data['step_number'],
            'step_type': step_data['step_type'],
            'duration': step_data['duration'],
            'pre_test_rest_time': step_data['pre_test_rest_time'],
            'data_meta': step_data['data_meta']
        }
        
        print(f"[DEBUG] Step 物件 {step_attributes['step_number']}: pre_test_rest_time = {step_attributes['pre_test_rest_time']}")
        
        # 驗證 pre_test_rest_time 值不是 NaN 或錯誤型別
        if step_data['step_number'] > 1:  # 第一個工步以外的都應該有值
            assert step_attributes['pre_test_rest_time'] is not None, f"工步 {step_data['step_number']} 的 pre_test_rest_time 不應該是 None"
            assert isinstance(step_attributes['pre_test_rest_time'], (int, float)), f"工步 {step_data['step_number']} 的 pre_test_rest_time 應該是數字類型"
            print(f"  ✓ 工步 {step_data['step_number']} 的 pre_test_rest_time 類型和值正確")

def main():
    """主要測試流程"""
    print("開始 pre_test_rest_time Debug 測試（簡化版）")
    print("=" * 60)
    
    try:
        # 測試 1: calculate_pre_test_rest_time 函數
        print("測試 1: 驗證 calculate_pre_test_rest_time 函數")
        transformed_steps = test_calculate_pre_test_rest_time()
        
        # 測試 2: UI 端資料處理模擬
        print("\n測試 2: 模擬 UI 端資料處理")
        selected_steps = test_ui_data_processing_simulation()
        
        # 測試 3: 資料庫 Step 物件創建模擬
        print("\n測試 3: 模擬資料庫 Step 物件創建")
        test_database_step_creation_simulation()
        
        print("\n" + "=" * 60)
        print("🎉 所有測試通過！pre_test_rest_time 功能正常運作")
        print("\n測試結果摘要:")
        print("✓ ETL 流程: calculate_pre_test_rest_time 函數正確計算")
        print("✓ UI 流程: 選擇的工步正確包含 pre_test_rest_time 值")
        print("✓ DB 流程: Step 物件創建時正確設定 pre_test_rest_time")
        
        print("\n下一步驗證建議：")
        print("1. 在實際的 web 應用中上傳測試檔案")
        print("2. 選擇工步並載入資料庫")
        print("3. 觀察 console log 中的 [DEBUG] 訊息")
        print("4. 檢查資料庫中 Step 表的 pre_test_rest_time 欄位值")
        print("5. 如果仍然出現 None，檢查是否使用了正確的 transformed DataFrame")
        
    except Exception as e:
        print(f"\n❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
