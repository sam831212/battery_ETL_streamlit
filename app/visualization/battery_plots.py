"""
Battery performance visualization functions

This module provides functions for creating battery performance visualization plots
such as capacity vs voltage, voltage vs time, and other key metrics.
"""
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import Dict, List, Tuple, Any, Union, Optional

from .utils import (apply_consistent_styling, get_color_by_step_type,
                    add_anomaly_markers, plot_data_by_step_type,
                    preprocess_for_visualization, format_time_axis,
                    handle_plotting_error, cache_plot, PLOT_COLORS)


@handle_plotting_error
@cache_plot(ttl=300)
def plot_capacity_vs_voltage(df: pd.DataFrame,
                             voltage_col: str = 'voltage',
                             capacity_col: str = 'capacity',
                             step_type_col: str = 'step_type',
                             step_number_col: str = 'step_number',
                             highlight_anomalies: bool = True,
                             title: str = 'Capacity vs Voltage') -> go.Figure:
    """
    Create capacity vs voltage plot with discharge/charge curves.
    
    Args:
        df: DataFrame containing the data
        voltage_col: Name of the voltage column
        capacity_col: Name of the capacity column
        step_type_col: Name of the step type column
        step_number_col: Name of the step number column
        highlight_anomalies: Whether to highlight anomalies
        title: Plot title
        
    Returns:
        Plotly figure object
    """
    # Validate data
    if voltage_col not in df.columns or capacity_col not in df.columns:
        fig = go.Figure()
        fig.update_layout(
            title=
            f"Cannot create plot: Missing required columns ({voltage_col}, {capacity_col})"
        )
        return fig

    # Preprocess data for visualization
    processed_df = preprocess_for_visualization(df)

    # Create figure
    fig = go.Figure()

    # Add traces by step type and step number
    if step_type_col in processed_df.columns and step_number_col in processed_df.columns:
        # Only include charge and discharge steps
        step_types_to_plot = ['charge', 'discharge']
        filtered_df = processed_df[processed_df[step_type_col].isin(
            step_types_to_plot)]

        if filtered_df.empty:
            # No charge/discharge data, just plot all data
            fig.add_trace(
                go.Scatter(x=processed_df[voltage_col],
                           y=processed_df[capacity_col],
                           mode='lines+markers',
                           name='All data',
                           line=dict(color=PLOT_COLORS['default']),
                           marker=dict(color=PLOT_COLORS['default'], size=5)))
        else:
            # Group by step type and step number
            for step_type in step_types_to_plot:
                step_type_df = filtered_df[filtered_df[step_type_col] ==
                                           step_type]

                if step_type_df.empty:
                    continue

                for step_number, step_df in step_type_df.groupby(
                        step_number_col):
                    # Sort by voltage to get clean curves
                    if step_type == 'discharge':
                        step_df = step_df.sort_values(voltage_col,
                                                      ascending=False)
                    else:
                        step_df = step_df.sort_values(voltage_col,
                                                      ascending=True)

                    # Get color for step type
                    color = get_color_by_step_type(step_type)

                    # Add trace for this step
                    fig.add_trace(
                        go.Scatter(
                            x=step_df[voltage_col],
                            y=step_df[capacity_col],
                            mode='lines+markers',
                            name=f"{step_type.capitalize()} {step_number}",
                            line=dict(color=color),
                            marker=dict(color=color, size=5),
                            hovertemplate=(
                                f"Voltage: %{{x}} V<br>"
                                f"Capacity: %{{y}} Ah<br>"
                                f"Step: {step_number}<br>"
                                f"Type: {step_type}<extra></extra>")))
    else:
        # Just create a simple scatter plot
        fig.add_trace(
            go.Scatter(x=processed_df[voltage_col],
                       y=processed_df[capacity_col],
                       mode='lines+markers',
                       name='Capacity vs. Voltage',
                       line=dict(color=PLOT_COLORS['default']),
                       marker=dict(color=PLOT_COLORS['default'], size=5)))

    # Highlight anomalies if requested
    if highlight_anomalies:
        # Check for voltage anomalies
        voltage_anomaly_col = f'{voltage_col}_is_anomaly'
        if voltage_anomaly_col in processed_df.columns and processed_df[
                voltage_anomaly_col].any():
            fig = add_anomaly_markers(fig,
                                      processed_df,
                                      voltage_col,
                                      capacity_col,
                                      anomaly_col=voltage_anomaly_col,
                                      name='Voltage Anomalies')

        # Check for capacity anomalies
        capacity_anomaly_col = f'{capacity_col}_is_anomaly'
        if capacity_anomaly_col in processed_df.columns and processed_df[
                capacity_anomaly_col].any():
            fig = add_anomaly_markers(fig,
                                      processed_df,
                                      voltage_col,
                                      capacity_col,
                                      anomaly_col=capacity_anomaly_col,
                                      name='Capacity Anomalies')

    # Apply consistent styling
    fig = apply_consistent_styling(fig,
                                   title=title,
                                   x_title='Voltage (V)',
                                   y_title='Capacity (Ah)')

    return fig


