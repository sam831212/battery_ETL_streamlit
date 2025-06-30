"""
測試時間間隔篩選功能
"""

import pandas as pd
import numpy as np
from datetime import datetime
import sys
import os

# 添加專案根目錄到路徑
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from app.services.database_service import filter_data_by_time_interval, validate_time_interval, config

def create_test_data(num_steps=3, points_per_step=100, time_interval_seconds=0.1):
    """
    創建測試數據
    
    Args:
        num_steps: 步驟數量
        points_per_step: 每個步驟的數據點數量
        time_interval_seconds: 數據點間的時間間隔
    """
    data = []
    
    for step_num in range(1, num_steps + 1):
        for i in range(points_per_step):
            data.append({
                'step_number': step_num,
                'execution_time': i * time_interval_seconds,
                'voltage': 3.7 + np.random.normal(0, 0.01),
                'current': 1.0 + np.random.normal(0, 0.05),
                'temperature': 25.0 + np.random.normal(0, 0.5),
                'capacity': i * 0.01,
                'energy': i * 0.037
            })
    
    return pd.DataFrame(data)

def test_time_interval_filtering():
    """測試時間間隔篩選功能"""
    print("🧪 測試時間間隔篩選功能")
    print("=" * 50)
    
    # 創建測試數據
    print("📊 創建測試數據...")
    test_df = create_test_data(num_steps=3, points_per_step=100, time_interval_seconds=0.1)
    print(f"原始數據: {len(test_df)} 行, {test_df['step_number'].nunique()} 個步驟")
    print(f"每個步驟平均數據點: {len(test_df) / test_df['step_number'].nunique():.1f}")
    
    # 測試不同的時間間隔
    test_intervals = [0.0, 0.5, 1.0, 2.0, 5.0]
    
    for interval in test_intervals:
        print(f"\n🕐 測試時間間隔: {interval} 秒")
        print("-" * 30)
        
        try:
            filtered_df = filter_data_by_time_interval(test_df, interval)
            
            if interval == 0.0:
                assert len(filtered_df) == len(test_df), "間隔為0時應該返回所有數據"
                print(f"✅ 無篩選: {len(filtered_df)} 行 (與原始相同)")
            else:
                reduction_rate = ((len(test_df) - len(filtered_df)) / len(test_df) * 100)
                print(f"✅ 篩選結果: {len(test_df)} -> {len(filtered_df)} 行")
                print(f"   減少率: {reduction_rate:.1f}%")
                
                # 驗證每個步驟都有數據
                original_steps = set(test_df['step_number'].unique())
                filtered_steps = set(filtered_df['step_number'].unique())
                assert original_steps == filtered_steps, "篩選後應該保留所有步驟"
                print(f"   步驟保留: {len(filtered_steps)}/{len(original_steps)} ✅")
                
                # 驗證時間間隔
                for step_num in original_steps:
                    step_data = filtered_df[filtered_df['step_number'] == step_num].sort_values('execution_time')
                    if len(step_data) > 1:
                        time_diffs = step_data['execution_time'].diff().dropna()
                        min_diff = time_diffs.min()
                        # 允許一定的容差，因為總是保留第一個和最後一個點
                        if min_diff < interval - 0.01 and len(step_data) > 2:
                            print(f"   ⚠️ 步驟 {step_num}: 最小時間間隔 {min_diff:.3f}s < {interval}s")
                        else:
                            print(f"   ✅ 步驟 {step_num}: 時間間隔符合要求")
        
        except Exception as e:
            print(f"❌ 錯誤: {str(e)}")

def test_validation_function():
    """測試驗證函數"""
    print("\n🔍 測試時間間隔驗證功能")
    print("=" * 50)
    
    test_cases = [
        (0.0, 0.0, "零值應該被接受"),
        (1.0, 1.0, "正常值應該被接受"),
        (0.05, config.min_time_interval, "小於最小值應該被調整"),
        (5000.0, config.max_time_interval, "大於最大值應該被調整"),
    ]
    
    for input_val, expected_val, description in test_cases:
        try:
            result = validate_time_interval(input_val)
            if abs(result - expected_val) < 0.001:
                print(f"✅ {description}: {input_val} -> {result}")
            else:
                print(f"❌ {description}: 期望 {expected_val}, 得到 {result}")
        except Exception as e:
            print(f"❌ {description}: 錯誤 {str(e)}")
    
    # 測試負值（應該拋出異常）
    try:
        validate_time_interval(-1.0)
        print("❌ 負值應該拋出異常")
    except Exception:
        print("✅ 負值正確拋出異常")

def test_performance_impact():
    """測試性能影響"""
    print("\n⚡ 測試性能影響")
    print("=" * 50)
    
    # 創建大量測試數據
    large_test_df = create_test_data(num_steps=10, points_per_step=1000, time_interval_seconds=0.01)
    print(f"大數據集: {len(large_test_df)} 行")
    
    import time
    
    intervals = [0.0, 0.1, 1.0, 10.0]
    
    for interval in intervals:
        start_time = time.time()
        filtered_df = filter_data_by_time_interval(large_test_df, interval)
        end_time = time.time()
        
        processing_time = end_time - start_time
        reduction_rate = ((len(large_test_df) - len(filtered_df)) / len(large_test_df) * 100) if interval > 0 else 0
        
        print(f"間隔 {interval:4.1f}s: {len(large_test_df):5d} -> {len(filtered_df):5d} 行 "
              f"({reduction_rate:5.1f}% 減少), 耗時 {processing_time:.3f}s")

if __name__ == "__main__":
    try:
        test_time_interval_filtering()
        test_validation_function()
        test_performance_impact()
        print("\n🎉 所有測試完成！")
    except Exception as e:
        print(f"\n💥 測試失敗: {str(e)}")
        import traceback
        traceback.print_exc()
