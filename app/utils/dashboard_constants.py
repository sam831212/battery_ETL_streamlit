"""
DataFrame column constants for dashboard and DB fetch service
"""

PROJECT_DF_COLUMNS = ['id', 'name', 'description', 'start_date', 'experiment_count']
EXPERIMENT_DF_COLUMNS = ['id', 'name', 'project_id', 'project_name', 'battery_type',
                         'nominal_capacity', 'temperature', 'operator', 'start_date',
                         'step_count']
STEP_DF_COLUMNS = ['id', 'step_name', 'experiment_id', 'experiment_name', 'step_number',
                   'step_type', 'duration', 'voltage_start', 'voltage_end', 'current', 'capacity',
                   'energy', 'temperature', 'c_rate', 'soc_start', 'soc_end', 'pre_test_rest_time']
MEASUREMENT_DF_COLUMNS = ['step_id', 'execution_time', 'voltage', 'current', 'temperature', 'capacity', 'energy']
CELL_DF_COLUMNS = [
    'id', 'name', 'manufacturer', 'chemistry', 'capacity', 'form',
    'nominal_capacity', 'nominal_voltage', 'form_factor', 'serial_number',
    'date_received', 'notes'
]
