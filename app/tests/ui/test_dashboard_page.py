import pytest
from unittest.mock import patch, MagicMock, call
import pandas as pd
import streamlit as st
from datetime import datetime

from app.ui.dashboard_page import (
    render_overview_tab,
    render_capacity_tab,
    render_voltage_tab,
    render_temperature_tab
)
from app.models.database import Experiment, Step, Measurement, Cell, Machine

# Test for render_overview_tab
@patch('app.ui.dashboard_page.get_session')
@patch('streamlit.metric')
@patch('streamlit.plotly_chart')
@patch('streamlit.info')
def test_render_overview_tab_with_data(mock_st_info, mock_st_plotly, mock_st_metric, mock_get_session, mock_db_session):
    """Test render_overview_tab with a selected experiment and available data."""
    # Setup mock session and data
    mock_get_session.return_value.__enter__.return_value = mock_db_session

    mock_experiment = Experiment(id=1, name="Test Exp 1", battery_type="NMC", nominal_capacity=3.0, created_at=datetime.now())
    mock_steps_data = [
        Step(id=1, experiment_id=1, step_type="charge", cycle_number=1, capacity_ah=2.9),
        Step(id=2, experiment_id=1, step_type="discharge", cycle_number=1, capacity_ah=2.8),
        Step(id=3, experiment_id=1, step_type="charge", cycle_number=2, capacity_ah=2.85),
        Step(id=4, experiment_id=1, step_type="discharge", cycle_number=2, capacity_ah=2.75),
        Step(id=5, experiment_id=1, step_type="rest", cycle_number=2), # No capacity
    ]
    mock_measurements_data = [
        Measurement(id=1, experiment_id=1, step_id=1, temperature_c=25.0),
        Measurement(id=2, experiment_id=1, step_id=2, temperature_c=28.5),
        Measurement(id=3, experiment_id=1, step_id=4, temperature_c=30.1),
    ]

    mock_db_session.get.return_value = mock_experiment # For session.get(Experiment, ...)
    
    # Side effect for session.exec based on statement (simplified)
    def exec_side_effect_overview(statement):
        mock_query_result = MagicMock()
        # This is a simplified way to distinguish queries.
        # A more robust way might involve inspecting statement.whereclause more deeply
        # or using a library that helps mock SQLAlchemy query results based on model.
        query_str = str(statement).lower()
        if "from step" in query_str: # Assuming this is the query for steps
            mock_query_result.all.return_value = mock_steps_data
        elif "max(measurement.temperature_c)" in query_str: # Query for max temperature
            max_temp = max(m.temperature_c for m in mock_measurements_data) if mock_measurements_data else None
            mock_query_result.one_or_none.return_value = max_temp
        else:
            mock_query_result.all.return_value = [] # Default for other queries
            mock_query_result.one_or_none.return_value = None
        return mock_query_result

    mock_db_session.exec.side_effect = exec_side_effect_overview
    
    with patch.dict(st.session_state, {"selected_experiment_id": 1}):
        render_overview_tab()

    # Assertions
    # Total Discharge Capacity = 2.8 + 2.75 = 5.55
    # Cycle Count = 2 (cycles 1 and 2 from discharge)
    # Efficiency = (5.55 / (2.9 + 2.85)) * 100 = (5.55 / 5.75) * 100 = 96.5217... ~96.52%
    # Max Temp = 30.1
    
    # Check metric calls. Order might vary, so check individually or collect and compare.
    # Using a dictionary to store actual calls for easier comparison
    actual_metric_calls = {call_args.args[0]: call_args.args[1] for call_args in mock_st_metric.call_args_list}

    assert actual_metric_calls.get("Total Discharge Capacity (Ah)") == "5.55"
    assert actual_metric_calls.get("Cycle Count") == "2"
    # For efficiency, it's float, so check with tolerance or formatted string
    assert actual_metric_calls.get("Overall C/D Efficiency (%)") == "96.52%" 
    assert actual_metric_calls.get("Max Temperature (°C)") == "30.10" 
    
    mock_st_plotly.assert_called_once() # Chart for discharge capacity per cycle
    mock_st_info.assert_not_called() # Should not show "no data" messages

