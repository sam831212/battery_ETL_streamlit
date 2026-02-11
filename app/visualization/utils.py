"""
Utility functions for visualization of battery test data

This module provides common plotting utilities and helper functions
for consistent styling across different visualizations.
"""
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import Dict, List, Tuple, Any, Union, Optional, Callable
import functools
import time


# Define color schemes for different data types
PLOT_COLORS = {
    'charge': '#2E86C1',    # Blue
    'discharge': '#E74C3C',  # Red
    'rest': '#58D68D',      # Green
    'anomaly': '#F39C12',   # Orange
    'reference': '#9B59B6',  # Purple
    'default': '#3498DB'    # Default blue
}


def apply_consistent_styling(fig: go.Figure, title: str = None, 
                            x_title: str = None, y_title: str = None,
                            show_legend: bool = True) -> go.Figure:
    """
    Apply consistent styling to plotly figures.
    
    Args:
        fig: Plotly figure to style
        title: Plot title
        x_title: X-axis title
        y_title: Y-axis title
        show_legend: Whether to show the legend
        
    Returns:
        Styled Plotly figure
    """
    # Set titles if provided
    if title:
        fig.update_layout(title=title)
    if x_title:
        fig.update_layout(xaxis_title=x_title)
    if y_title:
        fig.update_layout(yaxis_title=y_title)
    
    # Apply consistent styling
    fig.update_layout(
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=10),
            bgcolor='rgba(255, 255, 255, 0.8)',
            bordercolor='rgba(0, 0, 0, 0.2)',
            borderwidth=1
        ),
        showlegend=show_legend,
        plot_bgcolor='white',
        margin=dict(l=10, r=10, t=50, b=10),
        hovermode='closest'
    )
    
    # Style axes
    fig.update_xaxes(
        showgrid=True,
        gridwidth=1,
        gridcolor='rgba(0, 0, 0, 0.1)',
        zeroline=True,
        zerolinewidth=1.5,
        zerolinecolor='rgba(0, 0, 0, 0.3)'
    )
    
    fig.update_yaxes(
        showgrid=True,
        gridwidth=1,
        gridcolor='rgba(0, 0, 0, 0.1)',
        zeroline=True,
        zerolinewidth=1.5,
        zerolinecolor='rgba(0, 0, 0, 0.3)'
    )
    
    return fig


def get_color_by_step_type(step_type: str) -> str:
    """
    Get color for a specific step type.
    
    Args:
        step_type: Step type (charge, discharge, rest)
        
    Returns:
        Color hex code
    """
    step_type = step_type.lower() if isinstance(step_type, str) else 'default'
    return PLOT_COLORS.get(step_type, PLOT_COLORS['default'])


def add_anomaly_markers(fig: go.Figure, df: pd.DataFrame, 
                       x_col: str, y_col: str, 
                       anomaly_col: str = 'is_anomaly',
                       name: str = 'Anomalies') -> go.Figure:
    """
    Add markers for anomalies to a plotly figure.
    
    Args:
        fig: Plotly figure to add markers to
        df: DataFrame containing data with anomaly flags
        x_col: Column to use for x-axis
        y_col: Column to use for y-axis
        anomaly_col: Column containing anomaly flags
        name: Name for the anomaly trace in the legend
        
    Returns:
        Plotly figure with anomaly markers added
    """
    if anomaly_col not in df.columns:
        # Check for column with _is_anomaly suffix
        full_anomaly_col = f'{y_col}_is_anomaly'
        if full_anomaly_col in df.columns:
            anomaly_col = full_anomaly_col
        else:
            return fig
    
    # Filter for anomaly points
    anomaly_df = df[df[anomaly_col] == True].copy()
    
    if not anomaly_df.empty:
        # Add anomaly markers
        fig.add_trace(
            go.Scatter(
                x=anomaly_df[x_col],
                y=anomaly_df[y_col],
                mode='markers',
                marker=dict(
                    color=PLOT_COLORS['anomaly'],
                    symbol='circle-open',
                    size=10,
                    line=dict(width=2)
                ),
                name=name,
                hovertemplate=(
                    f"{x_col}: %{{x}}<br>"
                    f"{y_col}: %{{y}}<br>"
                    "Anomaly: Yes<extra></extra>"
                )
            )
        )
    
    return fig


