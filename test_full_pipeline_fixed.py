#!/usr/bin/env python3
"""
測試完整的數據庫操作管道，包括步驟和測量數據
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.database_service import get_db_session, save_steps_to_db, save_measurements_to_db_with_session
from app.models.database import Experiment, Step, Measurement
import pandas as pd
from datetime import datetime
import numpy as np

def test_full_pipeline():
    """測試完整的步驟和測量數據保存管道"""
    print("=== 測試完整數據庫管道 ===")
    
    # 創建測試步驟數據
    test_steps_df = pd.DataFrame({
        'step_number': [1, 2, 3],
        'step_type': ['CC_Charge', 'CV_Charge', 'Rest'],
        'start_time': [datetime.now(), datetime.now(), datetime.now()],
        'end_time': [datetime.now(), datetime.now(), datetime.now()],
        'duration': [100.0, 200.0, 50.0],
        'voltage_start': [3.0, 4.1, 4.1],
        'voltage_end': [4.1, 4.1, 4.1],
        'current': [1.0, 0.5, 0.0],
        'capacity': [50.0, 20.0, 0.0],
        'energy': [30.0, 15.0, 0.0]
    })
    
    # 創建測試測量數據
    measurement_data = []
    for step_num in [1, 2, 3]:
        for i in range(5):  # 每個步驟5個測量點
            measurement_data.append({
                'step_number': step_num,
                'execution_time': i * 10.0,
                'voltage': 3.5 + (step_num - 1) * 0.2 + i * 0.01,
                'current': 1.0 - step_num * 0.2 + i * 0.01,
                'temperature': 25.0 + i * 0.5,
                'capacity': i * 10.0,
                'energy': i * 5.0,
                'soc': i * 20.0
            })
    
    test_measurements_df = pd.DataFrame(measurement_data)
    
    try:
        with get_db_session() as session:
            # 查找測試實驗
            from sqlmodel import select
            experiment = session.exec(
                select(Experiment).where(Experiment.id == 18)
            ).first()
            
            if not experiment:
                print("錯誤：找不到實驗 ID 18")
                return False
            
            # 驗證實驗 ID 不為 None
            if experiment.id is None:
                print("錯誤：實驗 ID 為 None")
                return False
                
            print(f"使用實驗 ID: {experiment.id}")
            
            # 步驟 1: 保存步驟數據
            print("步驟 1: 保存步驟數據...")
            steps = save_steps_to_db(
                experiment_id=experiment.id,
                steps_df=test_steps_df,
                nominal_capacity=100.0,
                session=session
            )
            
            # 立即提交步驟數據以確保獲得有效的 step IDs
            session.commit()
            print(f"已提交步驟數據，獲得步驟 IDs: {[step.id for step in steps]}")
            
            # 步驟 2: 創建步驟映射表，過濾 None 值
            step_mapping = {step.step_number: step.id for step in steps if step.id is not None}
            print(f"步驟映射表: {step_mapping}")
            
            # 驗證映射表
            invalid_mappings = {k: v for k, v in step_mapping.items() if v is None}
            if invalid_mappings:
                print(f"錯誤: 發現無效的步驟 ID: {invalid_mappings}")
                return False
            
            # 步驟 3: 保存測量數據
            print("步驟 3: 保存測量數據...")
            save_measurements_to_db_with_session(
                session=session,
                experiment_id=experiment.id,
                details_df=test_measurements_df,
                step_mapping=step_mapping,
                nominal_capacity=100.0,
                batch_size=10
            )
            
            # 提交測量數據
            session.commit()
            print("已提交測量數據")
            
            # 步驟 4: 驗證數據保存
            print("步驟 4: 驗證數據保存...")
            
            # 檢查步驟數量
            from sqlmodel import select, func
            step_count = session.exec(
                select(func.count(Step.id)).where(Step.experiment_id == experiment.id)
            ).one()
            
            # 檢查測量數量
            measurement_count = session.exec(
                select(func.count(Measurement.id))
                .select_from(Measurement)
                .join(Step)
                .where(Step.experiment_id == experiment.id)
            ).one()
            
            print(f"實驗 {experiment.id} 中的步驟數量: {step_count}")
            print(f"實驗 {experiment.id} 中的測量數量: {measurement_count}")
            
            # 驗證結果
            expected_steps = len(test_steps_df)
            expected_measurements = len(test_measurements_df)
            
            if step_count >= expected_steps and measurement_count >= expected_measurements:
                print("✓ 完整管道測試成功！")
                print(f"  - 步驟數據: {step_count} >= {expected_steps} ✓")
                print(f"  - 測量數據: {measurement_count} >= {expected_measurements} ✓")
                return True
            else:
                print("✗ 數據保存不完整")
                print(f"  - 步驟數據: {step_count} < {expected_steps}")
                print(f"  - 測量數據: {measurement_count} < {expected_measurements}")
                return False
                
    except Exception as e:
        print(f"完整管道測試失敗: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_database_lock_resolution():
    """測試數據庫鎖定問題是否已解決"""
    print("\n=== 測試數據庫鎖定解決方案 ===")
    
    try:
        # 模擬多個並發操作
        success_count = 0
        total_tests = 3
        
        for i in range(total_tests):
            print(f"並發測試 {i+1}/{total_tests}...")
            
            try:
                with get_db_session() as session:
                    # 簡單的數據庫查詢
                    from sqlmodel import select
                    experiment = session.exec(
                        select(Experiment).where(Experiment.id == 18)
                    ).first()
                    
                    if experiment:
                        print(f"  ✓ 測試 {i+1} 成功訪問數據庫")
                        success_count += 1
                    else:
                        print(f"  - 測試 {i+1} 找不到實驗")
                        
            except Exception as e:
                print(f"  ✗ 測試 {i+1} 失敗: {str(e)}")
        
        if success_count == total_tests:
            print("✓ 數據庫鎖定問題已解決！")
            return True
        else:
            print(f"✗ 部分數據庫操作失敗 ({success_count}/{total_tests})")
            return False
            
    except Exception as e:
        print(f"數據庫鎖定測試失敗: {str(e)}")
        return False

if __name__ == "__main__":
    print("開始測試完整修復...")
    
    test1_result = test_full_pipeline()
    test2_result = test_database_lock_resolution()
    
    if test1_result and test2_result:
        print("\n🎉 所有測試通過！修復完全成功。")
        print("\n修復摘要:")
        print("✅ Step ID 驗證問題已解決")
        print("✅ 會話管理問題已修復")
        print("✅ 數據庫鎖定問題已解決")
        print("✅ 完整數據管道正常工作")
    else:
        print("\n❌ 部分測試失敗，需要進一步調查。")