@patch('app.ui.dashboard_page.get_session')
@patch('streamlit.metric')
@patch('streamlit.plotly_chart')
@patch('streamlit.info')
def test_render_overview_tab_no_data(mock_st_info, mock_st_plotly, mock_st_metric, mock_get_session, mock_db_session):
    """Test render_overview_tab when no experiment data is available."""
    mock_get_session.return_value.__enter__.return_value = mock_db_session
    
    mock_experiment = Experiment(id=1, name="Test Exp No Data", battery_type="LFP", nominal_capacity=2.0, created_at=datetime.now())
    mock_db_session.get.return_value = mock_experiment
    
    # Simulate no steps and no measurements
    def exec_side_effect_no_data(statement):
        mock_query_result = MagicMock()
        mock_query_result.all.return_value = [] 
        mock_query_result.one_or_none.return_value = None # For max_temp
        return mock_query_result
    mock_db_session.exec.side_effect = exec_side_effect_no_data

    with patch.dict(st.session_state, {"selected_experiment_id": 1}):
        render_overview_tab()

    actual_metric_calls = {call_args.args[0]: call_args.args[1] for call_args in mock_st_metric.call_args_list}

    assert actual_metric_calls.get("Total Discharge Capacity (Ah)") == "--"
    assert actual_metric_calls.get("Cycle Count") == "0" 
    assert actual_metric_calls.get("Overall C/D Efficiency (%)") == "0.00%"
    assert actual_metric_calls.get("Max Temperature (°C)") == "--"

    mock_st_info.assert_any_call("No discharge capacity data (from 'discharge' steps) available to display for this experiment.")
    mock_st_plotly.assert_not_called() # No chart should be displayed


@patch('app.ui.dashboard_page.get_session')
@patch('streamlit.info')
@patch('streamlit.metric') # Also patch metric to ensure it's not called
@patch('streamlit.plotly_chart') # Also patch plotly_chart
def test_render_overview_tab_no_selected_experiment(mock_st_plotly, mock_st_metric, mock_st_info, mock_get_session, mock_db_session):
    """Test render_overview_tab when no experiment is selected."""
    mock_get_session.return_value.__enter__.return_value = mock_db_session # Though get_session won't be used much here
    
    with patch.dict(st.session_state, {"selected_experiment_id": None}):
        render_overview_tab()
    
    mock_st_info.assert_called_once_with("Please select an experiment from the sidebar or adjust filters to view its overview.")
    mock_st_metric.assert_not_called()
    mock_st_plotly.assert_not_called()

# --- Tests for render_capacity_tab ---

@patch('app.ui.dashboard_page.get_session')
@patch('streamlit.plotly_chart')
@patch('streamlit.info')
@patch('streamlit.caption')
def test_render_capacity_tab_with_data(mock_st_caption, mock_st_info, mock_st_plotly, mock_get_session, mock_db_session):
    """Test render_capacity_tab with discharge data."""
    mock_get_session.return_value.__enter__.return_value = mock_db_session
    
    mock_steps_data = [
        Step(id=1, experiment_id=1, step_type="discharge", cycle_number=1, capacity_ah=2.8),
        Step(id=2, experiment_id=1, step_type="discharge", cycle_number=2, capacity_ah=2.7),
        Step(id=3, experiment_id=1, step_type="charge", cycle_number=1, capacity_ah=3.0), # Should be ignored by main query
        Step(id=4, experiment_id=1, step_type="discharge", cycle_number=3, capacity_ah=2.6),
    ]
    # Simulate the query for discharge steps
    mock_db_session.exec.return_value.all.return_value = [
        (s.cycle_number, s.capacity_ah) for s in mock_steps_data if s.step_type == "discharge"
    ]

    with patch.dict(st.session_state, {"selected_experiment_id": 1}):
        render_capacity_tab()

    # Expect two plotly charts: one for capacity vs cycle, one for retention
    assert mock_st_plotly.call_count == 2
    mock_st_info.assert_not_called()
    mock_st_caption.assert_called_once() # For retention chart

