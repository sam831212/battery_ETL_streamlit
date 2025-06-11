# Pre-test Rest Time 自動設定功能修復總結

## 修復日期
2025年6月11日

## 問題描述

`pre_test_rest_time` 欄位應該自動存儲每個工步的前一個工步執行時間（duration），但在實際操作中發現該欄位始終為 None。

## 根本原因分析

經過 debug 發現，問題出現在數據流水線的 ETL 轉換階段：

1. **ETL 轉換不完整**：`app/ui/preview_page.py` 中的 `apply_transformations` 函數只執行了部分轉換（C-rate 和 SOC 計算），但沒有調用完整的 `transform_data` 函數，因此沒有執行 `calculate_pre_test_rest_time`。

2. **數據流水線斷鏈**：
   - 在 Preview 頁面：只執行部分轉換，`pre_test_rest_time` 欄位缺失
   - 在 Meta Data 頁面：從 `steps_df_transformed` 取資料時，該欄位不存在
   - 寫入資料庫：Step ORM 獲得 None 值

## 數據流水線架構

### 完整數據流水線

```
Raw CSV Files
     ↓
┌─────────────────────────────────────────────────┐
│              ETL Extraction                     │
│  - parse_step_csv() / parse_detail_csv()       │
│  - 檔案格式驗證和資料清理                          │
└─────────────────────────────────────────────────┘
     ↓
┌─────────────────────────────────────────────────┐
│             ETL Transformation                  │
│  app/etl/transformation.py                     │
│  transform_data() 函數包含：                     │
│  1. calculate_c_rate()                         │
│  2. calculate_soc()                            │
│  3. calculate_pre_test_rest_time() ← 修復重點    │
└─────────────────────────────────────────────────┘
     ↓
┌─────────────────────────────────────────────────┐
│            Session State Storage                │
│  - steps_df_transformed                        │
│  - details_df_transformed                      │
│  - selected_steps (用戶選擇的工步)                │
└─────────────────────────────────────────────────┘
     ↓
┌─────────────────────────────────────────────────┐
│               UI Processing                     │
│  handle_selected_steps_save()                  │
│  從 transformed DataFrame 取資料                 │
└─────────────────────────────────────────────────┘
     ↓
┌─────────────────────────────────────────────────┐
│              Database Storage                   │
│  Step ORM → PostgreSQL                         │
│  pre_test_rest_time 欄位正確存儲                  │
└─────────────────────────────────────────────────┘
```

## 修復措施

### 1. 修復 ETL 轉換函數

**檔案**：`app/ui/preview_page.py`
**函數**：`apply_transformations()`

**修復前**：
```python
def apply_transformations(step_df, detail_df, nominal_capacity):
    # 只執行部分轉換
    step_df['c_rate'] = step_df['current'].apply(lambda x: calculate_c_rate(x, nominal_capacity))
    step_df, detail_df = calculate_soc(step_df, detail_df)
    # ❌ 沒有調用 calculate_pre_test_rest_time
```

**修復後**：
```python
def apply_transformations(step_df, detail_df, nominal_capacity):
    # 使用完整的 transform_data 函數
    from app.etl.transformation import transform_data
    step_df_transformed, detail_df_transformed = transform_data(step_df, detail_df, nominal_capacity)
    # ✅ 包含所有轉換：C-rate, SOC, pre_test_rest_time
```

### 2. 加強 Debug 功能

**檔案**：`app/etl/transformation.py`
**函數**：`calculate_pre_test_rest_time()`, `transform_data()`

加入詳細的 debug print 來追蹤：
- 每個工步的 duration 和 pre_test_rest_time 計算過程
- ETL 轉換完成後的欄位檢查
- 最終值的驗證

**檔案**：`app/ui/components/meta_data_page/selected_data_processing_ui.py`
**函數**：`handle_selected_steps_save()`

加入 debug print 來追蹤：
- transformed DataFrame 中是否包含 pre_test_rest_time 欄位
- 每個選擇工步的 pre_test_rest_time 值
- Step ORM 物件創建時的值設定

