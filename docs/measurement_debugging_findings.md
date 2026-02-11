# Measurement Debugging Findings - May 28, 2025
解決
總結一下我們進行的更改和原因（中文）：

問題描述： 您在 Streamlit 應用程式中將實驗數據（特別是測量數據 Measurement）保存到 SQLite 資料庫時，遇到了 "database is locked"（資料庫已鎖定）的錯誤。這個問題主要發生在 selected_data_processing_ui.py 文件中的 handle_selected_steps_save 函數，該函數會調用 database_service.py 中的 save_measurements_to_db 函數。

根本原因是在 handle_selected_steps_save 函數中，創建 Experiment（實驗）、多個 Step（步驟）以及隨後保存所有相關的 Measurement（測量數據）的整個過程都包含在一個單一的、長時間運行的資料庫事務中。儘管 save_measurements_to_db 函數本身被重構為對每個批次的測量數據使用獨立的事務，但這些內部的“子事務”與來自 UI 處理函數的外部“父事務”產生了衝突。

解決方案： 我們主要通過以下兩個步驟進行了重構：

在 database_service.py 的 save_measurements_to_db 函數中：

修改了 save_measurements_to_db 函數，使其分批處理和保存測量數據。
每個批次的數據都在其自己的 safe_session（安全會話）上下文中處理，這意味著每個批次都有自己獨立的資料庫事務（提交/回滾）。
retry_database_operation（資料庫操作重試）邏輯被應用於處理單個批次的操作，從而能在更細的粒度上重試因暫時性“資料庫鎖定”導致的錯誤。
在 selected_data_processing_ui.py 的 handle_selected_steps_save 函數中：

將原來那個單一的、龐大的資料庫事務進行了拆分。
首先，創建 Experiment 和 Step 對象，然後立即提交 (commit) 到資料庫。這樣做可以確保這些初始記錄被成功寫入，並釋放與這部分操作相關的任何資料庫鎖。
然後，再調用 save_measurements_to_db 函數。由於此時實驗和步驟數據已經被提交，save_measurements_to_db（及其內部的批次事務）在執行時就不會與 UI 處理函數中針對這些父實體數據的、長時間未關閉的事務發生衝突。
最後，ProcessedFile（已處理文件）記錄以及對 Experiment 的任何更新（例如 end_date 結束日期）會在一個新的事務中提交。
帶來的好處：

減少鎖競爭： 縮短了單個資料庫事務的持續時間，顯著降低了發生 "database is locked" 錯誤的機率。
提高穩健性： save_measurements_to_db 中的批次重試機制使得測量數據的保存過程對暫時性的資料庫鎖定更具彈性。
更清晰的事務邊界： 代碼邏輯更清晰，更容易理解每個原子性的資料庫操作包含哪些數據。
改進的錯誤恢復（部分）： 即使保存測量數據失敗，核心的 Experiment 和 Step 數據也已經成功持久化到資料庫中。

## Issue Summary

During testing of the battery data processing system, we discovered that measurements were not being properly saved to the database despite the UI showing successful processing messages (e.g., "Successfully saved 1982 measurements").

## Root Cause Analysis

### Initial Problem (Experiment 14)
- **Symptom**: Step 24 (step_number 9, type=discharge) had 0 measurements
- **Cause**: Issue in the measurement processing pipeline during "Selected data processing" workflow
- **Status**: ✅ **RESOLVED** - Step 24 now has 20 measurements

### Current Problem (Experiment 18)
- **Symptom**: Step 28 (step_number 21) shows 0 measurements despite UI claiming 1982 measurements saved
- **Cause**: Disconnect between UI success messages and actual database storage
- **Status**: 🛑 **CRITICAL - ROOT CAUSE IDENTIFIED**

## Key Findings

### 1. The `save_measurements_to_db` Function Works Correctly
- ✅ Successfully tested with synthetic data
- ✅ Proper error handling and batch processing
- ✅ Comprehensive logging and validation
- ✅ 100% success rate in isolated tests

