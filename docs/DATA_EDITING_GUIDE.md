# 數據編輯功能使用說明

## 概述
Battery ETL Dashboard 現在支持直接在 UI 中編輯資料庫中的數值。此功能允許用戶：
- 編輯單個記錄
- 批量編輯多個記錄
- 實時更新資料庫數據

## 支持的表格
- **Projects** (專案)
- **Cells** (電池)
- **Experiments** (實驗)
- **Steps** (步驟)

## 如何使用

### 1. 選擇記錄
1. 在相應的表格中選擇一個或多個記錄
2. 選擇後會顯示成功訊息和編輯按鈕

### 2. 單記錄編輯
- 選擇一個記錄後，點擊 **"✏️ 編輯選中記錄"** 按鈕
- 填寫編輯表單中的欄位
- 點擊 **"💾 保存變更"** 提交修改

### 3. 批量編輯
- 選擇多個記錄後，點擊 **"📝 批量編輯"** 按鈕
- 選擇要更新的欄位（勾選相應的複選框）
- 輸入新的值
- 點擊 **"💾 批量保存變更"** 提交修改

## 可編輯的欄位

### Projects (專案)
- `name` - 專案名稱
- `description` - 專案描述
- `start_date` - 開始日期

### Cells (電池)
- `name` - 電池名稱
- `manufacturer` - 製造商
- `chemistry` - 電池化學類型
- `nominal_capacity` - 標稱容量 (Ah)
- `nominal_voltage` - 標稱電壓 (V)
- `form_factor` - 形狀因子
- `serial_number` - 序列號
- `date_received` - 接收日期
- `notes` - 備註

### Experiments (實驗)
- `name` - 實驗名稱
- `description` - 實驗描述
- `battery_type` - 電池類型
- `nominal_capacity` - 標稱容量 (Ah)
- `temperature` - 溫度 (°C)
- `operator` - 操作員
- `start_date` - 開始日期


### Steps (步驟)
- `step_type` - 步驟類型 (charge/discharge/rest)
- `voltage_start` - 起始電壓 (V)
- `voltage_end` - 結束電壓 (V)
- `current` - 電流 (A)
- `capacity` - 容量 (Ah)
- `energy` - 能量 (Wh)
- `temperature_start` - 起始溫度 (°C)
- `temperature_end` - 結束溫度 (°C)
- `c_rate` - C 倍率
- `soc_start` - 起始 SOC (%)
- `soc_end` - 結束 SOC (%)
- `pre_test_rest_time` - 測試前休息時間 (s)

## 數據類型

### 數值欄位
- 支持小數點後 6 位精度
- 包括容量、電壓、電流、溫度等

### 日期時間欄位
- 提供日期選擇器和時間選擇器
- 自動組合為完整的日期時間

### 文本欄位
- 支持自由文本輸入
- 包括名稱、描述、操作員等

## 注意事項

1. **權限管理**: 確保有適當的資料庫寫入權限
2. **數據驗證**: 系統會驗證輸入的數據類型和格式
3. **即時更新**: 保存後頁面會自動刷新顯示最新數據
4. **錯誤處理**: 如果更新失敗，會顯示錯誤訊息
5. **備份建議**: 在進行大量修改前建議備份數據

## 安全性

- 所有編輯操作都會記錄 `updated_at` 時間戳
- 支持事務性操作，確保數據一致性
- 提供操作結果反饋，確保用戶了解操作狀態

## 故障排除

### 常見問題
1. **編輯按鈕不顯示**: 確保已選擇記錄
2. **保存失敗**: 檢查數據格式和資料庫連接
3. **頁面未刷新**: 手動刷新瀏覽器

### 錯誤訊息
- `Record not found`: 記錄不存在或已被刪除
- `Error updating record`: 資料庫更新失敗
- `No changes detected`: 沒有檢測到數據變更