@patch('app.ui.dashboard_page.get_session')
@patch('streamlit.plotly_chart')
@patch('streamlit.info')
@patch('streamlit.caption')
def test_render_capacity_tab_no_discharge_data(mock_st_caption, mock_st_info, mock_st_plotly, mock_get_session, mock_db_session):
    """Test render_capacity_tab with no discharge data."""
    mock_get_session.return_value.__enter__.return_value = mock_db_session
    mock_db_session.exec.return_value.all.return_value = [] # No discharge steps

    with patch.dict(st.session_state, {"selected_experiment_id": 1}):
        render_capacity_tab()

    mock_st_info.assert_any_call("No discharge capacity data available for this experiment (check filters and data).")
    # One empty chart with annotation is shown
    assert mock_st_plotly.call_count == 1 
    mock_st_caption.assert_not_called()


@patch('app.ui.dashboard_page.get_session')
@patch('streamlit.plotly_chart')
@patch('streamlit.info')
@patch('streamlit.caption')
def test_render_capacity_tab_zero_initial_capacity(mock_st_caption, mock_st_info, mock_st_plotly, mock_get_session, mock_db_session):
    """Test render_capacity_tab when initial discharge capacity is zero."""
    mock_get_session.return_value.__enter__.return_value = mock_db_session
    
    mock_steps_data_tuples = [
        (1, 0.0), # Cycle 1, 0 capacity
        (2, 2.7), # Cycle 2
    ]
    mock_db_session.exec.return_value.all.return_value = mock_steps_data_tuples

    with patch.dict(st.session_state, {"selected_experiment_id": 1}):
        render_capacity_tab()

    # Capacity vs Cycle chart should still be called
    # Retention chart should not be called, and an info message shown instead
    assert mock_st_plotly.call_count == 1 
    mock_st_info.assert_any_call("Initial capacity is zero or invalid, cannot calculate capacity retention.")
    mock_st_caption.assert_not_called()


@patch('app.ui.dashboard_page.get_session')
@patch('streamlit.info')
@patch('streamlit.plotly_chart') # Also patch plotly_chart
def test_render_capacity_tab_no_selected_experiment(mock_st_plotly, mock_st_info, mock_get_session, mock_db_session):
    """Test render_capacity_tab when no experiment is selected."""
    with patch.dict(st.session_state, {"selected_experiment_id": None}):
        render_capacity_tab()
    
    mock_st_info.assert_called_once_with("Please select an experiment from the sidebar or adjust filters to view capacity analysis.")
    mock_st_plotly.assert_not_called()

# --- Tests for render_voltage_tab ---

@patch('app.ui.dashboard_page.get_session')
@patch('streamlit.info')
@patch('streamlit.plotly_chart')
def test_render_voltage_tab_no_selected_experiment(mock_st_plotly, mock_st_info, mock_get_session, mock_db_session):
    """Test render_voltage_tab when no experiment is selected."""
    mock_get_session.return_value.__enter__.return_value = mock_db_session
    with patch.dict(st.session_state, {"selected_experiment_id": None, "selected_step_types_filter": ["Charge", "Discharge"]}):
        render_voltage_tab()
    mock_st_info.assert_called_once_with("Please select an experiment from the sidebar or adjust filters to view voltage analysis.")
    mock_st_plotly.assert_not_called()

@patch('app.ui.dashboard_page.get_session')
@patch('streamlit.selectbox')
@patch('streamlit.info')
@patch('streamlit.warning')
@patch('streamlit.plotly_chart')
def test_render_voltage_tab_no_steps_available(mock_st_plotly, mock_st_warning, mock_st_info, mock_st_selectbox, mock_get_session, mock_db_session):
    """Test render_voltage_tab when an experiment is selected but no steps match filters."""
    mock_get_session.return_value.__enter__.return_value = mock_db_session
    mock_db_session.exec.return_value.all.return_value = [] # No steps available

    with patch.dict(st.session_state, {"selected_experiment_id": 1, "selected_step_types_filter": ["Charge"]}):
        render_voltage_tab()
    
    mock_st_info.assert_any_call("No steps matching the selected types (Charge) and cycle criteria found for this experiment.")
    assert mock_st_plotly.call_count == 2 # Two empty charts with annotations
    mock_st_selectbox.assert_not_called() # Selectbox for steps should not appear

