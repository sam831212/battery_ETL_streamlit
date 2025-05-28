#!/usr/bin/env python3
"""
測試資料庫連接腳本
"""
import sys
import os
from pathlib import Path

# 添加專案根目錄到路徑
sys.path.insert(0, str(Path(__file__).parent))

def test_database_connections():
    """測試所有資料庫連接"""
    print("=== 測試資料庫連接 ===")
    
    # 測試主要資料庫配置
    print("\n1. 測試 app.utils.config 配置:")
    try:
        from app.utils.config import DATABASE_URL, DB_PATH
        print(f"DB_PATH: {DB_PATH}")
        print(f"DATABASE_URL: {DATABASE_URL}")
    except Exception as e:
        print(f"錯誤: {e}")
    
    # 測試 database_service 的配置
    print("\n2. 測試 database_service 配置:")
    try:
        from app.services.database_service import engine
        print(f"Engine URL: {engine.url}")
    except Exception as e:
        print(f"錯誤: {e}")
    
    # 測試實際資料庫連接
    print("\n3. 測試實際連接:")
    try:
        from app.utils.database import test_db_connection
        success, error = test_db_connection()
        if success:
            print("✓ 主要資料庫連接成功")
        else:
            print(f"✗ 主要資料庫連接失敗: {error}")
    except Exception as e:
        print(f"✗ 測試連接時發生錯誤: {e}")

    # 檢查實際資料庫檔案
    print("\n4. 檢查資料庫檔案:")
    db_files = ['battery.db', 'default.db']
    for db_file in db_files:
        if os.path.exists(db_file):
            size = os.path.getsize(db_file)
            print(f"✓ {db_file} 存在 (大小: {size} bytes)")
        else:
            print(f"✗ {db_file} 不存在")

if __name__ == "__main__":
    test_database_connections()
