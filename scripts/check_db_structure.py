#!/usr/bin/env python3
"""
檢查資料庫結構腳本
"""
import sqlite3
import os

def check_database_structure():
    """檢查資料庫結構"""
    # 檢查資料庫文件
    db_files = ['battery.db', 'default.db']
    
    for db_file in db_files:
        if os.path.exists(db_file):
            print(f'\n=== {db_file} ===')
            conn = sqlite3.connect(db_file)
            cursor = conn.cursor()
            
            # 獲取所有表
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            table_names = [table[0] for table in tables]
            print(f'Tables: {table_names}')
            
            # 檢查是否有 measurement 表
            if 'measurement' in table_names:
                cursor.execute('PRAGMA table_info(measurement);')
                columns = cursor.fetchall()
                column_names = [col[1] for col in columns]
                print(f'Measurement table columns: {column_names}')
            else:
                print('measurement table NOT FOUND')
            
            # 檢查其他關鍵表
            for table in ['experiment', 'step', 'cell', 'machine']:
                if table in table_names:
                    print(f'{table} table EXISTS')
                else:
                    print(f'{table} table NOT FOUND')
            
            conn.close()
        else:
            print(f'{db_file} not found')

if __name__ == "__main__":
    check_database_structure()