@patch('app.ui.dashboard_page.get_session')
@patch('streamlit.selectbox')
@patch('streamlit.warning')
@patch('streamlit.plotly_chart')
@patch('plotly.express.line') # To check if it's called with data
def test_render_voltage_tab_with_data_no_measurements(mock_px_line, mock_st_plotly, mock_st_warning, mock_st_selectbox, mock_get_session, mock_db_session):
    """Test render_voltage_tab with steps but no measurements for the selected step."""
    mock_get_session.return_value.__enter__.return_value = mock_db_session
    
    mock_available_steps = [
        MagicMock(cycle_number=1, step_type="charge", id=10, step_number=1),
        MagicMock(cycle_number=1, step_type="discharge", id=11, step_number=2)
    ]
    # First call to exec().all() for steps
    mock_db_session.exec.return_value.all.side_effect = [mock_available_steps, []] # Second call for measurements returns empty

    # Mock st.selectbox to return the label of the first step
    mock_st_selectbox.return_value = "Step 1 (Cycle 1) - Charge" 
                                     # Label format: f"Step {s.step_number} (Cycle {s.cycle_number if s.cycle_number is not None else 'N/A'}) - {s.step_type.capitalize()}"

    with patch.dict(st.session_state, {"selected_experiment_id": 1, "selected_step_types_filter": ["Charge", "Discharge"]}):
        render_voltage_tab()

    mock_st_selectbox.assert_called_once()
    # Expected warning when no measurements are found for the selected step
    mock_st_warning.assert_called_once_with(f"No measurement data found for the selected step: Step 1 (Cycle 1) - Charge. Check data integrity or filters.")
    assert mock_st_plotly.call_count == 2 # Two empty charts with annotations
    mock_px_line.assert_not_called() # Plotly express line should not be called with actual data

@patch('app.ui.dashboard_page.get_session')
@patch('streamlit.selectbox')
@patch('streamlit.plotly_chart')
@patch('plotly.express.line')
def test_render_voltage_tab_with_data_and_measurements(mock_px_line, mock_st_plotly, mock_st_selectbox, mock_get_session, mock_db_session):
    """Test render_voltage_tab with steps and measurements."""
    mock_get_session.return_value.__enter__.return_value = mock_db_session

    mock_step1 = MagicMock(spec=Step)
    mock_step1.cycle_number = 1
    mock_step1.step_type = "charge"
    mock_step1.id = 10
    mock_step1.step_number = 1
    
    mock_available_steps = [mock_step1]
    
    mock_measurements_data = [
        (1.0, 0.1, 0.0, 10.0), # voltage_v, charge_capacity_ah, discharge_capacity_ah, step_time_s
        (1.1, 0.2, 0.0, 20.0),
    ]
    # exec().all() called for steps, then for measurements
    mock_db_session.exec.return_value.all.side_effect = [mock_available_steps, mock_measurements_data]

    mock_st_selectbox.return_value = "Step 1 (Cycle 1) - Charge"

    with patch.dict(st.session_state, {"selected_experiment_id": 1, "selected_step_types_filter": ["Charge"]}):
        render_voltage_tab()

    mock_st_selectbox.assert_called_once()
    # Two plotly charts should be called (Voltage vs. Capacity, Voltage vs. Time)
    assert mock_st_plotly.call_count == 2
    # px.line should be called twice with a non-empty DataFrame
    assert mock_px_line.call_count == 2
    for mock_call in mock_px_line.call_args_list:
        assert not mock_call.args[0].empty # Check that DataFrame passed to px.line is not empty

# --- Tests for render_temperature_tab ---

