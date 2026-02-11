#!/usr/bin/env python3
"""
測試修復後的會話管理和 step_id 驗證
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.database_service import get_db_session, save_steps_to_db
from app.models.database import Experiment
import pandas as pd

def test_step_id_validation():
    """測試步驟 ID 驗證功能"""
    print("=== 測試步驟 ID 驗證功能 ===")
      # 創建測試數據
    from datetime import datetime
    
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
    
    try:
        with get_db_session() as session:
            # 查找測試實驗
            experiment = session.query(Experiment).filter(Experiment.id == 18).first()
            if not experiment:
                print("錯誤：找不到實驗 ID 18")
                return False
            
            print(f"使用實驗 ID: {experiment.id}")
            
            # 測試保存步驟
            print("保存測試步驟...")
            steps = save_steps_to_db(
                experiment_id=experiment.id,
                steps_df=test_steps_df,
                nominal_capacity=100.0,
                session=session
            )
            
            print(f"成功保存 {len(steps)} 個步驟")
            
            # 驗證所有步驟都有有效的 ID
            step_ids = [step.id for step in steps]
            print(f"步驟 IDs: {step_ids}")
            
            # 創建映射表，過濾 None 值
            step_mapping = {step.step_number: step.id for step in steps if step.id is not None}
            print(f"步驟映射表: {step_mapping}")
            
            # 驗證映射表
            if len(step_mapping) == len(test_steps_df):
                print("✓ 所有步驟都有有效的 step_id")
                return True
            else:
                print(f"✗ 映射表不完整：期望 {len(test_steps_df)} 個映射，實際得到 {len(step_mapping)} 個")
                return False
                
    except Exception as e:
        print(f"測試失敗: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_experiment_id_validation():
    """測試實驗 ID 驗證"""
    print("\n=== 測試實驗 ID 驗證 ===")
    
    try:
        with get_db_session() as session:            # 測試空實驗 ID
            try:
                # 使用 type: ignore 來忽略類型檢查，因為我們故意測試錯誤情況
                save_steps_to_db(
                    experiment_id=None,  # type: ignore
                    steps_df=pd.DataFrame(),
                    nominal_capacity=100.0,
                    session=session
                )
                print("✗ 應該拒絕 None 實驗 ID")
                return False
            except (ValueError, TypeError) as e:
                print(f"✓ 正確拒絕了 None 實驗 ID: {e}")
                return True
                
    except Exception as e:
        print(f"實驗 ID 驗證測試失敗: {str(e)}")
        return False

if __name__ == "__main__":
    print("開始測試修復...")
    
    test1_result = test_step_id_validation()
    test2_result = test_experiment_id_validation()
    
    if test1_result and test2_result:
        print("\n✓ 所有測試通過！修復成功。")
    else:
        print("\n✗ 部分測試失敗。")