## 關鍵函數說明

### 1. calculate_pre_test_rest_time()
**位置**：`app/etl/transformation.py`
**功能**：計算每個工步的前一個工步執行時間
**邏輯**：
- 第一個工步：`pre_test_rest_time = None`
- 其他工步：`pre_test_rest_time = 前一個工步的 duration`

### 2. transform_data()
**位置**：`app/etl/transformation.py`
**功能**：完整的 ETL 轉換流程
**包含**：
1. C-rate 計算
2. SOC 計算
3. **pre_test_rest_time 計算** ← 修復的關鍵

### 3. apply_transformations()
**位置**：`app/ui/preview_page.py`
**功能**：在 Preview 頁面執行資料轉換
**修復**：改為調用完整的 `transform_data()` 函數

### 4. handle_selected_steps_save()
**位置**：`app/ui/components/meta_data_page/selected_data_processing_ui.py`
**功能**：將選擇的工步儲存到資料庫
**關鍵**：從 `steps_df_transformed` 取得包含 `pre_test_rest_time` 的資料

## 數據欄位流程

### pre_test_rest_time 欄位的完整生命週期

1. **計算階段**（ETL）：
   ```python
   # app/etl/transformation.py - calculate_pre_test_rest_time()
   for i in range(1, len(steps)):
       previous_duration = steps.iloc[i-1]['duration']
       steps.at[i, 'pre_test_rest_time'] = previous_duration
   ```

2. **存儲階段**（Session State）：
   ```python
   # app/ui/preview_page.py - apply_transformations()
   st.session_state['steps_df_transformed'] = step_df_transformed
   ```

3. **選擇階段**（UI）：
   ```python
   # app/ui/step_selection_page.py
   # 用戶選擇工步，pre_test_rest_time 值保持不變
   ```

4. **寫入階段**（Database）：
   ```python
   # app/ui/components/meta_data_page/selected_data_processing_ui.py
   step = Step(
       pre_test_rest_time=row_dict.get("pre_test_rest_time"),
       # ... 其他欄位
   )
   ```

## 驗證結果

修復後的 debug log 顯示：
```
[DEBUG] transformed_df 中 pre_test_rest_time 欄位存在，X/Y 個工步有值
[DEBUG] 工步 N: pre_test_rest_time = 1800.0 (類型: <class 'float'>)
[DEBUG] Step 物件 N: pre_test_rest_time = 1800.0
```

## 測試建議

1. **單元測試**：`test_pre_test_rest_time_simple.py` 驗證 `calculate_pre_test_rest_time` 函數邏輯
2. **整合測試**：在 UI 中上傳檔案 → 選擇工步 → 檢查資料庫中的值
3. **回歸測試**：確保修復不影響其他功能（C-rate, SOC 計算）

## 相關檔案清單

### 核心修復檔案
- `app/ui/preview_page.py` - ETL 轉換流程修復
- `app/etl/transformation.py` - 加強 debug 功能

### 相關檔案
- `app/ui/components/meta_data_page/selected_data_processing_ui.py` - UI 端 debug
- `app/models/database.py` - Step 模型定義
- `migrations/versions/add_pre_test_rest_time_*.py` - 資料庫 schema 更新

### 測試檔案
- `test_pre_test_rest_time_simple.py` - 單元測試腳本

## 總結

此次修復的關鍵在於發現數據流水線中的 ETL 轉換階段不完整，缺少 `pre_test_rest_time` 的計算。通過修復 `apply_transformations()` 函數，使其調用完整的 `transform_data()` 函數，成功解決了 `pre_test_rest_time` 欄位為 None 的問題。

修復後，整個數據流水線現在能夠：
1. ✅ 正確計算每個工步的 `pre_test_rest_time`
2. ✅ 在 transformed DataFrame 中包含該欄位
3. ✅ 在用戶選擇工步時保持正確的值
4. ✅ 成功寫入資料庫的 Step 表中

這確保了電池測試數據的完整性和可追溯性，為後續的數據分析和報告生成提供了必要的基礎數據。