@patch('app.ui.dashboard_page.get_session')
@patch('streamlit.info')
@patch('streamlit.plotly_chart')
def test_render_temperature_tab_no_selected_experiment(mock_st_plotly, mock_st_info, mock_get_session, mock_db_session):
    """Test render_temperature_tab when no experiment is selected."""
    mock_get_session.return_value.__enter__.return_value = mock_db_session
    with patch.dict(st.session_state, {"selected_experiment_id": None, "selected_step_types_filter": ["Charge", "Discharge"]}):
        render_temperature_tab()
    mock_st_info.assert_called_once_with("Please select an experiment from the sidebar or adjust filters to view temperature analysis.")
    mock_st_plotly.assert_not_called()

@patch('app.ui.dashboard_page.get_session')
@patch('streamlit.plotly_chart')
@patch('streamlit.info')
@patch('streamlit.selectbox') # To ensure it's not called if no steps for detailed
def test_render_temperature_tab_no_overall_temp_data(mock_st_selectbox, mock_st_info, mock_st_plotly, mock_get_session, mock_db_session):
    """Test render_temperature_tab with no overall temperature data for the experiment."""
    mock_get_session.return_value.__enter__.return_value = mock_db_session
    # First call for overall temp data, second for available steps for detailed profile
    mock_db_session.exec.return_value.all.side_effect = [[], []] 

    with patch.dict(st.session_state, {"selected_experiment_id": 1, "selected_step_types_filter": ["Charge"]}):
        render_temperature_tab()

    mock_st_info.assert_any_call("No overall temperature data available for this experiment (check filters and data).")
    # One plotly chart for the empty overall temp plot with annotation
    assert mock_st_plotly.call_count == 1 
    # Info message that no steps are available for detailed view (since first exec().all() for steps was empty)
    mock_st_info.assert_any_call("No steps available to show detailed temperature profile.")
    mock_st_selectbox.assert_not_called() # No steps, so selectbox for detailed profile shouldn't show

@patch('app.ui.dashboard_page.get_session')
@patch('streamlit.plotly_chart')
@patch('streamlit.info')
@patch('streamlit.selectbox')
@patch('plotly.express.line')
def test_render_temperature_tab_with_overall_data_no_steps_for_detailed(mock_px_line, mock_st_selectbox, mock_st_info, mock_st_plotly, mock_get_session, mock_db_session):
    """Test render_temperature_tab with overall data but no steps for detailed profile."""
    mock_get_session.return_value.__enter__.return_value = mock_db_session
    
    mock_overall_temp_data = [
        (10.0, 25.0), (20.0, 26.0) # experiment_time_s, temperature_c
    ]
    # First call for overall temp, second for available steps (empty list)
    mock_db_session.exec.return_value.all.side_effect = [mock_overall_temp_data, []]

    with patch.dict(st.session_state, {"selected_experiment_id": 1, "selected_step_types_filter": ["Rest"]}): # Filter that might yield no steps
        render_temperature_tab()

    # Plotly chart for overall temperature should be called
    # px.line should be called once for the overall data
    mock_px_line.assert_called_once() 
    assert not mock_px_line.call_args.args[0].empty # DataFrame for overall temp should not be empty
    
    mock_st_info.assert_any_call("No steps matching the selected types (Rest) found for detailed temperature profile.")
    mock_st_selectbox.assert_not_called() # Selectbox for detailed step temp should not appear


@patch('app.ui.dashboard_page.get_session')
@patch('streamlit.selectbox')
@patch('streamlit.plotly_chart')
@patch('streamlit.info')
@patch('plotly.express.line')
def test_render_temperature_tab_detailed_step_no_measurements(mock_px_line, mock_st_info, mock_st_plotly, mock_st_selectbox, mock_get_session, mock_db_session):
    """Test render_temperature_tab when a detailed step is selected but has no temperature measurements."""
    mock_get_session.return_value.__enter__.return_value = mock_db_session

    mock_overall_temp_data = [(10.0, 25.0)]
    mock_available_steps_for_detailed = [MagicMock(id=100, step_type="charge", cycle_number=1, step_number=1)]
    
    # Overall temp, then steps for detailed, then measurements for selected detailed step (empty)
    mock_db_session.exec.return_value.all.side_effect = [mock_overall_temp_data, mock_available_steps_for_detailed, []]
    
    mock_st_selectbox.return_value = "Step 1 (Cycle 1) - Charge" # Mocking selection

    with patch.dict(st.session_state, {"selected_experiment_id": 1, "selected_step_types_filter": ["Charge"]}):
        render_temperature_tab()

    # px.line called once for overall, not for detailed
    mock_px_line.assert_called_once() 
    assert mock_st_plotly.call_count == 2 # Overall chart + one empty chart for detailed step
    mock_st_info.assert_any_call("No temperature data for the selected step: Step 1 (Cycle 1) - Charge. Check data or filters.")