### 2. UI vs Database Disconnect
- ❌ UI shows "Successfully saved X measurements" 
- ❌ Database shows 0 measurements in the actual tables
- 🔍 Suggests issue in the UI processing workflow, not the core saving function

### 3. Data Availability Confirmed
- ✅ All example CSV files contain the required step numbers (9, 21, etc.)
- ✅ Raw data has sufficient measurement records (59-68 rows per step)
- ✅ Step records are created correctly in the database
- ❌ Only the measurement records are missing

### 4. Database Locked Error (New)
- ❌ 發現 `sqlite3.OperationalError: database is locked` 錯誤，導致所有批次寫入失敗
- ❌ step_id=None，資料異常，應加強前置驗證
- ❌ UI 未正確顯示錯誤，仍顯示成功訊息

## Technical Investigation

### Database State Analysis
```
Experiment 14: "T"
- Step 24 (step_number 9): 20 measurements (after fix)
- ProcessedFiles: 2 records showing 9,672 detail rows processed

Experiment 18: "test" 
- Step 28 (step_number 21): 0 measurements
- UI claimed: 1982 measurements saved
- Actual: No measurement records found
- Error: (sqlite3.OperationalError) database is locked
```

### Processing Workflow Analysis
1. **File Upload**: ✅ Working correctly
2. **Step Creation**: ✅ Working correctly  
3. **Step Mapping**: ✅ Working correctly
4. **Measurement Processing**: ❌ Failing due to DB lock & data error
5. **UI Feedback**: ❌ Showing false success

## Files Modified During Investigation

### 1. `app/services/database_service.py`
- ✅ Fixed SQLModel deprecation warnings
- ✅ Enhanced error handling and logging
- ✅ Improved batch processing with validation
- ✅ Added comprehensive debug output
- ❌ 需加強 database locked 處理與 step_id 檢查

### 2. `app/ui/components/meta_data_page/selected_data_processing_ui.py`
- ✅ Updated to use the proven `save_measurements_to_db` function
- ✅ Added proper error handling
- ✅ Enhanced debugging output
- ❌ Still has silent failure issues
- ❌ 需加強錯誤顯示與 post-processing 驗證

### 3. Debug Scripts Created
- `debug_experiment_14.py` - Successfully identified and resolved experiment 14
- `debug_experiment_18.py` - Created to investigate current issue
- `debug_measurement_flow.py` - Comprehensive database state analysis

## Current Status

### ✅ Resolved Issues
1. **Experiment 14 measurements**: Fixed and verified
2. **`save_measurements_to_db` function**: Proven to work correctly
3. **Database schema**: Working properly
4. **Step creation**: Working correctly

### 🛑 Critical Issues (May 28, 2025)
1. **Database locked 導致所有寫入失敗**
2. **step_id=None 導致資料異常**
3. **UI 錯誤未顯示，誤導使用者**

### 🔍 Ongoing Issues
1. **UI false success messages**: Need to investigate why UI shows success when DB shows failure
2. **Silent measurement processing failures**: Error handling may be masking issues
3. **Large dataset processing**: Need to verify if 1000+ measurements cause issues

## Next Steps

### Immediate Actions Needed
1. **修正 database locked 問題**：檢查多重連線、分批 commit、確保 session 正確關閉
2. **step_id 檢查**：所有資料進 DB 前必須有正確 step_id，否則 raise error
3. **UI 錯誤顯示**：將 DB 寫入失敗訊息顯示給使用者，避免 false success
4. **Add transaction-level debugging** to the selected data processing workflow
5. **Investigate session state handling** during large dataset processing
6. **Add measurement count validation** after processing claims success
7. **Review error handling** in the UI workflow to prevent silent failures

### Recommended Fixes
1. **Add post-processing verification**: Always check actual measurement count after claiming success
2. **Improve error propagation**: Ensure UI shows actual errors rather than false success
3. **Add data consistency checks**: Verify step mapping and data integrity before processing
4. **Implement rollback mechanisms**: If measurement saving fails, rollback the entire experiment

## Testing Strategy

### Proven Working Components
- ✅ `save_measurements_to_db` function with small datasets (5-10 measurements)
- ✅ Step creation and mapping
- ✅ Database connectivity and schema

