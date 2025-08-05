@echo off
REM 啟動 Streamlit 並自動開啟瀏覽器到 http://localhost:5000

REM 啟動 Streamlit 並監聽所有網絡接口，端口設置為 8501
streamlit run main.py --server.port 8501 --server.address 0.0.0.0 --server.headless true