def _get_execution_time_col(df: pd.DataFrame) -> str:
    """
    自動選擇 detail data 的時間欄位，優先 'execution_time_alt'
    """
    if 'execution_time_alt' in df.columns:
        return 'execution_time_alt'
    else:
        return 'timestamp'  # fallback


@handle_plotting_error
@cache_plot(ttl=300)
def plot_voltage_vs_time(df: pd.DataFrame,
                         voltage_col: str = 'voltage',
                         time_col: str = 'timestamp',
                         step_type_col: str = 'step_type',
                         step_number_col: str = 'step_number',
                         highlight_anomalies: bool = True,
                         title: str = 'Voltage vs Time') -> go.Figure:
    """
    Create voltage vs time plot showing cycling behavior.
    
    Args:
        df: DataFrame containing the data
        voltage_col: Name of the voltage column
        time_col: Name of the time column
        step_type_col: Name of the step type column
        step_number_col: Name of the step number column
        highlight_anomalies: Whether to highlight anomalies
        title: Plot title
        
    Returns:
        Plotly figure object
    """
    # 自動選擇時間欄位
    time_col = _get_execution_time_col(df) if time_col == 'timestamp' else time_col

    # Validate data
    if voltage_col not in df.columns or time_col not in df.columns:
        fig = go.Figure()
        fig.update_layout(
            title=
            f"Cannot create plot: Missing required columns ({voltage_col}, {time_col})"
        )
        return fig

    # Preprocess data for visualization
    processed_df = preprocess_for_visualization(df)

    # Ensure the data is sorted by time
    processed_df = processed_df.sort_values(time_col)

    # Create initial plot by step type
    fig = plot_data_by_step_type(processed_df,
                                 x_col=time_col,
                                 y_col=voltage_col,
                                 title=title,
                                 x_title='Time',
                                 y_title='Voltage (V)',
                                 step_type_col=step_type_col,
                                 highlight_anomalies=highlight_anomalies)

    # Format time axis for better readability
    fig = format_time_axis(fig, time_col=time_col)

    # Add step number annotations if available
    if step_number_col in processed_df.columns and step_type_col in processed_df.columns:
        # Get step transitions
        steps = processed_df[[time_col, step_number_col,
                              step_type_col]].drop_duplicates()
        steps = steps.sort_values(time_col)

        # Add step transition markers (vertical lines)
        for i, (_, step) in enumerate(steps.iterrows()):
            if i == 0:
                continue  # Skip first step transition

            step_time = step[time_col]
            step_number = step[step_number_col]
            step_type = step[step_type_col]

            # Add vertical line for step transition
            fig.add_shape(
                type="line",
                x0=step_time,
                y0=0,
                x1=step_time,
                y1=1,
                yref="paper",
                line=dict(
                    color="rgba(0, 0, 0, 0.3)",
                    width=1,
                    dash="dot",
                ),
            )

            # Add annotation for step number
            fig.add_annotation(x=step_time,
                               y=1.05,
                               yref="paper",
                               text=f"Step {step_number}",
                               showarrow=False,
                               font=dict(size=10),
                               bgcolor="rgba(255, 255, 255, 0.8)",
                               bordercolor="rgba(0, 0, 0, 0.2)",
                               borderwidth=1)

    return fig


