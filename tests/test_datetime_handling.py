import unittest
from datetime import datetime
import pandas as pd
from app.ui.refactored_upload import convert_datetime_to_python

class TestDateTimeHandling(unittest.TestCase):
    def test_convert_datetime_to_python(self):
        # 測試字串日期時間
        test_cases = [
            # 輸入值, 預期類型
            ("2025-04-01T02:34:54", datetime),
            ("2025-04-01 02:34:54", datetime),
            (pd.Timestamp("2025-04-01T02:34:54"), datetime),
            (datetime(2025, 4, 1, 2, 34, 54), datetime),
            (None, type(None)),
        ]
        
        for input_value, expected_type in test_cases:
            with self.subTest(input_value=input_value):
                result = convert_datetime_to_python(input_value)
                self.assertIsInstance(result, expected_type)
                if result is not None:
                    self.assertTrue(isinstance(result, datetime))

if __name__ == '__main__':
    unittest.main() 