@patch('app.ui.dashboard_page.get_session')
@patch('streamlit.selectbox')
@patch('streamlit.plotly_chart')
@patch('plotly.express.line')
def test_render_temperature_tab_with_all_data(mock_px_line, mock_st_plotly, mock_st_selectbox, mock_get_session, mock_db_session):
    """Test render_temperature_tab with overall data and detailed step data."""
    mock_get_session.return_value.__enter__.return_value = mock_db_session

    mock_overall_temp_data = [(10.0, 25.0), (20.0, 25.5)]
    mock_detailed_step = MagicMock(spec=Step) # Use spec for more realistic MagicMock
    mock_detailed_step.id = 100
    mock_detailed_step.step_type = "charge"
    mock_detailed_step.cycle_number = 1
    mock_detailed_step.step_number = 1
    
    mock_available_steps_for_detailed = [mock_detailed_step]
    mock_measurements_for_detailed_step = [(5.0, 28.0), (10.0, 29.0)] # step_time_s, temperature_c

    # Side effects for multiple exec().all() calls
    mock_db_session.exec.return_value.all.side_effect = [
        mock_overall_temp_data, 
        mock_available_steps_for_detailed, 
        mock_measurements_for_detailed_step
    ]
    
    mock_st_selectbox.return_value = "Step 1 (Cycle 1) - Charge"

    with patch.dict(st.session_state, {"selected_experiment_id": 1, "selected_step_types_filter": ["Charge"]}):
        render_temperature_tab()

    # px.line should be called twice (overall + detailed)
    assert mock_px_line.call_count == 2
    # Check that DataFrames passed to px.line are not empty for both calls
    assert not mock_px_line.call_args_list[0].args[0].empty # Overall
    assert not mock_px_line.call_args_list[1].args[0].empty # Detailed
    
    # Plotly chart should be called twice
    assert mock_st_plotly.call_count == 2

# --- Tests for render_validation_tab ---

@patch('app.ui.dashboard_page.get_session')
@patch('streamlit.info')
@patch('streamlit.error') # For experiment not found
def test_render_validation_tab_no_selected_experiment(mock_st_error, mock_st_info, mock_get_session, mock_db_session):
    """Test render_validation_tab when no experiment is selected."""
    mock_get_session.return_value.__enter__.return_value = mock_db_session
    with patch.dict(st.session_state, {"selected_experiment_id": None}):
        # Need to import render_validation_tab from dashboard_page to test it directly if it's not already
        from app.ui.dashboard_page import render_validation_tab 
        render_validation_tab()
    mock_st_info.assert_called_once_with("Please select an experiment from the sidebar to view validation results.")
    mock_st_error.assert_not_called()


@patch('app.ui.dashboard_page.get_session')
@patch('streamlit.error')
def test_render_validation_tab_experiment_not_found(mock_st_error, mock_get_session, mock_db_session):
    """Test render_validation_tab when the selected experiment is not found in DB."""
    mock_get_session.return_value.__enter__.return_value = mock_db_session
    mock_db_session.get.return_value = None # Simulate experiment not found

    with patch.dict(st.session_state, {"selected_experiment_id": 999}): # Some non-existent ID
        from app.ui.dashboard_page import render_validation_tab
        render_validation_tab()
    mock_st_error.assert_called_once_with("Selected experiment not found.")


