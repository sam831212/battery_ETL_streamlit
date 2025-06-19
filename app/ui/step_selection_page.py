"""
步驟選擇 UI 元件 - Battery ETL 儀表板

此模組提供選擇與過濾電池測試步驟的 UI 元件
以便進行分析與資料庫載入。
"""
import streamlit as st
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any

from app.etl.transformation import calculate_soc


def format_range(start: float, end: float, format_str: str = "{:.2f}") -> str:
    """
    格式化一段數值範圍為字串。
    
    參數:
        start: 範圍的起始值
        end: 範圍的結束值
        format_str: 數值的格式字串
        
    回傳:
        範圍的字串表示
    """
    if pd.isna(start) or pd.isna(end):
        return "N/A"
    
    start_str = format_str.format(start)
    end_str = format_str.format(end)
    
    return f"{start_str} → {end_str}"


def init_step_selection_state():
    """
    初始化步驟選擇的會話狀態變數。
    """
    if 'full_discharge_step_idx' not in st.session_state:
        st.session_state.full_discharge_step_idx = None
    
    if 'selected_steps_for_db' not in st.session_state:
        st.session_state.selected_steps_for_db = []
        
    # 暫存的 DB 選擇，供更新前使用
    if 'temp_selected_steps_for_db' not in st.session_state:
        st.session_state.temp_selected_steps_for_db = []
        
    if 'steps_df_with_soc' not in st.session_state:
        st.session_state.steps_df_with_soc = None
        
    if 'details_df_with_soc' not in st.session_state:
        st.session_state.details_df_with_soc = None
        
    if 'filtered_step_types' not in st.session_state:
        st.session_state.filtered_step_types = ["charge", "discharge", "rest", "waveform"]
        
    # 暫存的參考步驟，供更新前使用
    if 'temp_reference_step_idx' not in st.session_state:
        st.session_state.temp_reference_step_idx = None
        
    # 標記是否需要更新
    if 'update_needed' not in st.session_state:
        st.session_state.update_needed = False
        
    # 儲存最後使用的步驟資料框，以便 SOC 計算
    if 'current_steps_df' not in st.session_state:
        st.session_state.current_steps_df = None


@st.cache_data
def calculate_step_ranges(steps_df: pd.DataFrame) -> pd.DataFrame:
    """
    計算步驟資料的範圍值。
    
    參數:
        steps_df: 包含步驟資料的資料框
        
    回傳:
        具有額外範圍欄位的資料框
    """
    # 建立副本以避免修改原始資料
    df = steps_df.copy()
    
    # 如果存在 SOC 欄位，則新增 SOC 範圍欄位
    if 'soc_start' in df.columns and 'soc_end' in df.columns:
        mask = pd.notna(df['soc_start']) & pd.notna(df['soc_end'])
        # SOC 值的格式字串為 "{:.1f}%"
        soc_start_formatted = df['soc_start'].apply(lambda x: "{:.1f}%".format(x) if pd.notna(x) else "")
        soc_end_formatted = df['soc_end'].apply(lambda x: "{:.1f}%".format(x) if pd.notna(x) else "")
        df['soc_range'] = np.where(mask, soc_start_formatted + " → " + soc_end_formatted, "N/A")
    else:
        df['soc_range'] = "N/A"
    
    # 如果存在 C-rate 欄位，則格式化並新增 C-rate 範圍欄位
    if 'c_rate' in df.columns:
        mask = pd.notna(df['c_rate'])
        # C-rate 的格式字串為 "{:.2f}C"
        c_rate_formatted = df['c_rate'].apply(lambda x: "{:.2f}C".format(x) if pd.notna(x) else "N/A")
        df['c_rate'] = c_rate_formatted
    else:
        df['c_rate'] = "N/A"
    
    # 如果存在溫度欄位，則新增溫度範圍欄位：顯示 temperature_start → temperature_end
    if 'temperature_start' in df.columns and 'temperature_end' in df.columns:
        mask = pd.notna(df['temperature_start']) & pd.notna(df['temperature_end'])
        temp_start_formatted = df['temperature_start'].apply(lambda x: "{:.1f}".format(x) if pd.notna(x) else "")
        temp_end_formatted = df['temperature_end'].apply(lambda x: "{:.1f}".format(x) if pd.notna(x) else "")
        df['temperature_range'] = np.where(mask, temp_start_formatted + " → " + temp_end_formatted, "N/A")
    else:
        df['temperature_range'] = "N/A"
    
    return df


