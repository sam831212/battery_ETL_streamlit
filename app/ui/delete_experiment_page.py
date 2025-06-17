import streamlit as st
from app.services.database_service import delete_experiment_and_related
from app.models import Experiment, Step, Measurement, ProcessedFile
from app.utils.database import get_session
from sqlmodel import select, func, func

st.title("刪除實驗（含步驟與量測資料）")

# 取得所有實驗
@st.cache_data(ttl=1)  # Cache for 1 second to avoid frequent DB calls
def load_experiments():
    try:
        with get_session() as session:
            return session.exec(select(Experiment)).all()
    except Exception as e:
        st.error(f"無法載入實驗資料：{e}")
        return []

experiments = load_experiments()

# Show success message if available
if "delete_success_message" in st.session_state:
    st.success(st.session_state.delete_success_message)
    del st.session_state.delete_success_message
    # Clear cache to reload experiments
    load_experiments.clear()
    experiments = load_experiments()

if not experiments:
    st.info("目前沒有可刪除的實驗。")
else:
    # Create a simple form for experiment selection and deletion
    with st.form("delete_experiment_form", clear_on_submit=False):
        # Create experiment options
        exp_options = {}
        for exp in experiments:
            label = f"ID {exp.id} | {exp.name} | {exp.battery_type}"
            exp_options[label] = exp.id
        
        # Select experiment
        selected_label = st.selectbox(
            "選擇要刪除的實驗：", 
            list(exp_options.keys())
        )
        selected_id = exp_options[selected_label]
        
        # Show experiment details
        selected_exp = next((exp for exp in experiments if exp.id == selected_id), None)
        if selected_exp:
            st.subheader("實驗詳細資訊")
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**實驗ID:** {selected_exp.id}")
                st.write(f"**實驗名稱:** {selected_exp.name}")
                st.write(f"**電池類型:** {selected_exp.battery_type}")
                st.write(f"**標稱容量:** {selected_exp.nominal_capacity} Ah")
            with col2:
                st.write(f"**操作員:** {selected_exp.operator or 'N/A'}")
                st.write(f"**開始日期:** {selected_exp.start_date}")
                st.write(f"**結束日期:** {selected_exp.end_date or 'N/A'}")
                st.write(f"**溫度:** {selected_exp.temperature or 'N/A'} °C")
            
            # 添加資料統計信息 - 讓用戶了解將要刪除的資料規模
            st.subheader("📊 相關資料統計")
            try:
                with get_session() as session:
                    # 計算 steps 數量
                    step_count = session.exec(
                        select(func.count()).select_from(Step).where(Step.experiment_id == selected_id)
                    ).one()
                    
                    # 計算 measurements 數量  
                    measurement_count = session.exec(
                        select(func.count()).select_from(Measurement)
                        .join(Step).where(Step.experiment_id == selected_id)
                    ).one()
                    
                    # 計算 processed files 數量
                    file_count = session.exec(
                        select(func.count()).select_from(ProcessedFile).where(ProcessedFile.experiment_id == selected_id)
                    ).one()
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Steps", step_count)
                    with col2:
                        st.metric("Measurements", f"{measurement_count:,}")
                    with col3:
                        st.metric("Files", file_count)
                    
                    # 警告大量資料
                    if measurement_count > 10000:
                        st.warning(f"⚠️ 此實驗包含大量測量資料 ({measurement_count:,} 個)，刪除可能需要較長時間")
                    
            except Exception as e:
                st.error(f"無法載入統計資訊：{e}")
            
          # Warning and confirmation
        st.markdown("---")
        st.error("⚠️ **警告：此操作將永久刪除實驗及其所有相關資料（步驟與量測），無法復原！**")
          # Confirmation checkbox
        confirm_delete = st.checkbox("我確認要刪除此實驗及其所有相關資料")
        
        # Submit button - always enabled, but check confirmation when clicked
        submitted = st.form_submit_button("🗑️ 刪除實驗", type="primary")
        experiment_name = selected_exp.name if selected_exp else f"ID {selected_id}"
        st.write(f"🔍 DEBUG: 開始處理實驗 '{experiment_name}' (ID: {selected_id}) 的刪除請求 (目前為NO-OP)")
        
        # Temporarily remove st.spinner to simplify
        # with st.spinner(f"正在處理實驗 '{experiment_name}'..."):
        try:
            st.write("🔍 DEBUG: 即將調用 delete_experiment_and_related 函數 (目前為 NO-OP)")
            delete_experiment_and_related(selected_id) # This is the NO-OP version
            st.write("🔍 DEBUG: delete_experiment_and_related (NO-OP) 函數調用完成")

            st.warning("🚧 DEBUG: 模擬刪除流程完成 (無實際刪除)。")
            st.info("🚧 DEBUG: 頁面應保持可見。如果頁面消失，問題可能在於 Streamlit 的表單提交/渲染機制。")
            st.info("🚧 DEBUG: 請檢查瀏覽器控制台是否有任何錯誤訊息 (通常按 F12 可以打開)。")

        except Exception as e:
            st.error(f"❌ 在模擬刪除流程中發生意外錯誤：{e}")
            st.write(f"🔍 DEBUG: 錯誤類型: {type(e).__name__}")
            import traceback
            st.write("🔍 DEBUG: 完整錯誤堆疊:")
            st.code(traceback.format_exc())
            st.warning("🔍 DEBUG: 錯誤已捕獲。如果頁面仍然消失，問題可能非常棘手。")
            
            st.write("🔍 DEBUG: 完整錯誤堆疊:")
            st.code(traceback.format_exc())
            
            # 從日誌分析可能的問題
            st.write("🔍 DEBUG: 從日誌分析:")
            st.write("- 看到了 ROLLBACK，表示資料庫事務被回滾")
            st.write("- 可能是因為大量資料刪除時出現異常")
            st.write("- 建議檢查資料庫鎖定或外鍵約束問題")
            
            # 防止頁面重新載入，保持調試信息可見
            st.write("🔍 DEBUG: 錯誤已捕獲，頁面不會重新載入")
