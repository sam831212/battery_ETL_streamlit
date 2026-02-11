#!/usr/bin/env python3
"""
測試腳本：用於測試增強的日誌記錄功能
這個腳本會模擬文件處理流程，以便我們可以看到詳細的日誌輸出
"""

import pandas as pd
import os
import sys
from datetime import datetime

# 添加項目根目錄到路徑
sys.path.append(os.path.dirname(__file__))

from app.services.file_processing_service import get_file_data_and_metadata, handle_file_processing_pipeline
from app.services.database_service import save_measurements_to_db

def test_logging_with_example_files():
    """使用示例文件測試日誌記錄功能"""
    
    print("===== 開始測試增強的日誌記錄功能 =====")
    
    # 檢查示例文件是否存在
    example_step_file = "example_csv_chromaLex/CALB20Ah_ BMW power map_as 24Ah_0331_Step.csv"
    example_detail_file = "example_csv_chromaLex/CALB20Ah_ BMW power map_as 24Ah_0331_Detail.csv"
    
    if not os.path.exists(example_step_file):
        print(f"錯誤：找不到示例步驟文件: {example_step_file}")
        return False
        
    if not os.path.exists(example_detail_file):
        print(f"錯誤：找不到示例詳細文件: {example_detail_file}")
        return False
    
    print(f"找到示例文件:")
    print(f"  步驟文件: {example_step_file}")
    print(f"  詳細文件: {example_detail_file}")
    
    try:
        # 測試 get_file_data_and_metadata 函數
        print("\n===== 測試文件數據提取 =====")
        file_data = get_file_data_and_metadata(
            step_source=example_step_file,
            detail_source=example_detail_file,
            is_example_file=True
        )
        
        print(f"文件數據提取成功:")
        print(f"  步驟DataFrame形狀: {file_data['step_df'].shape}")
        print(f"  詳細DataFrame形狀: {file_data['detail_df'].shape}")
        print(f"  步驟DataFrame列名: {file_data['step_df'].columns.tolist()}")
        print(f"  詳細DataFrame列名: {file_data['detail_df'].columns.tolist()}")
        
        # 檢查詳細數據的前幾行
        detail_df = file_data['detail_df']
        if not detail_df.empty:
            print(f"\n詳細DataFrame前3行:")
            print(detail_df.head(3))
            
            # 檢查是否有中文列名需要映射
            chinese_columns = [col for col in detail_df.columns if any(char > '\u4e00' and char < '\u9fff' for char in col)]
            if chinese_columns:
                print(f"\n發現中文列名: {chinese_columns}")
                
                # 顯示可能需要映射的列
                mapping_needed = {
                    "工步": "step_number",
                    "工步執行時間(秒)": "execution_time",
                    "電壓(V)": "voltage", 
                    "電流(A)": "current",
                    "Aux T1": "temperature",
                    "電量(Ah)": "capacity",
                    "能量(Wh)": "energy"
                }
                
                for chinese, english in mapping_needed.items():
                    if chinese in detail_df.columns:
                        print(f"  需要映射: '{chinese}' -> '{english}'")
                        unique_values = detail_df[chinese].nunique()
                        print(f"    唯一值數量: {unique_values}")
                        if chinese == "工步":
                            step_values = sorted(detail_df[chinese].unique())
                            print(f"    步驟編號: {step_values}")
        
        return True
        
    except Exception as e:
        print(f"測試失敗: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_measurement_saving_logic():
    """測試測量數據保存邏輯"""
    
    print("\n===== 測試測量數據保存邏輯 =====")
    
    # 創建模擬數據來測試保存邏輯
    test_detail_df = pd.DataFrame({
        'step_number': [1, 1, 1, 2, 2, 2],
        'execution_time': [0.0, 1.0, 2.0, 0.0, 1.0, 2.0],
        'voltage': [3.2, 3.3, 3.4, 3.4, 3.3, 3.2],
        'current': [1.0, 1.0, 1.0, -1.0, -1.0, -1.0],
        'temperature': [25.0, 25.1, 25.2, 25.2, 25.1, 25.0],
        'capacity': [0.0, 0.5, 1.0, 1.0, 0.5, 0.0],
        'energy': [0.0, 1.0, 2.0, 2.0, 1.0, 0.0]
    })
    
    test_step_mapping = {1: 101, 2: 102}  # step_number -> step_id
    
    print(f"測試數據:")
    print(f"  Detail DataFrame形狀: {test_detail_df.shape}")
    print(f"  Step mapping: {test_step_mapping}")
    print(f"  Detail DataFrame:")
    print(test_detail_df)
    
    try:
        # 這裡我們只是測試邏輯，不實際保存到數據庫
        # 我們可以檢查save_measurements_to_db函數的輸入驗證邏輯
        
        # 檢查必要列
        required_columns = ['step_number', 'execution_time', 'voltage', 'current']
        missing_columns = [col for col in required_columns if col not in test_detail_df.columns]
        
        print(f"\n驗證結果:")
        print(f"  必要列: {required_columns}")
        print(f"  缺少列: {missing_columns}")
        
        if not missing_columns:
            print("  ✓ 所有必要列都存在")
            
            # 檢查step_number匹配
            step_numbers_in_data = set(test_detail_df['step_number'].unique())
            step_numbers_in_mapping = set(test_step_mapping.keys())
            matching_steps = step_numbers_in_data.intersection(step_numbers_in_mapping)
            missing_steps = step_numbers_in_data - step_numbers_in_mapping
            
            print(f"  數據中的步驟編號: {sorted(step_numbers_in_data)}")
            print(f"  映射中的步驟編號: {sorted(step_numbers_in_mapping)}")
            print(f"  匹配的步驟編號: {sorted(matching_steps)}")
            print(f"  未匹配的步驟編號: {sorted(missing_steps)}")
            
            if matching_steps:
                print(f"  ✓ 有 {len(matching_steps)} 個步驟可以保存測量數據")
                
                # 計算可保存的行數
                valid_rows = test_detail_df[test_detail_df['step_number'].isin(matching_steps)]
                print(f"  ✓ 可保存 {len(valid_rows)} 行測量數據 (總共 {len(test_detail_df)} 行)")
            else:
                print("  ✗ 沒有匹配的步驟編號，無法保存測量數據")
        else:
            print(f"  ✗ 缺少必要列: {missing_columns}")
            
        return True
        
    except Exception as e:
        print(f"測試失敗: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("開始調試測試...")
    
    # 測試文件數據提取
    success1 = test_logging_with_example_files()
    
    # 測試測量數據保存邏輯  
    success2 = test_measurement_saving_logic()
    
    if success1 and success2:
        print("\n===== 測試完成 =====")
        print("所有測試都成功完成！現在可以運行實際的應用程序來查看詳細日誌。")
    else:
        print("\n===== 測試失敗 =====")
        print("一些測試失敗了，請檢查上面的錯誤信息。")