def filter_steps_by_type(steps_df: pd.DataFrame, step_types: List[str]) -> pd.DataFrame:
    """
    根據步驟類型過濾步驟。
    
    參數:
        steps_df: 包含步驟資料的資料框
        step_types: 要包含的步驟類型列表
        
    回傳:
        過濾後的資料框
    """
    return steps_df[steps_df['step_type'].isin(step_types)]


def display_steps_table(steps_df: pd.DataFrame) -> Tuple[pd.DataFrame, Optional[int], List[int]]:
    """
    顯示步驟的表格，並提供選擇功能。
    
    參數:
        steps_df: 包含步驟資料的資料框
        
    回傳:
        Tuple，包含:
        - 過濾後的資料框
        - 選擇的全放電步驟索引（或 None）
        - 要載入資料庫的選擇步驟索引列表
    """
    # 初始化會話狀態（如果需要的話）
    init_step_selection_state()
    
    # --- 決定顯示用的 DataFrame ---
    # 若已經 pre-process 過，則顯示最新的 steps_df_with_soc
    # 若剛按下 Update Selections，則顯示最新的 steps_df_with_soc
    if st.session_state.steps_df_with_soc is not None:
        display_df = calculate_step_ranges(st.session_state.steps_df_with_soc)
    else:
        display_df = calculate_step_ranges(steps_df)
    # 讓 filtered_df 也指向最新的 display_df，確保後續顯示與選擇都用最新資料
    filtered_df = display_df.copy()

    # 根據步驟類型過濾
    st.subheader("工步篩選")
    
    # 讓使用者選擇要顯示的步驟類型
    available_step_types = sorted(display_df['step_type'].unique().tolist())
    
    # 只篩選可用的預設步驟類型
    # 如果 available_step_types 可能很大，則使用集合進行更快的查找
    available_step_types_set = set(available_step_types)
    filtered_defaults = [step_type for step_type in st.session_state.filtered_step_types 
                        if step_type in available_step_types_set]
    
    selected_step_types = st.multiselect(
        "選擇要顯示的工步類型：",
        options=available_step_types,
        default=filtered_defaults,
        key="step_type_filter",
        help="依工步類型（如充電、放電）篩選下方顯示的工步。"
    )
    
    # 更新會話狀態中的選擇的步驟類型
    st.session_state.filtered_step_types = selected_step_types
    
    # 根據選擇的步驟類型過濾
    if selected_step_types:
        filtered_df = filter_steps_by_type(display_df, selected_step_types)
    else:
        filtered_df = display_df
        
    # 檢查是否有放電步驟可供參考選擇
    discharge_steps = filtered_df[filtered_df['step_type'] == 'discharge']
    has_discharge_steps = not discharge_steps.empty
    
    if not has_discharge_steps:
        st.warning("目前篩選條件下沒有可用的放電工步，請調整篩選條件以包含放電工步。")
    
    # 準備顯示用的欄位    # 建立一個新的資料框以顯示，避免修改過濾後的資料
    display_cols = [
        'step_number', 
        'original_step_type', 
        'step_type', 
        'duration',  # 工步執行時間(秒)
        'c_rate', 
        'soc_range',
        'temperature_range',  # 改為顯示溫度範圍
    ]
    
    # 新增 full_discharge_reference 欄位以供選擇
    filtered_df['full_discharge_reference'] = False
    
    # 新增 db_selection 欄位以供選擇
    filtered_df['db_selection'] = False
    
    # 新增 data_meta 欄位（如不存在）
    if 'data_meta' not in filtered_df.columns:
        filtered_df['data_meta'] = ""
    # 若 session_state 有暫存的 data_meta，則帶入
    if 'temp_data_meta_dict' not in st.session_state:
        st.session_state.temp_data_meta_dict = {}
    for idx in filtered_df.index:
        if idx in st.session_state.temp_data_meta_dict:
            filtered_df.at[idx, 'data_meta'] = st.session_state.temp_data_meta_dict[idx]

    # 根據會話狀態更新
    if st.session_state.full_discharge_step_idx is not None:
        if st.session_state.full_discharge_step_idx in filtered_df.index:
            filtered_df.loc[st.session_state.full_discharge_step_idx, 'full_discharge_reference'] = True
    
    # 如果暫存的選擇是空的，則用已選擇的步驟初始化
    if not st.session_state.temp_selected_steps_for_db and st.session_state.selected_steps_for_db:
        st.session_state.temp_selected_steps_for_db = st.session_state.selected_steps_for_db.copy()
    
    # 在資料編輯器中顯示暫時的選擇
    # 這確保了 UI 顯示最新的核取方塊選擇
    for idx in st.session_state.temp_selected_steps_for_db:
        if idx in filtered_df.index:
            filtered_df.loc[idx, 'db_selection'] = True
    
    # 建立兩個區塊：一個用於參考選擇，一個用於資料庫選擇
    st.subheader("工步選擇")
    
    # 顯示步驟表格
    st.write("#### 選擇全放電參考工步（用於 SOC 計算）")
    discharge_only = filtered_df[filtered_df['step_type'] == 'discharge'].copy()
    
    # 只顯示放電步驟以供參考選擇
    if not discharge_only.empty:
        # 為選擇參考放電步驟建立單選按鈕
        # 只取前 5 個放電工步
        discharge_options = {
            f"Step {row['step_number']} ({row['original_step_type']})": idx 
            for idx, row in discharge_only.head(5).iterrows() # 只顯示前 5 個以供選擇
        }
        
        # 如果放電工步超過 5 個，顯示提示訊息
        if len(discharge_only) > 5:
            st.info(f"僅顯示前 5 個放電工步供參考選擇（目前篩選下共有 {len(discharge_only)} 個放電工步）。如需更多，請先進一步篩選工步。")
        
        # --- 新增：自動預設選第二個 CC放電 ---
        # 只有當 temp_reference_step_idx 尚未設定時才自動選擇
        if st.session_state.temp_reference_step_idx is None:
            # 找出前 5 個放電工步中 original_step_type == 'CC放電' 的 index
            cc_discharge_indices = [idx for idx, row in discharge_only.head(5).iterrows() if row.get('original_step_type', '') == 'CC放電']
            if len(cc_discharge_indices) >= 2:
                st.session_state.temp_reference_step_idx = cc_discharge_indices[1]
            elif len(cc_discharge_indices) == 1:
                st.session_state.temp_reference_step_idx = cc_discharge_indices[0]
            else:
                # 若沒有 CC放電，維持 None
                pass
        # ---
        # 根據會話狀態中的選擇，決定目前選項的索引
        current_idx = st.session_state.temp_reference_step_idx # 使用 temp 以便立即在 UI 中反映
        current_option = next(
            (k for k, v in discharge_options.items() if v == current_idx), 
            "None (Auto-detect)"
        )
        
        # 修正 index 取得方式，避免 ValueError
        if current_option in discharge_options.keys():
            current_index = list(discharge_options.keys()).index(current_option)
        else:
            current_index = 0  # 預設選第一個

        selected_reference_option = st.radio(
            "選擇一個放電工步作為 0% SOC 參考：",
            options=list(discharge_options.keys()),
            index=current_index,
            key="reference_step_selector",
            help="選擇一個代表完全放電狀態（0% SOC）的放電工步。此選擇對於所有工步的 SOC 計算至關重要。僅顯示前 5 個放電工步，如需更多請先篩選。"
        )
        
        selected_reference_idx = discharge_options[selected_reference_option]
        
        # 將選擇儲存到暫存狀態中，並設置更新標誌
        if selected_reference_idx != st.session_state.temp_reference_step_idx:
            st.session_state.temp_reference_step_idx = selected_reference_idx
            st.session_state.update_needed = True
    else:
        st.info("目前無可用的放電工步作為參考，請調整篩選條件以包含放電工步。")
        selected_reference_idx = None
      # 顯示資料庫載入選擇的區塊
    st.write("#### 選擇要載入資料庫的工步")
    st.caption("請檢查下方工步，並使用「選擇載入資料庫」欄位的勾選框標記要納入最終資料集的工步。您也可以在「資料備註 (data_meta)」欄位輸入備註，**請記得點擊「Apply DB Selection Changes」以儲存您的 dataMeta 輸入**。請確保已選擇上方的『全放電參考工步』以正確計算 SOC，然後點擊『Update Selections』。")
    
    # 如果資料框中不存在 db_selection 欄位，則新增
    if 'db_selection' not in filtered_df.columns:
        filtered_df['db_selection'] = False
        
    # 根據會話狀態設置 db_selection 的初始值
    for idx_val in filtered_df.index: # 使用 idx_val 以避免與外部作用域的 idx 衝突
        filtered_df.loc[idx_val, 'db_selection'] = idx_val in st.session_state.temp_selected_steps_for_db
    
    # 建立一個表單來包裝資料編輯器
    with st.form(key="step_selection_form"):
        # 建立一個資料編輯器以進行多重選擇
        edited_df = st.data_editor(
            filtered_df[display_cols + ['db_selection']],
            column_config={
                "step_number": st.column_config.NumberColumn("工步編號"),
                "original_step_type": st.column_config.TextColumn("原始工步類型"),
                "step_type": st.column_config.TextColumn("工步動作"),
                "c_rate": st.column_config.TextColumn("充放電倍率"),
                "soc_range": st.column_config.TextColumn("SOC範圍"),
                "temperature_range": st.column_config.TextColumn("溫度範圍", help="起始溫度 → 截止溫度"),
                "duration": st.column_config.NumberColumn("工步執行時間(秒)", format="%.1f"),
                "data_meta": st.column_config.TextColumn("資料備註 (data_meta)", help="可選，為此工步輸入備註/說明，將一併存入資料庫。"),
                "db_selection": st.column_config.CheckboxColumn("選擇載入資料庫", help="勾選以將此工步納入資料庫。"),
            },
            hide_index=True,
            use_container_width=True,
            key="step_selection_table"
        )
        
        # 在右側添加表單提交按鈕
        form_col1, form_col2 = st.columns([3, 1])
        with form_col2:
            submit_form = st.form_submit_button(
                "儲存資料庫選擇變更", 
                type="secondary", 
                help="點擊以確認上方勾選的工步將被納入資料庫。"
            )
      # 當表單提交時，更新暫存的會話狀態以反映 DB 選擇
    if submit_form:
        # 在 edited_df 中使用布林索引以提高效率
        selected_rows_in_edited_df = edited_df[edited_df['db_selection']]
        # 通過使用 selected_rows_in_edited_df 的索引來獲取原始索引
        # 這些行號可用於從 filtered_df 獲取原始索引。
        temp_selected_db_indices = [int(idx) for idx in filtered_df.index[selected_rows_in_edited_df.index].tolist()]        # 從資料編輯器捕獲 data_meta 的變更
        for row_position, row in edited_df.iterrows():
            # 直接使用 row_position 作為 index，這對應到 filtered_df 的 index
            st.session_state.temp_data_meta_dict[row_position] = row.get('data_meta', "")
        
        if set(temp_selected_db_indices) != set(st.session_state.temp_selected_steps_for_db):
            st.session_state.temp_selected_steps_for_db = temp_selected_db_indices
            st.session_state.update_needed = True # 如果需要重新計算 SOC，則指示 "Update Selections" 可能相關
            st.rerun() # 重新運行以立即反映核取方塊變更到 "Selected Steps Overview"
        
        # 顯示成功訊息
        st.success("✅ 工步選擇與資料備註已成功儲存！")
        
    selected_db_indices = [int(idx) for idx in st.session_state.selected_steps_for_db] # 這是 "Update Selections" 後最終確認的列表
    
    # 強制 selected_reference_idx 型別為 int 或 None，避免型別錯誤
    import numpy as np
    if isinstance(selected_reference_idx, (int, np.integer)):
        selected_reference_idx_int = int(selected_reference_idx)
    elif selected_reference_idx is None:
        selected_reference_idx_int = None
    else:
        selected_reference_idx_int = None
    return filtered_df, selected_reference_idx_int, selected_db_indices


