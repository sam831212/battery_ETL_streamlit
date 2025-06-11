# Cell Filter 實驗篩選功能修復總結

## 問題描述
用戶報告 Dashboard 頁面中的 cell filter 功能無法正常工作，具體表現為：
- Cell table 的 UI 選擇控制項缺失
- 即使有 cell 選擇，也無法正確篩選 experiments table
- Cell 選擇與 experiment 篩選之間的級聯關係未建立

## 根本原因分析
通過代碼分析發現主要問題在於：

1. **UI 控制項缺失**：`render_filtering_controls()` 函數缺少 cell 相關的篩選控制項
2. **Cell 篩選邏輯未啟用**：Cell table 的篩選邏輯存在但被註解掉
3. **關鍵缺失**：`get_experiments_data()` 函數只接受 project IDs 參數，不支援 cell IDs 篩選

## 修復方案

### 1. 修復 UI 篩選控制項
**檔案**: `c:\Users\sam2_chen\DB0609\B\app\ui\components\dashboard_page\dashboard_components.py`

**修改函數**: `render_filtering_controls()`

**變更內容**:
```python
# 原本只有兩欄 (Project Filters, Experiment Filters)
col1, col2 = st.columns(2)

# 修改為三欄，新增 Cell Filters
col1, col2, col3 = st.columns(3)

# 新增第三欄的 Cell Filters 控制項
with col3:
    st.subheader("Cell Filters")
    
    # Cell Chemistry 多選
    cell_chemistries = st.multiselect(
        "Cell Chemistry",
        options=["NMC", "LFP", "LTO", "SIB", "Others"],
        default=st.session_state.dashboard_filters.get("cell_chemistries", []),
        key="cell_chemistries"
    )
    
    # Cell Capacity 範圍滑桿
    cell_capacity_range = st.slider(
        "Cell Capacity Range (Ah)",
        min_value=0.0,
        max_value=100.0,
        value=st.session_state.dashboard_filters.get("cell_capacity_range", (0.0, 100.0)),
        step=0.1,
        key="cell_capacity_range"
    )
    
    # Cell Form Factor 多選
    cell_form_factors = st.multiselect(
        "Cell Form Factor",
        options=["Prismatic", "cylindrical", "pouch", "others"],
        default=st.session_state.dashboard_filters.get("cell_form_factors", []),
        key="cell_form_factors"
    )

# 更新 session state
st.session_state.dashboard_filters.update({
    "cell_chemistries": cell_chemistries,
    "cell_capacity_range": cell_capacity_range,
    "cell_form_factors": cell_form_factors
})
```

### 2. 啟用 Cell Table 篩選
**檔案**: `c:\Users\sam2_chen\DB0609\B\app\ui\dashboard_page.py`

**修改位置**: `tab_cells` 區塊

**變更內容**:
```python
# 原本被註解的篩選邏輯
# 若有 cell filter，這裡可加 apply_filters(cells_df, "cells")

# 修改為實際執行篩選
cells_df = apply_filters(cells_df, "cells")
```

### 3. 修復核心篩選邏輯
**檔案**: `c:\Users\sam2_chen\DB0609\B\app\services\DB_fetch_service.py`

**修改函數**: `get_experiments_data()`

**原始函數簽名**:
```python
def get_experiments_data(selected_project_ids: Optional[List[int]] = None) -> pd.DataFrame:
    """Fetch experiments, optionally filtered by project IDs"""
```

**修改後函數簽名**:
```python
def get_experiments_data(selected_project_ids: Optional[List[int]] = None, selected_cell_ids: Optional[List[int]] = None) -> pd.DataFrame:
    """Fetch experiments, optionally filtered by project IDs and/or cell IDs"""
```

**查詢邏輯變更**:
```python
# 原本只篩選 project_id
query = select(Experiment)
if selected_project_ids:
    query = query.where(col(Experiment.project_id).in_(selected_project_ids))

# 修改後同時支援 project_id 和 cell_id 篩選
query = select(Experiment)
if selected_project_ids:
    query = query.where(col(Experiment.project_id).in_(selected_project_ids))
if selected_cell_ids:
    query = query.where(col(Experiment.cell_id).in_(selected_cell_ids))
```

