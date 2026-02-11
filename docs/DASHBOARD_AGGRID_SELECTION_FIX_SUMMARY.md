# Dashboard AgGrid Selection Fix Summary

## 問題描述
- Streamlit AgGrid 在 dashboard 中的 selection（選取）功能失效。
- `selected_rows` 回傳型態不一致，有時為 list of dict，有時為 DataFrame、list of list、list of index、甚至 string。
- 導致 UI 永遠顯示 "Selected 0 ..."，無法正確選取、過濾與繪圖。
- 若直接對 DataFrame 做布林判斷，會出現 `ValueError: The truth value of a DataFrame is ambiguous...`。

## 修正重點
1. **DataFrame Index Reset**
   - 在傳入 AgGrid 前，強制 `df = df.reset_index(drop=True)`，避免 index 混亂導致回傳型態異常。

2. **Debug 訊息增強**
   - 詳細列印 AgGrid 回傳的 `selected_rows` 型態、內容、DataFrame 狀態，方便追蹤問題。

3. **selected_rows 格式自動修正**
   - 若 `selected_rows` 為 DataFrame，先轉成 list of dict。
   - 若為 list of list，嘗試用欄位名稱組成 dict。
   - 若為 index list，嘗試用 iloc 取回原始資料。
   - 只要能還原出 dict，後續流程都能正確運作。

4. **extract_selected_ids 輔助函數**
   - 統一處理各種 selection 格式，保證回傳 id list。
   - 支援 dict、list、DataFrame、index、string 等多種情境。

5. **UI/測試一致性驗證**
   - 單元測試與 UI 實際操作皆通過。
   - 測試腳本模擬 DataFrame、list、dict 等多種情境。

## 實際修正檔案
- `app/ui/dashboard_page.py`：主要修正 selection 處理、debug、id 提取。
- `test_dashboard_fix.py`、`test_dashboard_debug.py`：測試各種 selection 輸入情境。

## 結論
- Dashboard AgGrid selection 現已 robust 處理所有常見型態。
- UI 可正確選取、過濾、繪圖。
- 若未來 AgGrid/st_aggrid 行為有變，僅需擴充 `extract_selected_ids` 處理即可。
