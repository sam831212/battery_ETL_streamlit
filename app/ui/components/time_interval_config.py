"""
時間間隔配置組件
用於配置測量數據的時間間隔篩選以提升性能
"""

import streamlit as st
from typing import Optional

def render_time_interval_config(
    key_prefix: str = "time_interval",
    default_value: float = 0.0,
    help_text: Optional[str] = None
) -> float:
    """
    渲染時間間隔配置組件
    
    Args:
        key_prefix: 組件鍵前綴
        default_value: 預設值
        help_text: 幫助文字
        
    Returns:
        配置的時間間隔值
    """
    
    if help_text is None:
        help_text = (
            "設定時間間隔篩選以減少數據密度，提升處理性能。\n"
            "• 0 秒 = 保留所有數據點（無篩選）\n"
            "• 1 秒 = 每隔1秒保留一個數據點\n"
            "• 10 秒 = 每隔10秒保留一個數據點\n"
            "• 60 秒 = 每隔1分鐘保留一個數據點\n"
            "注意：總是保留每個步驟的第一個和最後一個數據點"
        )
    
    st.subheader("🕐 時間間隔篩選配置")
    
    # 預設選項
    preset_options = {
        "無篩選（保留所有數據）": 0.0,
        "1 秒間隔": 1.0,
        "5 秒間隔": 5.0,
        "10 秒間隔": 10.0,
        "30 秒間隔": 30.0,
        "1 分鐘間隔": 60.0,
        "5 分鐘間隔": 300.0,
        "自定義間隔": -1.0
    }
    
    # 預設選擇
    default_preset = "無篩選（保留所有數據）"
    for preset_name, preset_value in preset_options.items():
        if abs(preset_value - default_value) < 0.001:
            default_preset = preset_name
            break
    
    # 如果預設值不在預設選項中，選擇自定義
    if default_preset == "無篩選（保留所有數據）" and default_value != 0.0:
        default_preset = "自定義間隔"
    
    # 預設選項選擇
    preset_choice = st.selectbox(
        "選擇預設間隔：",
        options=list(preset_options.keys()),
        index=list(preset_options.keys()).index(default_preset),
        key=f"{key_prefix}_preset",
        help=help_text
    )
    
    # 獲取選擇的值
    if preset_choice == "自定義間隔":
        # 自定義輸入
        time_interval = st.number_input(
            "自定義時間間隔（秒）：",
            min_value=0.0,
            max_value=3600.0,
            value=max(0.0, default_value),
            step=0.1,
            key=f"{key_prefix}_custom",
            help="輸入自定義的時間間隔，範圍：0-3600秒"
        )
    else:
        time_interval = preset_options[preset_choice]
    
    # 顯示性能提示
    if time_interval > 0:
        st.info(f"⚡ 已設定 {time_interval} 秒間隔篩選，這將減少數據量並提升處理性能")
        
        # 估算數據減少量
        if time_interval >= 60:
            st.success(f"💡 建議：{time_interval/60:.1f}分鐘間隔適合長時間測試數據")
        elif time_interval >= 10:
            st.success(f"💡 建議：{time_interval}秒間隔適合中等密度數據")
        elif time_interval >= 1:
            st.success(f"💡 建議：{time_interval}秒間隔適合高密度數據")
        else:
            st.warning("💡 建議：小於1秒的間隔可能減少效果有限")
    else:
        st.warning("⚠️ 無篩選模式：將保留所有數據點，可能影響處理性能")
    
    return time_interval

def render_time_interval_summary(
    time_interval: float,
    original_count: Optional[int] = None,
    filtered_count: Optional[int] = None
) -> None:
    """
    渲染時間間隔篩選摘要
    
    Args:
        time_interval: 時間間隔
        original_count: 原始數據量
        filtered_count: 篩選後數據量
    """
    
    st.subheader("📊 時間間隔篩選摘要")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "設定間隔",
            f"{time_interval} 秒" if time_interval > 0 else "無篩選",
            help="設定的時間間隔篩選值"
        )
    
    with col2:
        if original_count is not None:
            st.metric(
                "原始數據量",
                f"{original_count:,} 行",
                help="篩選前的數據行數"
            )
    
    with col3:
        if filtered_count is not None and original_count is not None:
            reduction_rate = ((original_count - filtered_count) / original_count * 100) if original_count > 0 else 0
            st.metric(
                "篩選後數據量",
                f"{filtered_count:,} 行",
                f"-{reduction_rate:.1f}%",
                help="篩選後的數據行數及減少百分比"
            )
    
    # 性能影響提示
    if time_interval > 0 and original_count is not None and filtered_count is not None:
        if filtered_count < original_count * 0.5:
            st.success("🚀 優秀：數據量減少超過50%，處理性能將顯著提升")
        elif filtered_count < original_count * 0.8:
            st.info("✅ 良好：數據量減少20-50%，處理性能將有所提升")
        else:
            st.warning("⚠️ 有限：數據量減少少於20%，性能提升可能有限")