@handle_plotting_error
@cache_plot(ttl=300)
def plot_current_vs_time(df: pd.DataFrame,
                         current_col: str = 'current',
                         time_col: str = 'timestamp',
                         step_type_col: str = 'step_type',
                         step_number_col: str = 'step_number',
                         highlight_anomalies: bool = True,
                         title: str = 'Current vs Time') -> go.Figure:
    """
    Create current vs time plot showing charge/discharge current.
    
    Args:
        df: DataFrame containing the data
        current_col: Name of the current column
        time_col: Name of the time column
        step_type_col: Name of the step type column
        step_number_col: Name of the step number column
        highlight_anomalies: Whether to highlight anomalies
        title: Plot title
        
    Returns:
        Plotly figure object
    """
    # 自動選擇時間欄位
    time_col = _get_execution_time_col(df) if time_col == 'timestamp' else time_col

    # Validate data
    if current_col not in df.columns or time_col not in df.columns:
        fig = go.Figure()
        fig.update_layout(
            title=
            f"Cannot create plot: Missing required columns ({current_col}, {time_col})"
        )
        return fig

    # Preprocess data for visualization
    processed_df = preprocess_for_visualization(df)

    # Ensure the data is sorted by time
    processed_df = processed_df.sort_values(time_col)

    # Create initial plot by step type
    fig = plot_data_by_step_type(processed_df,
                                 x_col=time_col,
                                 y_col=current_col,
                                 title=title,
                                 x_title='Time',
                                 y_title='Current (A)',
                                 step_type_col=step_type_col,
                                 highlight_anomalies=highlight_anomalies)

    # Add a horizontal line at zero current
    fig.add_shape(
        type="line",
        x0=processed_df[time_col].min(),
        y0=0,
        x1=processed_df[time_col].max(),
        y1=0,
        line=dict(
            color="rgba(0, 0, 0, 0.5)",
            width=1.5,
        ),
    )

    # Format time axis for better readability
    fig = format_time_axis(fig, time_col=time_col)

    return fig


