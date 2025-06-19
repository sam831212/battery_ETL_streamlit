import plotly.express as px
import plotly.graph_objects as go
from app.services.DB_fetch_service import get_measurements_for_steps
from app.utils.dashboard_constants import MEASUREMENT_DF_COLUMNS
try:
    from st_aggrid import AgGrid
    AGGRID_AVAILABLE = True
except ImportError:
    AgGrid = None
    AGGRID_AVAILABLE = False


import pandas as pd
import streamlit as st
from st_aggrid import DataReturnMode, GridOptionsBuilder, GridUpdateMode, JsCode


from typing import Any, Dict, List

from app.utils.dashboard_utils import get_available_numeric_columns


def create_interactive_table(df: pd.DataFrame, table_name: str,
                           selection_mode: str = "multiple") -> Dict[str, Any]:
    """Create an interactive table with st_aggrid or fallback to streamlit"""
    if df.empty:
        st.warning(f"No data available for {table_name}")
        return {"selected_rows": []}

    df = df.reset_index(drop=True)

    if not AGGRID_AVAILABLE:
        st.dataframe(df, use_container_width=True)
        selected_rows = []
        if 'name' in df.columns:
            selected_names = st.multiselect(f"Select {table_name} (by name):",
                                          df['name'].tolist(),
                                          key=f"{table_name}_selector")
            if selected_names:
                selected_rows = df[df['name'].isin(selected_names)].to_dict('records')
        return {"selected_rows": selected_rows}

    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_pagination(paginationAutoPageSize=True)
    gb.configure_side_bar()
    gb.configure_selection(selection_mode=selection_mode)

    # Determine the column for checkbox selection
    checkbox_col = None    # Always use 'id' column for checkbox if present
    if 'id' in df.columns:
        checkbox_col = 'id'
    else:
        # Fallback: use the first available column (not 'id')
        checkbox_col = next((col_name for col_name in df.columns if col_name != 'id'), None)

    if checkbox_col:
        gb.configure_column(checkbox_col, checkboxSelection=True)

    # 移除針對特定表格的固定寬度設定，所有表格統一使用自動寬度調整
    
    grid_options = gb.build()

    # Enhanced grid options for better autowidth handling
    grid_options.update({
        'skipHeaderOnAutoSize': False,
        'suppressColumnVirtualisation': False,
        'enableColResize': True,
        'suppressSizeToFit': False,
        'autoSizeStrategy': {
            'type': 'fitCellContents'
        }
    })    # 增強的 JSCode 用於自動寬度調整 - 避免使用可能導致欄位收縮的 sizeColumnsToFit
    # 專注使用 autoSizeColumns 根據內容調整欄位寬度，類似 Excel 的雙擊自動調整功能
    auto_size_js = JsCode("""
    function(e) {
        // 多次嘗試以確保自動調整大小能正常運作
        function autoSizeAllColumns() {
            try {
                var allColumnIds = [];
                e.columnApi.getAllColumns().forEach(function(column) {
                    allColumnIds.push(column.colId);
                });
                
                // 根據內容和標頭自動調整欄位大小，類似 Excel 的自動調整欄寬功能
                e.columnApi.autoSizeColumns(allColumnIds, false);
                
            } catch (error) {
                console.log('AutoSize error:', error);
            }
        }
        
        // 在網格準備好後以及延遲後執行自動調整大小以確保穩定性
        setTimeout(autoSizeAllColumns, 50);
        setTimeout(autoSizeAllColumns, 200);
    }
    """)    # Define aggrid_key outside the conditional blocks
    aggrid_key = f"aggrid_{table_name.lower()}_{str(st.session_state.dashboard_filters)}"

    # 為所有表格啟用自動調整大小以確保 UI 穩定性
    fit_columns_on_grid_load = True
    column_auto_size_enabled = True

    if AgGrid is None:
        st.error("st_aggrid is not installed. Please install it to use interactive tables.")
        return {"selected_rows": []}
    try:
        grid_response = AgGrid(
            df,
            gridOptions=grid_options,
            data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
            update_mode=GridUpdateMode.SELECTION_CHANGED,
            enable_enterprise_modules=False,
            height=400,
            width='100%',
            key=aggrid_key,
            allow_unsafe_jscode=True,
            theme='streamlit',
            fit_columns_on_grid_load=fit_columns_on_grid_load,
            columns_auto_size_mode=1 if column_auto_size_enabled else 0,
            onGridReady=auto_size_js
        )
    except Exception:
        grid_response = AgGrid(
            df,
            gridOptions=grid_options,
            data_return_mode=DataReturnMode.AS_INPUT,
            update_mode=GridUpdateMode.SELECTION_CHANGED,
            enable_enterprise_modules=False,
            height=400,
            width='100%',
            key=f"{aggrid_key}_fallback",
            allow_unsafe_jscode=True,
            fit_columns_on_grid_load=fit_columns_on_grid_load,
            columns_auto_size_mode=1 if column_auto_size_enabled else 0,
            onGridReady=auto_size_js
        )

    selected_rows_data = grid_response.get('selected_rows', [])


    # Ensure selected_rows_data is a list of dicts
    if isinstance(selected_rows_data, pd.DataFrame):
        processed_selected_rows = selected_rows_data.to_dict('records')
    elif isinstance(selected_rows_data, list) and all(isinstance(item, dict) for item in selected_rows_data):
        processed_selected_rows = selected_rows_data
    else: # If it's in an unexpected format, try to handle or default to empty
        processed_selected_rows = []
        if selected_rows_data: # Log if there's data but format is wrong
            st.warning(f"AgGrid selected_rows for {table_name} in unexpected format. Please check AgGrid configuration.")

    # Return a copy of the grid_response and ensure 'selected_rows' is in the desired format
    response_dict = dict(grid_response)
    response_dict['selected_rows'] = processed_selected_rows

    return response_dict


