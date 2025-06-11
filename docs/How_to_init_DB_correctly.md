# 如何正確初始化資料庫 (How to Initialize Database Correctly)

本文件記錄了在 Battery ETL Dashboard 專案中正確初始化資料庫的完整步驟，包括重置和添加新欄位的過程。

## 📋 完整的資料庫初始化流程

### 1. 更新資料模型 (Update Data Models)

首先在 `app/models/database.py` 中更新你的 SQLModel：

```python
class Step(BaseModel, table=True):
    """Model representing a test step within an experiment"""
    __table_args__ = {'extend_existing': True}
    
    # ... 其他欄位 ...
    
    # 新增欄位
    pre_test_rest_time: Optional[float] = Field(default=None, nullable=True)  # Duration of previous step, set automatically
    
    # ... 關聯設定 ...
```

### 2. 清理現有資料庫和遷移 (Clean Existing Database and Migrations)

如果需要完全重置資料庫：

```powershell
# 刪除資料庫檔案
Remove-Item -Path "battery.db" -Force -ErrorAction SilentlyContinue

# 刪除所有舊的遷移檔案 (保留 versions 資料夾)
Remove-Item -Path "migrations\versions\*" -Force -ErrorAction SilentlyContinue
```

### 3. 檢查 Alembic 配置 (Check Alembic Configuration)

確認 `alembic.ini` 設定正確：

```ini
[alembic]
script_location = migrations
sqlalchemy.url = sqlite:///battery.db
```

確認 `migrations/env.py` 正確導入模型：

```python
from app.models import database  # 確保導入所有模型
from sqlmodel import SQLModel
target_metadata = SQLModel.metadata
```

### 4. 生成初始遷移 (Generate Initial Migration)

```powershell
# 生成包含所有表格的初始遷移
alembic revision --autogenerate -m "Initial migration with pre_test_rest_time"
```

### 5. 修復遷移檔案中的導入問題 (Fix Import Issues in Migration)

檢查生成的遷移檔案（在 `migrations/versions/` 中），確保包含正確的導入：

```python
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes  # 確保這行存在
```

如果缺少 `sqlmodel.sql.sqltypes` 導入，需要手動添加。

### 6. 執行遷移 (Apply Migration)

```powershell
# 執行遷移，建立資料庫結構
alembic upgrade head
```

### 7. 驗證結果 (Verify Results)

檢查資料庫結構是否正確：

```powershell
# 檢查 Step 表格結構
python -c "
import sqlite3
conn = sqlite3.connect('battery.db')
cursor = conn.cursor()
cursor.execute('PRAGMA table_info(step);')
columns = cursor.fetchall()
print('Step table columns:')
for col in columns:
    print(f'  {col[1]} - {col[2]} (nullable: {not col[3]})')
conn.close()
"

# 檢查所有表格
python -c "
import sqlite3
conn = sqlite3.connect('battery.db')
cursor = conn.cursor()
cursor.execute('SELECT name FROM sqlite_master WHERE type=\'table\'')
tables = cursor.fetchall()
print('Database tables:')
for table in tables:
    print(f'  - {table[0]}')
conn.close()
"

# 檢查 Alembic 狀態
alembic current
```

## 🚨 常見錯誤和解決方案

### 錯誤 1: `NameError: name 'sqlmodel' is not defined`

**原因**: 遷移檔案缺少 `sqlmodel.sql.sqltypes` 導入

**解決方案**: 在遷移檔案頂部添加：
```python
import sqlmodel.sql.sqltypes
```

### 錯誤 2: Multiple heads error

**原因**: 有多個遷移檔案沒有正確的父子關係

**解決方案**:
```powershell
# 查看所有 heads
alembic heads

# 合併 heads
alembic merge heads -m "merge heads"

# 然後升級
alembic upgrade head
```

### 錯誤 3: Could not determine revision

**原因**: 遷移檔案缺少 `revision` 或 `down_revision` 標頭

**解決方案**: 刪除問題遷移檔案，重新使用 `alembic revision --autogenerate` 生成

## ✅ 最佳實踐

1. **永遠使用 `alembic revision --autogenerate`** 來生成遷移檔案
2. **不要手動創建遷移檔案**，除非你完全了解如何設定 revision 標頭
3. **刪除任何有問題的遷移檔案**，而不是試圖修復它們
4. **在修復遷移後，總是運行 `alembic upgrade head`** 確保資料庫是最新的
5. **定期檢查 `alembic current`** 來確認遷移狀態
6. **在重要變更前備份資料庫**

## 📝 新欄位說明

### `pre_test_rest_time` 欄位

- **類型**: `Optional[float]`
- **預設值**: `None`
- **用途**: 自動儲存前一個工步的執行時間（duration）
- **設定**: 系統自動設定，使用者不需手動輸入
- **規則**: 
  - 對於第一個工步（step_number = 1），值為 `None`
  - 對於其他工步，值等於前一個工步的 `duration` 值

## 🔄 日常更新流程

當需要添加新欄位時：

1. 更新 `app/models/database.py` 中的模型
2. 生成遷移：`alembic revision --autogenerate -m "Add new field"`
3. 檢查遷移檔案是否正確
4. 執行遷移：`alembic upgrade head`
5. 驗證結果

---

**創建日期**: 2025-06-11  
**最後更新**: 2025-06-11  
**適用版本**: SQLModel + Alembic