@handle_plotting_error
@cache_plot(ttl=300)
def plot_temperature_vs_time(df: pd.DataFrame,
                           temperature_col: str = 'temperature',
                           time_col: str = 'timestamp',
                           step_type_col: str = 'step_type',
                           step_number_col: str = 'step_number',
                           highlight_anomalies: bool = True,
                           title: str = 'Temperature vs Time') -> go.Figure:
    """
    Create temperature vs time plot.
    
    Args:
        df: DataFrame containing the data
        temperature_col: Name of the temperature column
        time_col: Name of the time column
        step_type_col: Name of the step type column
        step_number_col: Name of the step number column
        highlight_anomalies: Whether to highlight anomalies
        title: Plot title
        
    Returns:
        Plotly figure object
    """
    # 自動選擇時間欄位
    time_col = _get_execution_time_col(df) if time_col == 'timestamp' else time_col

    # Validate data
    if temperature_col not in df.columns or time_col not in df.columns:
        fig = go.Figure()
        fig.update_layout(
            title=
            f"Cannot create plot: Missing required columns ({temperature_col}, {time_col})"
        )
        return fig

    # Preprocess data for visualization
    processed_df = preprocess_for_visualization(df)
    
    # Create figure
    fig = go.Figure()
    
    # Plot data by step type
    # If step_type column exists, plot data by step type
    if step_type_col in processed_df.columns:
        for step_type in processed_df[step_type_col].unique():
            step_df = processed_df[processed_df[step_type_col] == step_type]
            
            # Skip if step dataframe is empty
            if len(step_df) == 0:
                continue
                
            # Get color for step type
            color = get_color_by_step_type(step_type)
            
            # Add trace for this step type
            fig.add_trace(go.Scatter(
                x=step_df[time_col],
                y=step_df[temperature_col],
                mode='lines+markers',
                name=f"{step_type.capitalize()}",
                line=dict(color=color),
                marker=dict(size=5, color=color),
                hovertemplate=(f"Time: %{{x}}<br>"
                               f"Temperature: %{{y}} °C<br>"
                               f"Step Type: {step_type}<extra></extra>")
            ))
    else:
        # Add single trace if no step type information
        fig.add_trace(go.Scatter(
            x=processed_df[time_col],
            y=processed_df[temperature_col],
            mode='lines+markers',
            name='Temperature',
            marker=dict(size=5),
            hovertemplate=(f"Time: %{{x}}<br>"
                          f"Temperature: %{{y}} °C<extra></extra>")
        ))
    
    
    # Add anomaly markers if requested
    if highlight_anomalies and temperature_col in df.columns:
        # Detect temperature anomalies
        temp_outliers = df[df[temperature_col].abs() > df[temperature_col].abs().quantile(0.95)]
        if not temp_outliers.empty:
            # Add markers directly
            fig.add_trace(go.Scatter(
                x=temp_outliers[time_col],
                y=temp_outliers[temperature_col],
                mode='markers',
                name='Temperature Anomalies',
                marker=dict(
                    symbol='circle',
                    size=10,
                    color='red',
                    line=dict(width=2, color='darkred')
                ),
                hovertemplate='Time: %{x}<br>Temperature: %{y}°C<br>Anomaly<extra></extra>'
            ))
    
    # Format time axis for better readability
    fig = format_time_axis(fig, time_col=time_col)
    
    # Update layout
    fig.update_layout(
        title=title,
        xaxis_title='Time',
        yaxis_title='Temperature (°C)',
        legend_title='Step Type',
        hovermode='closest'
    )
    
    # Apply consistent styling
    fig = apply_consistent_styling(fig)
    
    return fig


