Metabase 原生查詢（Native Query）變數限制

原生查詢的變數（如 {{experiment_id}}）預設只能單選，無法像 GUI 問題那樣用下拉選單或關聯篩選器。
若要多選，SQL 需用 IN ({{experiment_id}})，並在 Metabase 設定變數型態為「多選」或「文字」。
原生查詢無法做「關聯篩選器」或自動下拉選單（只能用手動清單、搜尋、或 SQL 提供選項）。
GUI 問題（Query Builder）介紹

GUI 問題是在 Metabase 點「新問題」→「簡單查詢」或「自動查詢」建立的。
GUI 問題支援互動式篩選、下拉選單、關聯篩選器等功能，但無法處理複雜 SQL。
複雜查詢的解法：建立 View

你的查詢太複雜，無法用 GUI 問題，只能用原生查詢。
建議將複雜查詢寫成資料庫 View（檢視表），這樣 Metabase GUI 問題就能查詢 View，享受互動式篩選功能。
View 需在資料庫（如 SQLite、PostgreSQL）用 DBeaver 等工具建立。
DBeaver 等工具的用途

DBeaver 是開源、跨平台的資料庫管理工具，適合建立/修改 View。
只需用 DBeaver 建立 View，之後 Metabase 會自動同步，不需每次都開 DBeaver。
實作流程建議

用 Streamlit+Python 建立 .db 沒問題。
用 DBeaver 連線資料庫，執行 CREATE VIEW 建立 View。
在 Metabase 查詢 View，可用 GUI 問題互動查詢。
只有要修改 View 時才需再用 DBeaver。