def render_step_plot(steps_df: pd.DataFrame):
    """Render the Step-level data visualization"""
    st.subheader("Step-Level Data Visualization")

    if steps_df.empty:
        st.info("Select steps to enable plotting")
        return

    col1, col2, col3 = st.columns(3)

    numeric_candidates = ['step_number', 'duration', 'voltage_start', 'voltage_end',
                          'current', 'capacity', 'energy', 'temperature', 'c_rate',
                          'soc_start', 'soc_end']

    with col1:
        available_x_cols = get_available_numeric_columns(steps_df, numeric_candidates)
        x_axis = st.selectbox("X-axis", available_x_cols, index=0 if available_x_cols else None, key="step_plot_x_axis")

    with col2:
        available_y_cols = get_available_numeric_columns(steps_df, numeric_candidates)
        y_axis_default_idx = 0 if available_y_cols else None # Default to first option or None if no options

        if available_y_cols and x_axis and x_axis in available_y_cols:
            # Try to find a default Y different from X
            non_x_options = [col for col in available_y_cols if col != x_axis]
            if non_x_options:
                y_axis_default_idx = available_y_cols.index(non_x_options[0])
            # If only x_axis is available (or x_axis is not in available_y_cols), 
            # y_axis_default_idx remains pointing to the first element (0) or None.

        y_axis = st.selectbox("Y-axis", available_y_cols,
                             index=y_axis_default_idx,
                             key="step_plot_y_axis")

    with col3:
        categorical_columns = ['step_type', 'experiment_name', 'data_meta']
        available_color_cols = ['None'] + [col for col in categorical_columns if col in steps_df.columns and steps_df[col].nunique() > 0]
        color_by = st.selectbox("Color/Group by", available_color_cols, key="step_plot_color_by")

    if x_axis and y_axis:
        # Create the plot
        if color_by == 'None':
            fig = px.scatter(steps_df, x=x_axis, y=y_axis,
                           title=f"{y_axis} vs {x_axis}",
                           hover_data=['experiment_name', 'step_number', 'step_type'])
        else:
            fig = px.scatter(steps_df, x=x_axis, y=y_axis, color=color_by,
                           title=f"{y_axis} vs {x_axis} (colored by {color_by})",
                           hover_data=['experiment_name', 'step_number', 'step_type'])

        fig.update_layout(height=500)
        st.plotly_chart(fig, use_container_width=True)