### 4. 更新函數調用
**檔案**: `c:\Users\sam2_chen\DB0609\B\app\ui\dashboard_page.py`

**修改位置**: `tab_experiments` 區塊

**變更內容**:
```python
# 原本只傳遞 selected_projects
experiments_df = get_experiments_data(st.session_state.selected_projects)

# 修改為同時傳遞 selected_projects 和 selected_cells
experiments_df = get_experiments_data(st.session_state.selected_projects, st.session_state.selected_cells)
```

## 函數調用關係圖

```
Dashboard Page 渲染流程:
│
├── render_dashboard_page()
│   │
│   ├── render_filtering_controls()           # UI 篩選控制項
│   │   └── 更新 st.session_state.dashboard_filters
│   │
│   ├── tab_projects                          # Projects Tab
│   │   ├── get_projects_data()              # 獲取所有 projects
│   │   ├── create_interactive_table()       # 創建可選擇表格
│   │   └── extract_selected_ids()           # 提取選中的 project IDs
│   │       └── 更新 st.session_state.selected_projects
│   │
│   ├── tab_cells                            # Cells Tab
│   │   ├── get_cells_data()                 # 獲取所有 cells
│   │   ├── apply_filters(cells_df, "cells") # 應用 cell 篩選邏輯
│   │   ├── create_interactive_table()       # 創建可選擇表格
│   │   └── extract_selected_ids()           # 提取選中的 cell IDs
│   │       └── 更新 st.session_state.selected_cells
│   │
│   ├── tab_experiments                      # Experiments Tab
│   │   ├── get_experiments_data(            # 獲取篩選後的 experiments
│   │   │     selected_projects,             # 傳入選中的 projects
│   │   │     selected_cells                 # 傳入選中的 cells ← 新增
│   │   │   )
│   │   ├── apply_filters(experiments_df, "experiments")
│   │   ├── create_interactive_table()
│   │   └── extract_selected_ids()
│   │       └── 更新 st.session_state.selected_experiments
│   │
│   └── tab_steps                           # Steps Tab
│       ├── get_steps_data(selected_experiments)
│       ├── apply_filters(steps_df, "steps")
│       └── create_interactive_table()
```

## 資料庫關聯關係

```
Cell → Experiment → Step → Measurement
 │        │
 │        └── Project (可選)
 │        └── Machine (可選)
 └── 一對多關聯 (cell_id 外鍵)

篩選邏輯:
1. Cell 選擇 → 篩選有相同 cell_id 的 Experiments
2. Project 選擇 → 篩選有相同 project_id 的 Experiments  
3. 兩者可同時作用 (AND 邏輯)
```

## 篩選功能執行順序

1. **UI 控制項設定** → `render_filtering_controls()` 設定篩選參數
2. **Cell 表格篩選** → `apply_filters(cells_df, "cells")` 根據 UI 參數篩選 cells
3. **Cell 選擇** → 用戶在篩選後的 cell table 中選擇特定 cells
4. **Experiment 查詢** → `get_experiments_data()` 根據選中的 cells 和 projects 查詢 experiments
5. **Experiment 篩選** → `apply_filters(experiments_df, "experiments")` 進一步篩選
6. **級聯篩選** → Steps 根據選中的 experiments 進行篩選

## 修復效果

修復後的功能實現了完整的階層式篩選：
- ✅ Cell 篩選 UI 控制項正常顯示
- ✅ Cell 選擇能正確儲存到 session state  
- ✅ Cell 選擇能正確篩選 experiments table
- ✅ 支援 Project 和 Cell 的組合篩選
- ✅ 維持原有的階層式資料流 (Project/Cell → Experiment → Step)

## 技術重點

1. **參數傳遞**: 確保 `get_experiments_data()` 函數能接收並處理多個篩選條件
2. **SQL 查詢**: 使用 SQLModel 的 `where().in_()` 語法進行多條件查詢
3. **狀態管理**: 正確維護 Streamlit session state 中的選擇狀態
4. **UI 一致性**: 保持與現有 Project/Experiment 篩選邏輯的一致性

修復完成日期: 2025年6月11日