def handle_reference_step_selection(
    steps_df: pd.DataFrame, 
    details_df: pd.DataFrame,
    full_discharge_step_idx: Optional[int] = None
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    處理參考步驟的選擇並重新計算 SOC 值。
    
    參數:
        steps_df: 包含步驟資料的資料框
        details_df: 包含詳細量測資料的資料框
        full_discharge_step_idx: 可選的放電步驟索引，用作參考
        
    回傳:
        Tuple，包含:
        - 更新的步驟資料框，帶有 SOC 值
        - 更新的詳細資料框，帶有 SOC 值
    """
    
    message = "正在重新計算 SOC，使用 "
    if full_discharge_step_idx is not None:
        message += "選定的放電步驟作為參考."
    else:
        message += "自動參考步驟偵測."
    
    with st.spinner(f"{message}..."):
        try:
            steps_with_soc, details_with_soc = calculate_soc(
                steps_df.copy(), 
                details_df.copy(),
                full_discharge_step_idx=full_discharge_step_idx
            )
            
            # 更新會話狀態
            st.session_state.steps_df_with_soc = steps_with_soc
            st.session_state.details_df_with_soc = details_with_soc
            
            # 成功訊息
            st.success("成功使用新的參考步驟重新計算 SOC！")
            
            return steps_with_soc, details_with_soc
            
        except Exception as e:
            st.error(f"重新計算 SOC 時發生錯誤。請檢查選定的參考步驟。詳細資訊: {str(e)}")
            st.info("確保選定的參考步驟具有有效的容量資料，並且適合用於定義 0% SOC。")
            # 如果出錯，返回原始資料框
            return steps_df, details_df


def display_selected_steps_overview(filtered_df: pd.DataFrame, selected_indices: List[int]):
    """
    顯示已選擇步驟的總覽。
    
    參數:
        filtered_df: 包含步驟資料的資料框
        selected_indices: 已選擇的步驟索引列表
    """
    if not selected_indices:
        st.info("尚未選擇任何工步進行資料庫載入，請於上方勾選工步。")
        return
    
    # 只顯示已選擇的步驟（安全起見）
    # 確保所有索引都存在於 filtered_df 中
    valid_indices = [idx for idx in selected_indices if idx in filtered_df.index]
    
    if not valid_indices:
        st.info("沒有有效的工步被選擇，請於上方勾選工步。")
        return
        
    selected_df = filtered_df.loc[valid_indices]
    
    st.subheader("已選工步總覽")
    
    # 顯示按步驟類型統計
    step_type_counts = selected_df['step_type'].value_counts().reset_index()
    step_type_counts.columns = ['步驟類型', '數量']
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write(f"已選工步總數：{len(selected_df)}")
        st.dataframe(step_type_counts, hide_index=True)
    
    with col2:
        # 顯示已選步驟類型的圓餅圖
        import plotly.express as px
        fig = px.pie(
            step_type_counts, 
            values='數量', 
            names='步驟類型', 
            title='已選工步類型分布'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # 顯示已選擇的工步表格
    st.write("已選擇的工步：")
    display_cols = [
        'step_number', 
        'original_step_type', 
        'step_type', 
        'c_rate', 
        'soc_range', 
        'temperature_range',  # 改為顯示溫度範圍
        'duration',
        'data_meta',   # 顯示 data_meta
    ]    # 先確保 session_state 有 temp_data_meta_dict
    if 'temp_data_meta_dict' not in st.session_state:
        st.session_state.temp_data_meta_dict = {}
    
    # 在顯示前同步 session_state 中的 data_meta 到 DataFrame
    for idx in selected_df.index:
        if idx in st.session_state.temp_data_meta_dict:
            selected_df.at[idx, 'data_meta'] = st.session_state.temp_data_meta_dict[idx]
    
    # 使用 st.form 包裝 data_editor 以避免即時 reload
    with st.form(key="selected_steps_data_meta_form"):
        # 只允許 data_meta 欄位可編輯
        edited_selected_df = st.data_editor(
            selected_df[display_cols],
            column_config={
                "step_number": st.column_config.NumberColumn("工步編號", disabled=True),
                "original_step_type": st.column_config.TextColumn("原始工步類型", disabled=True),
                "step_type": st.column_config.TextColumn("工步動作", disabled=True),
                "c_rate": st.column_config.TextColumn("充放電倍率", disabled=True),
                "soc_range": st.column_config.TextColumn("SOC範圍", disabled=True),
                "temperature_range": st.column_config.TextColumn("溫度範圍", help="起始溫度 → 截止溫度", disabled=True),
                "duration": st.column_config.NumberColumn("工步執行時間(秒)", format="%.1f", disabled=True),
                "data_meta": st.column_config.TextColumn("資料備註 (data_meta)", help="可選，為此工步輸入備註/說明，將一併存入資料庫。"),
            },
            hide_index=True,
            use_container_width=True,
            key="selected_steps_data_meta_editor"
        )
        # 添加保存按鈕
        form_col1, form_col2 = st.columns([3, 1])
        with form_col2:
            save_data_meta = st.form_submit_button("儲存資料備註", type="secondary")
    # 當按下保存按鈕時，將 data_meta 寫回 session_state
    if save_data_meta:
        for idx, row in edited_selected_df.iterrows():
            st.session_state.temp_data_meta_dict[idx] = row.get('data_meta', "")
        st.success("資料備註已成功儲存！")
        st.rerun()  # 重新運行以更新顯示


def create_processing_controls():
    """
    建立前處理和資料庫載入的按鈕。
    
    回傳:
        Tuple，包含:
        - 布林值，指示前處理按鈕是否被點擊
        - 布林值，指示載入資料庫按鈕是否被點擊
    """
    st.subheader("處理控制")
    
    col1, col2 = st.columns(2)
    
    # 只保留 Load to Database 按鈕
    preprocess_clicked = False
    with col2:
        load_db_clicked = st.button(
            "載入資料庫",
            type="secondary",
            use_container_width=True,
            disabled=(len(st.session_state.selected_steps_for_db) == 0 or st.session_state.steps_df_with_soc is None)
        )
        if len(st.session_state.selected_steps_for_db) == 0:
            st.info("請先選擇要載入資料庫的工步。")
        elif st.session_state.steps_df_with_soc is None:
            st.info("請先預處理工步再載入資料庫。")
    return preprocess_clicked, load_db_clicked


def validate_step_selections() -> bool:
    """
    驗證步驟選擇是否符合要求。
    
    回傳:
        布林值，指示選擇是否有效
    """
    # 檢查是否選擇了放電的參考步驟
    if st.session_state.full_discharge_step_idx is None:
        st.warning("請選擇一個放電工步作為 SOC 計算的參考。")
        return False
    
    # 檢查是否選擇了要載入資料庫的步驟
    if not st.session_state.selected_steps_for_db:
        st.warning("請至少選擇一個工步進行資料庫載入。")
        return False
    
    return True


def get_current_selections() -> Dict[str, Any]:
    """
    獲取當前的步驟選擇狀態。
    
    回傳:
        包含當前選擇的字典
    """
    return {
        'full_discharge_step_idx': st.session_state.full_discharge_step_idx,
        'selected_steps_for_db': st.session_state.selected_steps_for_db,
        'steps_df_with_soc': st.session_state.steps_df_with_soc,
        'details_df_with_soc': st.session_state.details_df_with_soc,
        'filtered_step_types': st.session_state.filtered_step_types
    }


def persist_selections():
    """
    將當前選擇儲存到會話狀態中。
    """
    # 已經在使用會話狀態進行持久化
    pass


def restore_selections() -> Dict[str, Any]:
    """
    從會話狀態中恢復選擇。
    
    回傳:
        包含恢復的選擇的字典
    """
    # 初始化會話狀態（如果需要的話）
    init_step_selection_state()
    
    # 返回當前選擇
    return get_current_selections()


def render_step_selection_page(steps_df: pd.DataFrame, details_df: pd.DataFrame):
    """
    渲染步驟選擇頁面的使用者介面。
    
    參數:
        steps_df: 包含步驟資料的資料框
        details_df: 包含詳細量測資料的資料框
    """
    st.header("工步選擇與處理")
    
    # 顯示有關已載入資料的資訊
    st.info(f"目前處理 {len(steps_df)} 筆工步與 {len(details_df)} 筆詳細量測資料。")
    
    # 初始化會話狀態（如果需要的話）
    init_step_selection_state()
    
    # 顯示步驟表格並獲取選擇
    filtered_df, selected_reference_idx, selected_db_indices = display_steps_table(steps_df)
    
    # 在選擇後添加更新按鈕，並附上說明文字
    st.info("請於上方完成選擇後點擊『更新』套用變更。未點擊更新前，變更不會生效。")
    update_col1, update_col2 = st.columns([3, 1])
    with update_col2:
        update_clicked = st.button("更新選擇", type="primary", key="update_button", use_container_width=True)
    
    # 當按鈕被點擊時，套用更新
    if update_clicked:
        # 從暫存中更新全放電步驟索引
        st.session_state.full_discharge_step_idx = st.session_state.temp_reference_step_idx
        
        # 從暫存中更新資料庫選擇的步驟
        st.session_state.selected_steps_for_db = st.session_state.temp_selected_steps_for_db
        
        # 儲存當前的 steps_df 以便 SOC 計算
        st.session_state.current_steps_df = steps_df
          # 使用更新的參考步驟計算 SOC
        if st.session_state.full_discharge_step_idx is not None or not st.session_state.filtered_step_types or st.session_state.temp_reference_step_idx != st.session_state.full_discharge_step_idx:
            # 重新計算的條件：如果設置了參考步驟，或者篩選條件改變，或者暫存的參考步驟與全放電步驟不一致
            
            current_steps_for_soc = st.session_state.current_steps_df if st.session_state.current_steps_df is not None else steps_df
            
            steps_with_soc, details_with_soc = handle_reference_step_selection(
                current_steps_for_soc, # 使用最初加載的或最後處理的完整 steps_df
                details_df, # 假設 details_df 相對靜態，或者在檔案變更時也會重新加載
                full_discharge_step_idx=st.session_state.full_discharge_step_idx # 使用確認的參考索引
            )
            
            # 保留 DATA_META：將使用者輸入的 dataMeta 添加到重新計算的資料框中
            if 'temp_data_meta_dict' in st.session_state and st.session_state.temp_data_meta_dict:
                # 如果不存在，則新增 data_meta 欄位
                if 'data_meta' not in steps_with_soc.columns:
                    steps_with_soc['data_meta'] = ""
                
                # 從會話狀態應用使用者輸入的 dataMeta
                for idx, data_meta_value in st.session_state.temp_data_meta_dict.items():
                    if idx in steps_with_soc.index:
                        steps_with_soc.at[idx, 'data_meta'] = data_meta_value
            
            # 更新將用於顯示和進一步處理的主要 steps_df
            st.session_state.steps_df_with_soc = steps_with_soc # 這是用於顯示的資料
            st.session_state.details_df_with_soc = details_with_soc
            
            # 重置更新所需的標誌
            st.session_state.update_needed = False
            
            # 強制重新運行以更新 UI 中的新值
            st.rerun()
    
    # 如果需要更新但尚未套用，則顯示警告
    if st.session_state.update_needed:
        st.warning("您有尚未套用的選擇變更，請點擊『更新』以套用。")
    
    # 顯示已選擇步驟的總覽
    display_selected_steps_overview(filtered_df, selected_db_indices)
    
    # 建立處理控制按鈕
    preprocess_clicked, load_db_clicked = create_processing_controls()
    
    # 處理載入資料庫按鈕的點擊事件
    if load_db_clicked:
        if validate_step_selections() and st.session_state.steps_df_with_soc is not None:
            # 準備選定步驟的資料，以便在元資料頁面使用
            selected_steps = []
            steps_df_with_soc = st.session_state.steps_df_with_soc
            details_df_with_soc = st.session_state.details_df_with_soc
            # 建立步驟資料字典的列表
            for step_idx in st.session_state.selected_steps_for_db:
                step_row = steps_df_with_soc.loc[step_idx].to_dict()
                # 加入 data_meta
                if 'temp_data_meta_dict' in st.session_state:
                    step_row['data_meta'] = st.session_state.temp_data_meta_dict.get(step_idx, "")
                selected_steps.append(step_row)
            
            # 將選定的步驟和相關資料儲存到會話狀態中，以便在元資料頁面使用
            st.session_state["selected_steps"] = selected_steps
            st.session_state["selected_steps_details_df"] = details_df_with_soc
            
            # 導航到元資料頁面
            st.session_state['current_page'] = "Meta Data"
            st.success("工步已選擇並可進行資料庫載入！即將導向 Meta Data 頁面...")
            st.rerun()
    
    # 返回當前的選擇狀態，以便其他元件使用
    return get_current_selections()