def plot_combined_voltage_current(
        df: pd.DataFrame,
        voltage_col: str = 'voltage',
        current_col: str = 'current',
        temperature_col: str = 'temperature',
        time_col: str = 'timestamp',
        step_type_col: str = 'step_type',
        step_number_col: str = 'step_number',
        include_temperature: bool = True,
        highlight_anomalies: bool = True,
        title: str = 'Voltage, Current, and Temperature vs Time') -> go.Figure:
    """
    Create combined voltage, current, and temperature plot with multiple y-axes.
    
    Args:
        df: DataFrame containing the data
        voltage_col: Name of the voltage column
        current_col: Name of the current column
        temperature_col: Name of the temperature column
        time_col: Name of the time column
        step_type_col: Name of the step type column
        include_temperature: Whether to include temperature in the plot
        highlight_anomalies: Whether to highlight anomalies
        title: Plot title
        
    Returns:
        Plotly figure object
    """
    # 自動選擇時間欄位
    time_col = _get_execution_time_col(df) if time_col == 'timestamp' else time_col

    # Validate data
    if voltage_col not in df.columns or current_col not in df.columns or time_col not in df.columns:
        fig = go.Figure()
        fig.update_layout(
            title=
            f"Cannot create plot: Missing required columns ({voltage_col}, {current_col}, {time_col})"
        )
        return fig

    # Preprocess data for visualization
    processed_df = preprocess_for_visualization(df)

    # Ensure the data is sorted by time
    processed_df = processed_df.sort_values(time_col)

    # Create figure with secondary y-axis
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Add voltage trace on primary y-axis
    if step_type_col in processed_df.columns:
        # Add traces by step type
        for step_type in processed_df[step_type_col].unique():
            step_df = processed_df[processed_df[step_type_col] == step_type]

            # Skip if step dataframe is empty
            if step_df.empty:
                continue

            # Get color for step type
            color = get_color_by_step_type(step_type)

            # Add voltage trace for this step type
            fig.add_trace(go.Scatter(
                x=step_df[time_col],
                y=step_df[voltage_col],
                mode='lines',
                name=f"{step_type.capitalize()} - Voltage",
                line=dict(color=color),
                hovertemplate=(f"Time: %{{x}}<br>"
                               f"Voltage: %{{y}} V<br>"
                               f"Step Type: {step_type}<extra></extra>")),
                          secondary_y=False)
    else:
        # Add single voltage trace
        fig.add_trace(go.Scatter(
            x=processed_df[time_col],
            y=processed_df[voltage_col],
            mode='lines',
            name='Voltage',
            line=dict(color=PLOT_COLORS['default']),
            hovertemplate=(f"Time: %{{x}}<br>"
                           f"Voltage: %{{y}} V<extra></extra>")),
                      secondary_y=False)

    # Add current trace on secondary y-axis with dashed line style
    fig.add_trace(go.Scatter(
        x=processed_df[time_col],
        y=processed_df[current_col],
        mode='lines',
        name='Current',
        line=dict(color='rgba(150, 50, 50, 0.7)', dash='dash'),
        hovertemplate=(f"Time: %{{x}}<br>"
                       f"Current: %{{y}} A<extra></extra>")),
                  secondary_y=True)
    
    # Add temperature trace if requested and available
    if include_temperature and temperature_col in processed_df.columns:
        # Create a copy of the figure for combining later
        temp_fig = go.Figure()
        
        # Add temperature trace with dotted line and different color
        temp_fig.add_trace(go.Scatter(
            x=processed_df[time_col],
            y=processed_df[temperature_col],
            mode='lines',
            name='Temperature',
            line=dict(color='rgba(50, 150, 50, 0.7)', dash='dot', width=2),
            hovertemplate=(f"Time: %{{x}}<br>"
                          f"Temperature: %{{y}} °C<extra></extra>")
        ))
        
        # Add the temperature trace to the main figure
        for trace in temp_fig.data:
            fig.add_trace(trace, secondary_y=True)

    # Set titles
    fig.update_layout(title=title)
    fig.update_xaxes(title_text='Time')
    fig.update_yaxes(title_text='Voltage (V)', secondary_y=False)
    fig.update_yaxes(title_text='Current (A) / Temperature (°C)', secondary_y=True)

    # Format time axis for better readability
    fig = format_time_axis(fig, time_col=time_col)

    # Apply consistent styling with some modifications for dual y-axis
    fig.update_layout(legend=dict(orientation="h",
                                  yanchor="bottom",
                                  y=1.02,
                                  xanchor="right",
                                  x=1,
                                  font=dict(size=10),
                                  bgcolor='rgba(255, 255, 255, 0.8)',
                                  bordercolor='rgba(0, 0, 0, 0.2)',
                                  borderwidth=1),
                      showlegend=True,
                      plot_bgcolor='white',
                      margin=dict(l=10, r=10, t=50, b=10),
                      hovermode='closest')

    # Style axes
    fig.update_xaxes(showgrid=True,
                     gridwidth=1,
                     gridcolor='rgba(0, 0, 0, 0.1)',
                     zeroline=True,
                     zerolinewidth=1.5,
                     zerolinecolor='rgba(0, 0, 0, 0.3)')

    # Style primary y-axis (voltage)
    fig.update_yaxes(showgrid=True,
                     gridwidth=1,
                     gridcolor='rgba(0, 0, 0, 0.1)',
                     zeroline=True,
                     zerolinewidth=1.5,
                     zerolinecolor='rgba(0, 0, 0, 0.3)',
                     secondary_y=False)

    # Style secondary y-axis (current)
    fig.update_yaxes(showgrid=False,
                     zeroline=True,
                     zerolinewidth=1.5,
                     zerolinecolor='rgba(0, 0, 0, 0.3)',
                     secondary_y=True)

    return fig