### Need Further Testing
- ❌ Large dataset processing (1000+ measurements)
- ❌ UI workflow error handling
- ❌ Session state management during long operations
- ❌ Memory usage during batch processing

## Lessons Learned

1. **UI success messages are not reliable** - Always verify against database
2. **The core measurement saving function works** - Issues are in the UI workflow
3. **Silent failures are dangerous** - Need better error propagation
4. **Debugging infrastructure is crucial** - Our debug scripts were essential
5. **Small test data vs large real data** - Different behavior patterns
6. **SQLite 適合單用戶小量資料，需考慮升級資料庫**

## Code Quality Improvements Made

1. **Enhanced logging throughout the measurement pipeline**
2. **Better error handling with specific error types**
3. **Comprehensive validation before and after operations**
4. **Debug scripts for ongoing monitoring**
5. **Fixed deprecation warnings for future compatibility**

---

**Summary**: The measurement saving functionality works correctly at the core level, but there are now critical issues: (1) database locked 導致所有寫入失敗，(2) step_id=None 資料異常，(3) UI 未正確顯示錯誤。需優先修正 DB locked 與資料驗證，並加強 UI 錯誤顯示與 post-processing 驗證。

## Measurement Data Processing - Issue Analysis & Solutions (2025/05/28)

### 問題摘要
- UI 顯示成功訊息，但資料庫實際未寫入 measurement 資料。
- step_id=None，導致所有 detail/measurement 資料寫入失敗。
- database locked 錯誤，批次寫入時發生。
- UI 未正確顯示錯誤，誤導使用者。

### 問題根因
1. **step_number mapping 問題**：
   - detail/measurement 資料依賴 step_id，若 step 尚未建立或 mapping 有誤，step_id 會是 None。
   - 目前流程為「先存 step，再存 detail」，但 mapping 或 commit 時機不當會導致查不到 step_id。
2. **資料驗證不足**：
   - 未在寫入前檢查 step_id 是否為 None。
   - UI 未顯示 DB 寫入失敗的真實錯誤。
3. **資料庫鎖定 (database locked)**：
   - 大量批次寫入時，session/transaction 管理不當，或多重連線導致鎖定。

### 可能解決方案

#### 1. 預先查詢/建立所有 step 並快取 step_id
- 在處理 detail/measurement 前，先分析所有 step_number，查詢/建立所有 step，取得完整的 step_number:step_id 對應表（dict）。
- 批次處理 detail 時直接用快取的 step_id，減少查詢與 mapping 問題。
- 優點：效能提升、避免 step_id=None、資料一致性高。

#### 2. 資料驗證與錯誤顯示
- 在寫入 measurement 前，檢查 step_id 是否為 None，若為 None 則 raise error 並記錄詳細訊息。
- UI 應顯示 DB 寫入失敗的真實錯誤，避免 false success。

#### 3. Transaction/Session 管理
- 用 transaction 包住 step 與 detail 的寫入，確保要嘛全部成功，要嘛全部 rollback。
- 批次 commit，減少 database locked 機率。
- 每次批次處理後，正確關閉 session。

#### 4. Post-processing 驗證
- 寫入後，立即查詢 DB 實際 measurement 筆數，與預期比對。
- 若不符，UI 顯示警告並記錄 log。

#### 5. 其他建議
- 增加 debug log，記錄 step_number 與 step_id 的 mapping 過程。
- 匯入前先比對 CSV 的 step_number 是否都存在於資料庫，若有缺漏則提示用戶。
- 若資料量大，考慮升級資料庫（如 PostgreSQL）。

### 可詢問的進一步問題
- 目前 `handle_file_processing_pipeline` 內部的 step/detail 寫入順序與 transaction 實作方式？
- 是否有多個 thread/process 同時寫入 DB？
- 目前 UI 如何捕捉與顯示 DB 寫入失敗的 exception？
- 是否有測試過小量資料能 100% 寫入成功？
- 是否有需要 sample code 來示範最佳實踐？

---
如需進一步協助，請提供 pipeline 內部邏輯或相關程式碼片段。
