#!/usr/bin/env python3
"""
Test script to verify dashboard selection functionality
Run this to check if the AgGrid selection fixes are working
"""

import pandas as pd
import sys
import os

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

# Mock streamlit to avoid import errors
class MockStreamlit:
    def __init__(self):
        self.session_state = {}
    
    def warning(self, msg):
        print(f"ST_WARNING: {msg}")
    
    def dataframe(self, df, **kwargs):
        print(f"ST_DATAFRAME: {df.shape} rows x {df.columns.tolist()}")
    
    def multiselect(self, label, options, **kwargs):
        print(f"ST_MULTISELECT: {label} with {len(options)} options")
        return options[:1] if options else []  # Select first option for testing

sys.modules['streamlit'] = MockStreamlit()

# Import our functions
from app.ui.dashboard_page import extract_selected_ids, create_interactive_table

def test_extract_selected_ids():
    """Test the extract_selected_ids function with various input formats"""
    print("=== Testing extract_selected_ids ===")
    
    # Test case 1: List of dicts (expected format)
    test_data_1 = [
        {'id': 1, 'name': 'Project A'},
        {'id': 2, 'name': 'Project B'}
    ]
    result_1 = extract_selected_ids(test_data_1, "Test1")
    print(f"Test 1 - List of dicts: {result_1}")
    assert result_1 == [1, 2], f"Expected [1, 2], got {result_1}"
    
    # Test case 2: List of lists (potential AgGrid format)
    test_data_2 = [
        [1, 'Project A', 'Description A'],
        [2, 'Project B', 'Description B']
    ]
    result_2 = extract_selected_ids(test_data_2, "Test2")
    print(f"Test 2 - List of lists: {result_2}")
    assert result_2 == [1, 2], f"Expected [1, 2], got {result_2}"
    
    # Test case 3: List of integers (row indices)
    test_data_3 = [0, 1]
    result_3 = extract_selected_ids(test_data_3, "Test3")
    print(f"Test 3 - List of integers: {result_3}")
    assert result_3 == [0, 1], f"Expected [0, 1], got {result_3}"
    
    # Test case 4: List of string numbers
    test_data_4 = ['1', '2', '3']
    result_4 = extract_selected_ids(test_data_4, "Test4")
    print(f"Test 4 - List of string numbers: {result_4}")
    assert result_4 == [1, 2, 3], f"Expected [1, 2, 3], got {result_4}"
    
    # Test case 5: Mixed invalid data
    test_data_5 = [
        {'id': 1, 'name': 'Valid'},
        'invalid_string',
        None,
        {'no_id_key': 'invalid'}
    ]
    result_5 = extract_selected_ids(test_data_5, "Test5")
    print(f"Test 5 - Mixed data: {result_5}")
    assert result_5 == [1], f"Expected [1], got {result_5}"
    
    print("✅ All extract_selected_ids tests passed!")

def test_create_interactive_table():
    """Test the create_interactive_table fallback functionality"""
    print("\n=== Testing create_interactive_table (fallback mode) ===")
    
    # Create test DataFrame
    test_df = pd.DataFrame({
        'id': [1, 2, 3],
        'name': ['Project A', 'Project B', 'Project C'],
        'description': ['Desc A', 'Desc B', 'Desc C']
    })
    
    # Test with st_aggrid not available (will use fallback)
    import app.ui.dashboard_page
    original_aggrid = app.ui.dashboard_page.AGGRID_AVAILABLE
    app.ui.dashboard_page.AGGRID_AVAILABLE = False
    
    try:
        result = create_interactive_table(test_df, "TestTable")
        print(f"Fallback mode result: {result}")
        assert 'selected_rows' in result, "Result should contain 'selected_rows' key"
        print("✅ Fallback mode test passed!")
    finally:
        app.ui.dashboard_page.AGGRID_AVAILABLE = original_aggrid

def main():
    """Run all tests"""
    print("🧪 Starting Dashboard Debug Tests\n")
    
    try:
        test_extract_selected_ids()
        test_create_interactive_table()
        print("\n🎉 All tests passed successfully!")
        print("\nThe dashboard selection fixes should now work correctly.")
        print("Key improvements made:")
        print("- Added DataFrame.reset_index(drop=True) to ensure clean indices")
        print("- Enhanced debug logging for AgGrid responses")
        print("- Robust extract_selected_ids function to handle various formats")
        print("- Fallback data return mode handling")
        print("- Better error handling for malformed selection data")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
