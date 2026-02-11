"""
時間間隔篩選配置文件
用戶可以根據需要調整這些設定
"""

# 時間間隔篩選預設配置
TIME_INTERVAL_PRESETS = {
    "ultra_high_density": {
        "name": "超高密度數據",
        "interval": 0.1,
        "description": "適用於每秒10個以上數據點的場景",
        "use_case": "實驗室精密測試、短時間高頻測量"
    },
    "high_density": {
        "name": "高密度數據", 
        "interval": 1.0,
        "description": "適用於每秒1-10個數據點的場景",
        "use_case": "標準電池測試、充放電循環"
    },
    "medium_density": {
        "name": "中密度數據",
        "interval": 10.0,
        "description": "適用於每10秒1個數據點的場景", 
        "use_case": "長時間穩定性測試"
    },
    "low_density": {
        "name": "低密度數據",
        "interval": 60.0,
        "description": "適用於每分鐘1個數據點的場景",
        "use_case": "長期老化測試、容量衰減監控"
    },
    "very_low_density": {
        "name": "極低密度數據",
        "interval": 300.0,
        "description": "適用於每5分鐘1個數據點的場景",
        "use_case": "超長期監控、月度/年度分析"
    }
}

# 根據數據類型的建議配置
DATA_TYPE_RECOMMENDATIONS = {
    "charge_discharge_cycle": {
        "recommended_interval": 1.0,
        "max_recommended": 10.0,
        "reason": "充放電循環需要保留足夠的電壓電流變化細節"
    },
    "capacity_test": {
        "recommended_interval": 5.0,
        "max_recommended": 30.0,
        "reason": "容量測試重點關注容量變化趨勢"
    },
    "impedance_test": {
        "recommended_interval": 0.1,
        "max_recommended": 1.0,
        "reason": "阻抗測試需要高頻響應數據"
    },
    "aging_test": {
        "recommended_interval": 60.0,
        "max_recommended": 300.0,
        "reason": "老化測試關注長期趨勢變化"
    },
    "temperature_test": {
        "recommended_interval": 10.0,
        "max_recommended": 60.0,
        "reason": "溫度測試需要監控溫度響應"
    }
}

# 性能優化建議
PERFORMANCE_GUIDELINES = {
    "data_size_thresholds": {
        "small": 1000,      # < 1K 行，無需篩選
        "medium": 10000,    # 1K-10K 行，建議輕度篩選
        "large": 100000,    # 10K-100K 行，建議中度篩選
        "very_large": 1000000  # > 100K 行，建議重度篩選
    },
    "recommendations": {
        "small": {
            "interval": 0.0,
            "message": "數據量較小，建議保留所有數據點"
        },
        "medium": {
            "interval": 1.0,
            "message": "中等數據量，建議1秒間隔篩選"
        },
        "large": {
            "interval": 10.0,
            "message": "大數據量，建議10秒間隔篩選"
        },
        "very_large": {
            "interval": 60.0,
            "message": "超大數據量，建議1分鐘間隔篩選"
        }
    }
}

def get_recommended_interval(data_size: int, data_type: str = None) -> dict:
    """
    根據數據大小和類型獲取建議的時間間隔
    
    Args:
        data_size: 數據行數
        data_type: 數據類型 (可選)
        
    Returns:
        包含建議間隔和說明的字典
    """
    # 根據數據大小確定基本建議
    if data_size <= PERFORMANCE_GUIDELINES["data_size_thresholds"]["small"]:
        size_category = "small"
    elif data_size <= PERFORMANCE_GUIDELINES["data_size_thresholds"]["medium"]:
        size_category = "medium"
    elif data_size <= PERFORMANCE_GUIDELINES["data_size_thresholds"]["large"]:
        size_category = "large"
    else:
        size_category = "very_large"
    
    base_recommendation = PERFORMANCE_GUIDELINES["recommendations"][size_category]
    
    # 如果指定了數據類型，進行調整
    if data_type and data_type in DATA_TYPE_RECOMMENDATIONS:
        type_config = DATA_TYPE_RECOMMENDATIONS[data_type]
        recommended_interval = type_config["recommended_interval"]
        
        # 如果基於大小的建議間隔太大，使用類型建議的最大值
        if base_recommendation["interval"] > type_config["max_recommended"]:
            final_interval = type_config["max_recommended"]
            message = f"根據數據類型 '{data_type}' 調整: {type_config['reason']}"
        else:
            final_interval = max(base_recommendation["interval"], recommended_interval)
            message = base_recommendation["message"]
    else:
        final_interval = base_recommendation["interval"]
        message = base_recommendation["message"]
    
    return {
        "interval": final_interval,
        "message": message,
        "size_category": size_category,
        "data_size": data_size
    }
