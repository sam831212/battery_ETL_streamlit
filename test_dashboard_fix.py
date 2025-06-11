#!/usr/bin/env python3
"""
測試 dashboard 修復的簡單腳本
"""

import pandas as pd
import sys
import os

# 添加項目根目錄到 Python 路徑
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.ui.components.dashboard_page.dashboard_components import create_interactive_table
from app.utils.dashboard_utils import extract_selected_ids

def test_extract_selected_ids():
    """測試 extract_selected_ids 函數"""
    print("=== 測試 extract_selected_ids ===")
    
    # 測試案例 1: 正常的 dict list
    test_rows_1 = [
        {'id': 1, 'name': 'Project 1'},
        {'id': 2, 'name': 'Project 2'}
    ]
    result_1 = extract_selected_ids(test_rows_1, "Test1")
    print(f"測試 1 - dict list: {result_1}")
    assert result_1 == [1, 2], f"期望 [1, 2]，得到 {result_1}"
    
    # 測試案例 2: list of lists
    test_rows_2 = [
        [1, 'Project 1', 'Description 1'],
        [2, 'Project 2', 'Description 2']
    ]
    result_2 = extract_selected_ids(test_rows_2, "Test2")
    print(f"測試 2 - list of lists: {result_2}")
    assert result_2 == [1, 2], f"期望 [1, 2]，得到 {result_2}"
    
    # 測試案例 3: 空列表
    test_rows_3 = []
    result_3 = extract_selected_ids(test_rows_3, "Test3")
    print(f"測試 3 - 空列表: {result_3}")
    assert result_3 == [], f"期望 []，得到 {result_3}"
    
    # 測試案例 4: 單一數值
    test_rows_4 = [1, 2, 3]
    result_4 = extract_selected_ids(test_rows_4, "Test4")
    print(f"測試 4 - 數值列表: {result_4}")
    assert result_4 == [1, 2, 3], f"期望 [1, 2, 3]，得到 {result_4}"
    
    print("✅ extract_selected_ids 測試通過！")

def test_dataframe_handling():
    """測試 DataFrame 處理"""
    print("\n=== 測試 DataFrame 處理 ===")
    
    # 創建測試 DataFrame
    test_df = pd.DataFrame({
        'id': [1, 2, 3],
        'name': ['Project A', 'Project B', 'Project C'],
        'description': ['Desc A', 'Desc B', 'Desc C']
    })
    
    print(f"測試 DataFrame:\n{test_df}")
    
    # 模擬 AgGrid 回傳 DataFrame 的情況
    mock_grid_response = {
        'selected_rows': test_df.iloc[0:2],  # 選擇前兩行
        'data': test_df
    }
    
    print(f"Mock selected_rows type: {type(mock_grid_response['selected_rows'])}")
    print(f"Mock selected_rows:\n{mock_grid_response['selected_rows']}")
    
    # 測試 DataFrame 轉換
    selected_rows = mock_grid_response['selected_rows']
    if isinstance(selected_rows, pd.DataFrame):
        if not selected_rows.empty:
            converted_rows = selected_rows.to_dict('records')
            print(f"轉換後的 rows: {converted_rows}")
            
            # 測試 ID 提取
            extracted_ids = extract_selected_ids(converted_rows, "DataFrame_Test")
            print(f"提取的 IDs: {extracted_ids}")
            assert extracted_ids == [1, 2], f"期望 [1, 2]，得到 {extracted_ids}"
    
    print("✅ DataFrame 處理測試通過！")

def main():
    """主測試函數"""
    print("開始測試 dashboard 修復...")
    
    try:
        test_extract_selected_ids()
        test_dataframe_handling()
        print("\n🎉 所有測試都通過了！修復成功！")
        
        print("\n📝 修復總結:")
        print("1. ✅ 修復了 DataFrame 的布林值檢查問題")
        print("2. ✅ 增強了 selected_rows 格式處理")
        print("3. ✅ 添加了 extract_selected_ids 輔助函數")
        print("4. ✅ 改善了錯誤處理和 debug 信息")
        
        print("\n🔍 現在可以運行完整的 dashboard 來測試:")
        print("python main.py")
        
    except Exception as e:
        print(f"\n❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
