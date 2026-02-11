# Streamlit-AgGrid 顯示 Checkbox 問題修正紀錄 (2025/06/10)

## 問題描述
- 在 Streamlit Dashboard 專案中，使用 st_aggrid 1.1.5 版本時，表格無法顯示多選 checkbox。
- 原本的 `use_checkbox=True` 寫法僅適用於舊版 (0.3.x)，新版 (1.x) 需改用不同語法。
- 若將 checkbox 設定在被隱藏的欄位（如 id），checkbox 也不會顯示。

## 解決步驟
1. **確認 st_aggrid 版本**
   - 使用 1.1.5 版本，需採用新版語法。

2. **調整 checkbox 設定方式**
   - 不再於 `configure_selection` 使用 `use_checkbox` 參數。
   - 改為在 `GridOptionsBuilder` 設定時，於第一個未被隱藏的欄位（如 `step_number`、`step_type`、`name` 等）加上 `checkboxSelection=True`。
   - 於 `grid_options` 加入：
     ```python
     grid_options['rowSelection'] = selection_mode
     grid_options['suppressRowClickSelection'] = False
     ```

3. **自動選擇合適欄位**
   - 程式會自動尋找 `name`、`step_number`、`step_type`、`experiment_name` 等欄位，若無則選第一個非 id 欄位。
   - 確保 checkbox 一定顯示在表格最左側。

4. **測試結果**
   - Checkbox 已正確顯示於所有 AgGrid 表格。
   - 多選功能正常。

## 參考程式片段
```python
gb = GridOptionsBuilder.from_dataframe(df)
gb.configure_selection(selection_mode=selection_mode)
# 自動選擇合適欄位設 checkboxSelection
preferred_cols = ['name', 'step_number', 'step_type', 'experiment_name']
checkbox_col = ... # 自動尋找
if checkbox_col:
    gb.configure_column(checkbox_col, checkboxSelection=True)
grid_options = gb.build()
grid_options['rowSelection'] = selection_mode
grid_options['suppressRowClickSelection'] = False
```

## 備註
- 1.x 版 st_aggrid 的 checkbox 行為與 0.3.x 差異大，需特別注意欄位順序與隱藏設定。
- 若遇到 checkbox 不顯示，請優先檢查欄位設定與上述語法。