def render_detail_plot(selected_step_ids: List[int], steps_meta_map: Dict[int, Any]):
    """Render the Detail-level time-series plotting area with selectable X and Y axes."""
    st.subheader("Detail-Level Time-Series Visualization")

    if not selected_step_ids:
        st.info("Select steps to enable time-series plotting")
        return

    measurements_df = get_measurements_for_steps(selected_step_ids)

    if measurements_df.empty:
        st.warning("No measurement data available for selected steps or an error occurred.")
        return

    # Potential candidates for axes
    # Ensure 'execution_time' is handled as a primary candidate for x-axis
    # Other numeric columns can be candidates for both x and y axes.
    all_plottable_columns = MEASUREMENT_DF_COLUMNS.copy()
    if 'step_id' in all_plottable_columns:
        all_plottable_columns.remove('step_id')

    x_axis_options = []
    if 'execution_time' in measurements_df.columns and not measurements_df['execution_time'].isna().all():
        x_axis_options.append('execution_time')

    numeric_cols_for_x = get_available_numeric_columns(measurements_df, [col for col in all_plottable_columns if col != 'execution_time'])
    x_axis_options.extend(numeric_cols_for_x)

    if not x_axis_options:
        st.warning("No suitable columns available for X-axis in measurement data.")
        return

    col1, col2, col3 = st.columns(3)

    with col1:
        x_axis_detail = st.selectbox("Select X-axis", x_axis_options, key="detail_plot_x_axis")

    # Y-axis candidates are determined directly by get_available_numeric_columns, excluding x_axis_detail
    # The variable y_axis_candidate_cols was unused and has been removed.

    with col2:
        available_y_metrics = get_available_numeric_columns(
            measurements_df,
            [col for col in all_plottable_columns if col != x_axis_detail]
        )

        # 預設 Y 軸不包含 X 軸（特別是 execution_time）
        default_y_selection = []
        if available_y_metrics:
            filtered_y_metrics = [col for col in available_y_metrics if col != x_axis_detail]
            if filtered_y_metrics:
                default_y_selection = filtered_y_metrics[:2] if len(filtered_y_metrics) >= 2 else filtered_y_metrics[:1]
            else:
                default_y_selection = available_y_metrics[:1]

        selected_y_metrics = st.multiselect(
            "Select Y-metrics",
            available_y_metrics,
            default=default_y_selection,
            key=f"detail_plot_y_metrics_{x_axis_detail}"
        )
    with col3:
        plot_type = st.radio("Plot type", ["Separate subplots", "Combined plot"], key="detail_plot_type")

    def get_legend_label(step_id_val):
        meta = steps_meta_map.get(step_id_val, None)
        if meta is not None and str(meta).strip() != '':
            return f"{meta} (Step {step_id_val})"
        else:
            return f"Step {step_id_val}"

    if x_axis_detail and selected_y_metrics:
        if plot_type == "Separate subplots":
            from plotly.subplots import make_subplots
            if not selected_y_metrics:
                st.info("Please select at least one Y-metric to plot.")
                return
            fig = make_subplots(
                rows=len(selected_y_metrics),
                cols=1,
                subplot_titles=[f"{metric} vs {x_axis_detail}" for metric in selected_y_metrics],
                shared_xaxes=True
            )

            # 為每個 step_id 分配固定顏色
            unique_step_ids = list(dict.fromkeys(selected_step_ids))
            colors = px.colors.qualitative.Plotly
            step_id_color_map = {step_id: colors[i % len(colors)] for i, step_id in enumerate(unique_step_ids)}

            for i, metric in enumerate(selected_y_metrics, 1):
                for j, step_id_val in enumerate(unique_step_ids):
                    step_data = measurements_df[measurements_df['step_id'] == step_id_val]
                    if not step_data.empty and x_axis_detail in step_data.columns and metric in step_data.columns:
                        if not step_data[x_axis_detail].isna().all() and not step_data[metric].isna().all():
                            fig.add_trace(
                                go.Scatter(
                                    x=step_data[x_axis_detail],
                                    y=step_data[metric],
                                    mode='lines',
                                    name=get_legend_label(step_id_val),
                                    line=dict(color=step_id_color_map[step_id_val]),
                                    showlegend=(i == 1)  # 只在第一個 subplot 顯示 legend
                                ),
                                row=i, col=1
                            )

            fig.update_layout(height=max(400, 200 * len(selected_y_metrics)), title_text=f"Time-Series Data: Metrics vs {x_axis_detail}")
            fig.update_xaxes(title_text=x_axis_detail)

        else: # Combined plot
            fig = go.Figure()
            # 為每個 step_id 分配固定顏色
            unique_step_ids = list(dict.fromkeys(selected_step_ids))
            colors = px.colors.qualitative.Plotly
            step_id_color_map = {step_id: colors[i % len(colors)] for i, step_id in enumerate(unique_step_ids)}

            for j, step_id_val in enumerate(unique_step_ids):
                for i, metric in enumerate(selected_y_metrics):
                    step_data = measurements_df[measurements_df['step_id'] == step_id_val]
                    if not step_data.empty and x_axis_detail in step_data.columns and metric in step_data.columns:
                        if not step_data[x_axis_detail].isna().all() and not step_data[metric].isna().all():
                            fig.add_trace(
                                go.Scatter(
                                    x=step_data[x_axis_detail],
                                    y=step_data[metric],
                                    mode='lines',
                                    name=f"{metric} (" + get_legend_label(step_id_val) + ")",
                                    line=dict(color=step_id_color_map[step_id_val]),
                                    yaxis=f"y{i+1}" if len(selected_y_metrics) > 1 else "y",
                                    showlegend=(i == 0)  # 只在第一個 y-metric 顯示 legend
                                )
                            )

            fig.update_layout(
                height=500,
                title_text=f"Combined Time-Series: Metrics vs {x_axis_detail}",
                xaxis_title=x_axis_detail
            )

            if len(selected_y_metrics) == 1:
                 fig.update_layout(yaxis_title=selected_y_metrics[0])
            elif len(selected_y_metrics) > 1:
                fig.update_layout(yaxis_title=selected_y_metrics[0])
                for i, metric_name in enumerate(selected_y_metrics[1:], start=1):
                    fig.update_layout({
                        f'yaxis{i+1}': {
                            'title': metric_name,
                            'overlaying': 'y',
                            'side': 'right' if i % 2 == 0 else 'left',
                            'position': 0.15 * i if i%2 !=0 else 1 - (0.15* (i-1)),
                            'showgrid': False,
                        }
                    })
                fig.update_layout(margin=dict(r=80 + (len(selected_y_metrics)-2)*60))

        st.plotly_chart(fig, use_container_width=True)
    elif not selected_y_metrics:
        st.info("Please select at least one Y-metric to plot.")
