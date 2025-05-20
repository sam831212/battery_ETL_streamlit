"""
Test specifically for execution_time handling in detail data.
"""
import os
import pandas as pd
import pytest
from datetime import datetime

from app.etl.extraction import parse_detail_csv


def test_execution_time_extraction():
    """Test that execution_time is correctly extracted from detail CSV files."""
    # Create a test file
    test_file = "test_detail.csv"
    
    # Create sample test data
    test_data = pd.DataFrame({
        '工步': [1, 1, 1, 2, 2],
        '工步執行時間(秒)': [0, 60, 120, 0, 60],
        '電壓(V)': [3.5, 3.6, 3.7, 3.8, 3.9],
        '電流(A)': [1.0, 1.1, 1.2, 1.3, 1.4],
        'Aux T1': [25.0, 25.1, 25.2, 25.3, 25.4],
        '電量(Ah)': [0.1, 0.2, 0.3, 0.4, 0.5],
        '能量(Wh)': [0.35, 0.72, 1.11, 1.52, 1.95]
    })
    
    try:
        # Save test data to CSV file
        test_data.to_csv(test_file, index=False)
        
        # Parse the test file using our extraction function
        df = parse_detail_csv(test_file)
        
        # Verify results
        assert 'execution_time' in df.columns
        assert 'step_number' in df.columns
        assert 'voltage' in df.columns
        assert 'current' in df.columns
        
        # Check that execution_time is correctly processed
        assert list(df['execution_time']) == [0.0, 60.0, 120.0, 0.0, 60.0]
        
        # Check that values are sorted by step_number and execution_time
        assert list(df['step_number']) == [1, 1, 1, 2, 2]
        assert df.iloc[0]['step_number'] == 1 and df.iloc[0]['execution_time'] == 0.0
        assert df.iloc[1]['step_number'] == 1 and df.iloc[1]['execution_time'] == 60.0
        assert df.iloc[2]['step_number'] == 1 and df.iloc[2]['execution_time'] == 120.0
        assert df.iloc[3]['step_number'] == 2 and df.iloc[3]['execution_time'] == 0.0
        assert df.iloc[4]['step_number'] == 2 and df.iloc[4]['execution_time'] == 60.0
        
    finally:
        # Clean up test file
        if os.path.exists(test_file):
            os.remove(test_file)


if __name__ == "__main__":
    # Run the test directly
    test_execution_time_extraction()
    print("All tests passed!")