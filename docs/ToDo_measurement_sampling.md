# ToDo: Measurement Detail Data Sampling by Config

## 目標
將 measurement detail data 載入資料庫時的精度，由原本全量，改為依 config 設定的間隔（如 0.1 秒）進行取樣。

---

## 主要修改點

1. **Config 設定**
   - 在 `.env` 與 `app/utils/config.py` 新增 `DETAIL_SAMPLING_INTERVAL`（如 0.1）。
   - 於 `config.py` 讀取該參數。

2. **ETL 資料載入流程**
   - `app/etl/extraction.py`：
     - `parse_detail_csv` 讀入 DataFrame 後，根據 `execution_time` 欄位與 config 進行取樣。
     - 取樣方式：每隔 interval 秒保留一筆（可用 `groupby` 或 `resample`）。
   - `load_and_preprocess_files`：如需傳遞 interval 參數，於此加入。

3. **資料轉換流程**
   - `app/etl/transformation.py`：
     - 檢查 `transform_data` 是否依賴 detail data 全量，必要時調整。

4. **測試**
   - 檢查 `tests/` 及 `test_save_measurements.py`、`test_user_flow_step_data.py` 等測試，是否需調整測試資料或驗證方式。

5. **文件**
   - 更新 `README.md` 或相關文件，說明 sampling 參數與設定方式。

---

## 實作步驟建議

1. 新增並測試 config 參數讀取。
2. 在 `parse_detail_csv` 完成取樣邏輯（可用 pandas `groupby` 或 `resample`）。
3. 測試資料載入流程，確認精度正確。
4. 調整並補充測試。
5. 更新文件。

---

## 其他注意事項
- 若未來需讓用戶自訂 sampling interval，可於 UI 或 CLI 增加選項。
- 若 detail data 欄位名稱或格式有異動，需同步調整。
