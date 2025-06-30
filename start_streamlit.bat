@echo off
REM 啟動 Streamlit 並自動開啟瀏覽器到 http://localhost:5000

REM 啟動 Streamlit，指定 port 5000
start "" http://localhost:5000/
streamlit run main.py --server.port 5000 --server.headless true
