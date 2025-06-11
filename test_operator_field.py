#!/usr/bin/env python3
"""
測試 operator 欄位是否能正確儲存到資料庫
"""
import sqlite3
from datetime import datetime
import sys
import os

# 添加應用程式根目錄到路徑
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_operator_field():
    """測試建立實驗時 operator 欄位能否正確儲存"""
    print("=== 測試 operator 欄位儲存 ===")
    
    try:
        from app.models.database import Experiment, Cell, Machine, CellChemistry, CellFormFactor
        from app.utils.database import get_session
        print("✅ 模組導入成功")
        
        with get_session() as session:
            # 先檢查是否有 cell 和 machine
            cell = session.query(Cell).first()
            machine = session.query(Machine).first()
            
            # 如果沒有，創建測試用的 cell 和 machine
            if not cell:
                cell = Cell(
                    name="Test Cell for Operator",
                    chemistry=CellChemistry.LFP,
                    form_factor=CellFormFactor.PRISMATIC,
                    nominal_capacity=20.0
                )
                session.add(cell)
                session.flush()
                
            if not machine:
                machine = Machine(
                    name="Test Machine for Operator",
                    model_number="Test-001"
                )
                session.add(machine)
                session.flush()
            
            # 創建測試實驗，包含 operator 欄位
            test_operator = "Test Operator 123"
            experiment = Experiment(
                name=f"Operator Test Experiment {datetime.now().strftime('%Y%m%d_%H%M%S')}",
                description="Testing operator field storage",
                battery_type="LFP",
                nominal_capacity=20.0,
                temperature=25.0,
                operator=test_operator,  # 設定 operator
                start_date=datetime.now(),
                cell_id=cell.id,
                machine_id=machine.id
            )
            
            session.add(experiment)
            session.commit()
            session.refresh(experiment)
            
            print(f"✅ 成功創建實驗 ID: {experiment.id}")
            print(f"✅ operator 欄位值: '{experiment.operator}'")
            
            # 驗證資料庫中的實際值
            conn = sqlite3.connect('battery.db')
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, operator FROM experiment WHERE id = ?", (experiment.id,))
            result = cursor.fetchone()
            conn.close()
            
            if result:
                db_id, db_name, db_operator = result
                print(f"✅ 資料庫驗證 - ID: {db_id}, Name: {db_name}, Operator: '{db_operator}'")
                
                if db_operator == test_operator:
                    print("🎉 測試成功！operator 欄位正確儲存到資料庫")
                    return True
                else:
                    print(f"❌ 測試失敗！預期 operator: '{test_operator}', 實際: '{db_operator}'")
                    return False
            else:
                print("❌ 無法從資料庫中找到創建的實驗")
                return False
                
    except Exception as e:
        print(f"❌ 測試過程中發生錯誤: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def check_operator_column():
    """檢查 experiment 表是否有 operator 欄位"""
    print("=== 檢查資料庫結構 ===")
    
    try:
        conn = sqlite3.connect('battery.db')
        cursor = conn.cursor()
        cursor.execute('PRAGMA table_info(experiment)')
        columns = cursor.fetchall()
        conn.close()
        
        print("experiment 表的欄位:")
        operator_found = False
        for column in columns:
            column_name = column[1]
            column_type = column[2]
            print(f"  {column_name} ({column_type})")
            if column_name == 'operator':
                operator_found = True
        
        if operator_found:
            print("✅ operator 欄位存在於資料庫中")
            return True
        else:
            print("❌ operator 欄位不存在於資料庫中")        return False
            
    except Exception as e:
        print(f"❌ 檢查資料庫結構時發生錯誤: {str(e)}")
        return False

if __name__ == "__main__":
    print("開始測試 operator 欄位...")
    
    # 先檢查欄位是否存在
    if check_operator_column():
        # 然後測試儲存功能
        if test_operator_field():
            print("\n🎉 所有測試通過！operator 欄位功能正常")
        else:
            print("\n❌ 測試失敗")
    else:
        print("\n❌ 資料庫結構測試失敗")
        traceback.print_exc()
        return False
    
    try:
        with get_session() as session:
            # 先創建一個測試用的cell和machine（如果不存在）
            cell = session.query(Cell).first()
            if not cell:
                cell = Cell(
                    name="Test Cell for Operator",
                    chemistry=CellChemistry.LFP,
                    form_factor=CellFormFactor.PRISMATIC,
                    capacity=20.0
                )
                session.add(cell)
                session.flush()

            machine = session.query(Machine).first()
            if not machine:
                machine = Machine(
                    name="Test Machine for Operator",
                    model_number="TEST-001"
                )
                session.add(machine)
                session.flush()

            # 創建一個有operator欄位的實驗
            test_operator = "John Doe (Operator Test)"
            experiment = Experiment(
                name=f"Operator Field Test {datetime.now().strftime('%Y%m%d_%H%M%S')}",
                description="Testing operator field functionality",
                battery_type="LFP",
                nominal_capacity=20.0,
                temperature=25.0,
                operator=test_operator,  # 這是我們要測試的欄位
                start_date=datetime.now(UTC),
                cell_id=cell.id,
                machine_id=machine.id
            )
            
            # 儲存到資料庫
            session.add(experiment)
            session.commit()
            session.refresh(experiment)
            
            print(f"✅ 成功創建實驗 ID: {experiment.id}")
            print(f"✅ Operator欄位值: '{experiment.operator}'")
            
            # 重新從資料庫讀取，確認operator欄位已正確儲存
            retrieved_experiment = session.query(Experiment).filter(
                Experiment.id == experiment.id
            ).first()
            
            if retrieved_experiment and retrieved_experiment.operator == test_operator:
                print(f"✅ 成功！Operator欄位已正確儲存和讀取: '{retrieved_experiment.operator}'")
                return True
            else:
                print(f"❌ 失敗！讀取的operator值不正確: '{retrieved_experiment.operator if retrieved_experiment else 'None'}'")
                return False
                
    except Exception as e:
        print(f"❌ 資料庫操作失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    try:
        success = test_operator_field()
        if success:
            print("\n🎉 所有測試通過！operator欄位功能正常。")
        else:
            print("\n❌ 測試失敗！")
    except Exception as e:
        print(f"\n❌ 測試過程中發生錯誤: {str(e)}")
        import traceback
        traceback.print_exc()