def plot_data_by_step_type(df: pd.DataFrame, 
                          x_col: str, y_col: str, 
                          title: str = None,
                          x_title: str = None, 
                          y_title: str = None,
                          step_type_col: str = 'step_type'):
    """
    Create a plot with data colored by step type.
    
    Args:
        df: DataFrame containing the data
        x_col: Column to use for x-axis
        y_col: Column to use for y-axis
        title: Plot title
        x_title: X-axis title
        y_title: Y-axis title
        step_type_col: Column containing step types
        
    Returns:
        Plotly figure
    """
    if x_col not in df.columns or y_col not in df.columns:
        # Return empty figure if required columns are missing
        fig = go.Figure()
        fig.update_layout(
            title=f"Cannot create plot: Missing required columns ({x_col}, {y_col})"
        )
        return fig
    
    # Create figure
    fig = go.Figure()
    
    # Add traces by step type if available
    if step_type_col in df.columns:
        for step_type in df[step_type_col].unique():
            step_df = df[df[step_type_col] == step_type]
            
            # Skip if filtered dataframe is empty
            if step_df.empty:
                continue
            # Get color for step type
            color = get_color_by_step_type(step_type)
            
            # Add scatter trace for this step type
            fig.add_trace(
                go.Scatter(
                    x=step_df[x_col],
                    y=step_df[y_col],
                    mode='lines+markers',
                    name=step_type,
                    line=dict(color=color),
                    marker=dict(color=color, size=5),
                    hovertemplate=(
                        f"{x_col}: %{{x}}<br>"
                        f"{y_col}: %{{y}}<br>"
                        f"Step Type: {step_type}<extra></extra>"
                    )
                )
            )
    else:
        # Add all data as one trace if no step type column
        fig.add_trace(
            go.Scatter(
                x=df[x_col],
                y=df[y_col],
                mode='lines+markers',
                name=y_col,
                line=dict(color=PLOT_COLORS['default']),
                marker=dict(color=PLOT_COLORS['default'], size=5),
                hovertemplate=(
                    f"{x_col}: %{{x}}<br>"
                    f"{y_col}: %{{y}}<extra></extra>"
                )
            )
        )
    # Set titles if provided
    if title:
        fig.update_layout(title=title)
    if x_title:
        fig.update_xaxes(title_text=x_title)
    if y_title:
        fig.update_yaxes(title_text=y_title)
    return fig



def cache_plot(ttl: int = 300):
    """
    Decorator for caching plot results.
    
    Args:
        ttl: Time to live for cached results in seconds (default: 300 seconds / 5 minutes)
    
    Returns:
        Decorated function with caching
    """
    cache = {}
    
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Create a cache key from function arguments
            key = str(args) + str(sorted(kwargs.items()))
            
            # Check if result is in cache and not expired
            if key in cache:
                result, timestamp = cache[key]
                if time.time() - timestamp < ttl:
                    return result
            
            # Call function and cache result
            result = func(*args, **kwargs)
            cache[key] = (result, time.time())
            
            return result
        return wrapper
    
    return decorator


def preprocess_for_visualization(df: pd.DataFrame) -> pd.DataFrame:
    """
    Preprocess DataFrame for visualization.
    
    Args:
        df: DataFrame to preprocess
        
    Returns:
        Preprocessed DataFrame
    """
    # Make a copy to avoid modifying the original
    processed_df = df.copy()
    
    # Handle missing values in key columns
    numeric_cols = ['voltage', 'current', 'capacity', 'temperature', 'c_rate', 'soc']
    
    for col in numeric_cols:
        if col in processed_df.columns:
            # Interpolate to fill gaps in time series data
            processed_df[col] = processed_df[col].interpolate(method='linear', limit=5)
    
    # Sort by timestamp if available
    if 'timestamp' in processed_df.columns:
        processed_df = processed_df.sort_values('timestamp')
    
    return processed_df


def format_time_axis(fig: go.Figure, time_col: str = 'timestamp', 
                    format_string: str = '%H:%M:%S') -> go.Figure:
    """
    Format time axis for better readability.
    
    Args:
        fig: Plotly figure to format
        time_col: Name of time column
        format_string: Format string for time display
        
    Returns:
        Formatted Plotly figure
    """
    fig.update_xaxes(
        tickformat=format_string,
        tickangle=-45,
        tickmode='auto',
        nticks=10
    )
    
    return fig


def handle_plotting_error(func: Callable) -> Callable:
    """
    Decorator to handle errors in plotting functions.
    
    Args:
        func: Plotting function to decorate
        
    Returns:
        Decorated function with error handling
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # Create error figure
            fig = go.Figure()
            fig.update_layout(
                title=f"Error creating plot: {str(e)}",
                annotations=[
                    dict(
                        text=f"Error details: {str(e)}",
                        showarrow=False,
                        xref="paper",
                        yref="paper",
                        x=0.5,
                        y=0.5
                    )
                ]
            )
            return fig
    
    return wrapper