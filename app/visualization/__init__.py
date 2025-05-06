"""
Plotting functions for visualizing battery test data
"""
from .utils import (
    apply_consistent_styling,
    get_color_by_step_type,
    add_anomaly_markers,
    plot_data_by_step_type,
    preprocess_for_visualization,
    format_time_axis,
    handle_plotting_error,
    cache_plot,
    PLOT_COLORS
)

from .battery_plots import (
    plot_capacity_vs_voltage,
    plot_voltage_vs_time,
    plot_current_vs_time,
    plot_combined_voltage_current
)

__all__ = [
    # Utility functions
    'apply_consistent_styling',
    'get_color_by_step_type',
    'add_anomaly_markers',
    'plot_data_by_step_type',
    'preprocess_for_visualization',
    'format_time_axis',
    'handle_plotting_error',
    'cache_plot',
    'PLOT_COLORS',
    
    # Battery plot functions
    'plot_capacity_vs_voltage',
    'plot_voltage_vs_time',
    'plot_current_vs_time',
    'plot_combined_voltage_current'
]