@patch('app.ui.dashboard_page.get_session')
@patch('streamlit.warning')
def test_render_validation_tab_no_validation_report(mock_st_warning, mock_get_session, mock_db_session):
    """Test render_validation_tab when experiment exists but has no validation report."""
    mock_get_session.return_value.__enter__.return_value = mock_db_session
    mock_experiment_no_report = Experiment(id=1, name="Test No Report", validation_report=None, created_at=datetime.now())
    mock_db_session.get.return_value = mock_experiment_no_report

    with patch.dict(st.session_state, {"selected_experiment_id": 1}):
        from app.ui.dashboard_page import render_validation_tab
        render_validation_tab()
    mock_st_warning.assert_called_once_with("No validation data available for this experiment.")


@patch('app.ui.dashboard_page.get_session')
@patch('streamlit.write')
@patch('streamlit.success')
@patch('streamlit.warning')
@patch('streamlit.expander') # To check if expanders are created
@patch('streamlit.metric') 
@patch('streamlit.error') # For critical issues in report
@patch('streamlit.json')
def test_render_validation_tab_with_valid_report(mock_st_json, mock_st_error_report, mock_st_metric, mock_st_expander, mock_st_warning_report, mock_st_success, mock_st_write, mock_get_session, mock_db_session):
    """Test render_validation_tab with a valid validation report."""
    mock_get_session.return_value.__enter__.return_value = mock_db_session
    
    mock_report_data = {
        "step_validation": {
            "summary": {"total_issues": 1, "critical_issues": 1, "warning_issues": 0},
            "issues_by_severity": {"critical": [{"validation": "Crit Rule", "issue": "Crit Issue"}], "warning": [], "info": []}
        },
        "detail_validation": {
            "summary": {"total_issues": 1, "critical_issues": 0, "warning_issues": 1},
            "issues_by_severity": {"critical": [], "warning": [{"validation": "Warn Rule", "issue": "Warn Issue"}], "info": []}
        },
        "timestamp": "2023-01-01T12:00:00"
    }
    mock_experiment_with_report = Experiment(
        id=1, name="Test Valid Report", validation_report=mock_report_data, validation_status=False, # False because there are issues
        battery_type="NCA", nominal_capacity=3.2, created_at=datetime.now(),
        cell_id=None, machine_id=None # Keep simple for this test
    )
    mock_db_session.get.return_value = mock_experiment_with_report

    # Mock the __enter__ method for the expander context manager
    mock_expander_cm = MagicMock()
    mock_st_expander.return_value = mock_expander_cm # This is the context manager object
    mock_expander_cm.__enter__.return_value = None # What `with ... as ...:` would yield, not strictly needed if not used
    mock_expander_cm.__exit__.return_value = None


    with patch.dict(st.session_state, {"selected_experiment_id": 1}):
        from app.ui.dashboard_page import render_validation_tab
        render_validation_tab()

    # Check experiment details are written
    mock_st_write.assert_any_call("#### Experiment: Test Valid Report")
    mock_st_write.assert_any_call("Battery Type: NCA")
    
    # Check validation status (False means issues found)
    mock_st_warning_report.assert_any_call("Validation found potential issues with the data. ⚠️")
    mock_st_success.assert_not_called() # Should not be called if status is False

    # Check if expanders are created
    assert mock_st_expander.call_count == 3 # Step, Measurement, Metadata

    # Check metrics for step validation
    # These calls are to st.metric(label, value)
    # We need to check based on the label
    step_metrics_calls = [call_args for call_args in mock_st_metric.call_args_list if call_args.args[0] in ["Total Issues", "Critical Issues", "Warning Issues"]]

    # This is a bit verbose, ideally we'd check specific expander contexts
    assert any(c.args == ("Total Issues", 1) for c in step_metrics_calls)
    assert any(c.args == ("Critical Issues", 1) for c in step_metrics_calls)
    assert any(c.args == ("Warning Issues", 0) for c in step_metrics_calls)
    
    # Check if critical error from report is displayed
    mock_st_error_report.assert_any_call("**Crit Rule**: Crit Issue")
    # Check if warning from report is displayed (this would be st.warning, already patched as mock_st_warning_report)
    mock_st_warning_report.assert_any_call("**Warn Rule**: Warn Issue")

    # Check if JSON report is displayed
    mock_st_json.assert_called_once_with(mock_report_data)


# TODO: Add more tests for edge cases and filter interactions if possible
