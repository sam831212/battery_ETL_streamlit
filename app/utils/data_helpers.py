"""General data conversion or helper utilities."""


import pandas as pd


from datetime import datetime


def convert_datetime_to_python(value):
    """
    將各種日期時間格式轉換為 Python datetime 物件

    Args:
        value: 輸入的日期時間值（可以是字串、pd.Timestamp 或 datetime）

    Returns:
        Python datetime 物件或 None
    """
    if value is None:
        return None

    if isinstance(value, datetime):
        return value

    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()

    if isinstance(value, str):
        try:
            return pd.to_datetime(value).to_pydatetime()
        except (ValueError, TypeError):
            return None

    return None