#!/usr/bin/env python3
"""
簡單測試 operator 欄位功能
"""
import sqlite3
from datetime import datetime
import sys
import os

# 添加應用程式根目錄到路徑
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_operator_simple():
    """簡單測試建立實驗時 operator 欄位能否正確儲存"""
    print("=== 簡單測試 operator 欄位 ===")
    
    try:
        from app.models.database import Experiment, Cell, Machine, CellChemistry, CellFormFactor
        from app.utils.database import get_session
        
        print("✅ 模組導入成功")
        
        with get_session() as session:
            # 創建測試實驗，包含 operator 欄位
            test_operator = f"TestUser_{datetime.now().strftime('%H%M%S')}"
            experiment = Experiment(
                name=f"Operator Test {datetime.now().strftime('%Y%m%d_%H%M%S')}",
                description="Testing operator field",
                battery_type="LFP",
                nominal_capacity=20.0,
                temperature=25.0,
                operator=test_operator,
                start_date=datetime.now()
            )
            
            session.add(experiment)
            session.commit()
            session.refresh(experiment)
            
            print(f"✅ 成功創建實驗 ID: {experiment.id}")
            print(f"✅ operator 欄位值: '{experiment.operator}'")
            
            # 驗證資料庫中的實際值
            conn = sqlite3.connect('battery.db')
            cursor = conn.cursor()
            cursor.execute("SELECT operator FROM experiment WHERE id = ?", (experiment.id,))
            result = cursor.fetchone()
            conn.close()
            
            if result and result[0] == test_operator:
                print("🎉 測試成功！operator 欄位正確儲存到資料庫")
                return True
            else:
                print(f"❌ 測試失敗！實際值: {result}")
                return False
                
    except Exception as e:
        print(f"❌ 測試失敗: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("開始測試...")
    success = test_operator_simple()
    if success:
        print("\n🎉 operator 欄位功能正常！")
    else:
        print("\n❌ 測試失敗")
