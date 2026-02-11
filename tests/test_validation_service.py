# tests/services/test_validation_service.py
import pytest
import pandas as pd
from unittest.mock import patch, mock_open
import os

# 假設您的 validate_files 函數位於 app.services.validation_service
from app.services.validation_service import validate_files

# 測試案例的基礎路徑 (可選，如果您的測試檔案與 app 目錄在同一級別)
# 如果 validate_files 內部使用了相對路徑，您可能需要調整
TEST_BASE_PATH = os.path.dirname(__file__) # 或者指向您的專案根目錄

@pytest.fixture
def mock_csv_files(tmp_path):
    """
    創建一個 fixture 來模擬 CSV 檔案。
    tmp_path 是 pytest 的一個內建 fixture，用於創建臨時檔案和目錄。
    """
    step_valid_content = "Step_Index,Step_Type,Step_Name,Status\n1,Charge,Charge_1,Running"
    detail_valid_content = "Date_Time,Voltage,Current\n2023-01-01 00:00:00,3.5,1.0"
    step_invalid_content = "Wrong_Header_1,Step_Type,Step_Name,Status\n1,Charge,Charge_1,Running"
    detail_invalid_content = "Date_Time,Wrong_Voltage_Header,Current\n2023-01-01 00:00:00,3.5,1.0"

    files = {
        "step_valid.csv": step_valid_content,
        "detail_valid.csv": detail_valid_content,
        "step_invalid_headers.csv": step_invalid_content,
        "detail_invalid_headers.csv": detail_invalid_content,
        "step_empty.csv": "",
        "detail_empty.csv": ""
    }

    file_paths = {}
    for filename, content in files.items():
        file_path = tmp_path / filename
        file_path.write_text(content)
        file_paths[filename] = str(file_path)
    
    return file_paths

def test_validate_files_both_valid(mock_csv_files):
    """測試當兩個檔案都有效時的情況。"""
    step_file = mock_csv_files["step_valid.csv"]
    detail_file = mock_csv_files["detail_valid.csv"]

    step_valid, detail_valid, step_missing, detail_missing, _, _ = validate_files(step_file, detail_file)

    assert step_valid is True
    assert detail_valid is True
    assert len(step_missing) == 0
    assert len(detail_missing) == 0

def test_validate_files_step_invalid(mock_csv_files):
    """測試當步驟檔案標頭無效時的情況。"""
    step_file = mock_csv_files["step_invalid_headers.csv"]
    detail_file = mock_csv_files["detail_valid.csv"]
    
    # 預期的缺失標頭
    expected_step_missing = ["Step_Index"]

    step_valid, detail_valid, step_missing, detail_missing, _, _ = validate_files(step_file, detail_file)

    assert step_valid is False
    assert detail_valid is True
    assert sorted(step_missing) == sorted(expected_step_missing) # 排序以確保順序不影響比較
    assert len(detail_missing) == 0

def test_validate_files_detail_invalid(mock_csv_files):
    """測試當詳細資料檔案標頭無效時的情況。"""
    step_file = mock_csv_files["step_valid.csv"]
    detail_file = mock_csv_files["detail_invalid_headers.csv"]

    # 預期的缺失標頭
    expected_detail_missing = ["Voltage", "Current"] # 根據您的 REQUIRED_DETAIL_HEADERS

    step_valid, detail_valid, step_missing, detail_missing, _, _ = validate_files(step_file, detail_file)

    assert step_valid is True
    assert detail_valid is False
    assert len(step_missing) == 0
    assert sorted(detail_missing) == sorted(expected_detail_missing)

def test_validate_files_both_invalid(mock_csv_files):
    """測試當兩個檔案都無效時的情況。"""
    step_file = mock_csv_files["step_invalid_headers.csv"]
    detail_file = mock_csv_files["detail_invalid_headers.csv"]

    expected_step_missing = ["Step_Index"]
    expected_detail_missing = ["Voltage", "Current"]

    step_valid, detail_valid, step_missing, detail_missing, _, _ = validate_files(step_file, detail_file)

    assert step_valid is False
    assert detail_valid is False
    assert sorted(step_missing) == sorted(expected_step_missing)
    assert sorted(detail_missing) == sorted(expected_detail_missing)

def test_validate_files_file_not_found():
    """測試當檔案不存在時的情況。"""
    # 預期的缺失標頭 (因為檔案讀取會失敗)
    REQUIRED_STEP_HEADERS = ["Step_Index", "Step_Type", "Step_Name", "Status"]
    REQUIRED_DETAIL_HEADERS = ["Date_Time", "Voltage", "Current"]

    # 使用 patch 來模擬 st.error，因為它在 validate_files 的異常處理中被調用
    with patch('app.services.validation_service.st.error') as mock_st_error:
        step_valid, detail_valid, step_missing, detail_missing, step_headers, detail_headers = validate_files("non_existent_step.csv", "non_existent_detail.csv")

        assert step_valid is False
        assert detail_valid is False
        assert step_missing == REQUIRED_STEP_HEADERS # 預期返回所有必需的標頭作為缺失
        assert detail_missing == REQUIRED_DETAIL_HEADERS
        assert step_headers == [] # 預期標頭列表為空
        assert detail_headers == []
        mock_st_error.assert_called_once() # 驗證 st.error 被調用了一次

def test_validate_files_empty_csv(mock_csv_files):
    """測試當 CSV 檔案為空時的情況 (pandas 可能會拋出 EmptyDataError)。"""
    step_file = mock_csv_files["step_empty.csv"]
    detail_file = mock_csv_files["detail_empty.csv"]

    REQUIRED_STEP_HEADERS = ["Step_Index", "Step_Type", "Step_Name", "Status"]
    REQUIRED_DETAIL_HEADERS = ["Date_Time", "Voltage", "Current"]

    with patch('app.services.validation_service.st.error') as mock_st_error:
        step_valid, detail_valid, step_missing, detail_missing, step_headers, detail_headers = validate_files(step_file, detail_file)
        
        assert step_valid is False
        assert detail_valid is False
        # 根據您的函數實現，當 pd.read_csv 失敗時，它會返回所有必需的標頭
        assert step_missing == REQUIRED_STEP_HEADERS
        assert detail_missing == REQUIRED_DETAIL_HEADERS
        assert step_headers == []
        assert detail_headers == []
        mock_st_error.assert_called_once() # 驗證 st.error 被調用

# 如果您想測試 validate_files 是否被其他函數調用，您需要模擬 validate_files 本身
# 例如，如果您有一個名為 process_files 的函數調用了 validate_files：
#
# from app.some_module import process_files # 假設 process_files 在這裡
#
# @patch('app.services.validation_service.validate_files')
# def test_process_files_calls_validate_files(mock_validate_files, mock_csv_files):
#     # 設置 mock_validate_files 的返回值
#     mock_validate_files.return_value = (True, True, [], [], ["Step_Index"], ["Date_Time"])
#
#     step_file = mock_csv_files["step_valid.csv"]
#     detail_file = mock_csv_files["detail_valid.csv"]
#
#     process_files(step_file, detail_file) # 調用那個會調用 validate_files 的函數
#
#     # 斷言 validate_files 被以正確的參數調用了一次
#     mock_validate_files.assert_called_once_with(step_file, detail_file)
