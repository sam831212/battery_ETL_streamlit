#!/usr/bin/env python3
import sqlite3

def check_measurement_table():
    """檢查 Measurement 表的結構"""
    try:
        conn = sqlite3.connect('battery.db')
        cursor = conn.cursor()
        
        # 檢查表結構
        cursor.execute('PRAGMA table_info(measurement)')
        columns = cursor.fetchall()
        
        print("Measurements 表的欄位:")
        print("-" * 40)
        for column in columns:
            print(f"  {column[1]} ({column[2]})")
        
        # 檢查是否還有 SOC 欄位
        soc_columns = [col for col in columns if 'soc' in col[1].lower()]
        
        if soc_columns:
            print(f"\n⚠️  發現 SOC 相關欄位:")
            for col in soc_columns:
                print(f"  {col[1]} ({col[2]})")
        else:
            print(f"\n✅ 確認: Measurement 表中已經沒有 SOC 欄位")
        
        conn.close()
        
    except Exception as e:
        print(f"錯誤: {e}")

if __name__ == "__main__":
    check_measurement_table()
