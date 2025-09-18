import pandas as pd
import streamlit as st

from app.visualization import plot_combined_voltage_current, plot_current_vs_time, plot_temperature_vs_time, plot_voltage_vs_time


def display_data_statistics(step_df: pd.DataFrame, detail_df: pd.DataFrame):
    """
    Display basic statistics about the data files.

    Args:
        step_df: DataFrame containing step data
        detail_df: DataFrame containing detail data
    """
    st.subheader("Data Statistics")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Steps", step_df['step_number'].nunique())

    with col2:
        st.metric("Step Records", len(step_df))

    with col3:
        step_types = step_df['step_type'].value_counts()
        common_step = step_types.index[0] if not step_types.empty else "N/A"
        st.metric("Primary Step Type", common_step)


def display_data_tables(step_df: pd.DataFrame, detail_df: pd.DataFrame):
    """
    Display data tables with tabs for different tables.

    Args:
        step_df: DataFrame containing step data
        detail_df: DataFrame containing detail data
    """
    st.subheader("Data Tables")

    # Create tabs for different data tables
    table_tabs = st.tabs([
        "Step Data",
        "Detail Data"
    ])

    # Tab 1: Step Data
    with table_tabs[0]:
        st.write("### Step Data Preview")

        # 定義欄位顯示順序
        column_order = [
            'step_number',        # 工步
            'original_step_type', # 原始工步種類
            'start_time',        # 日期時間
            'duration',          # 工步執行時間(秒)
            'voltage_start',     # 開始電壓
            'voltage_end',       # 截止電壓(V)
            'current',           # 截止電流(A)
            'capacity',          # 截止電量(Ah)
            'total_capacity',    # 總電量(Ah)
            'soc_start',         # 起始SOC
            'soc_end',           # 結束SOC
            'energy',           # 能量(Wh)
            'power',            # 功率(W)
            'temperature'        # Aux T1
        ]

        # 建立中英文欄位對照表
        column_mapping = {
            'step_number': '工步',
            'step_type': '工步種類',
            'start_time': '日期時間',
            'capacity': '截止電量(Ah)',
            'current': '截止電流(A)',
            'voltage_end': '截止電壓(V)',
            'voltage_start': '開始電壓',  # 改為中文顯示
            'original_step_type': '原始工步種類',
            'energy': '能量(Wh)',
            'total_capacity': '總電量(Ah)',
            'soc_start': '起始SOC(%)',
            'soc_end': '結束SOC(%)',
            'power': '功率(W)',
            'temperature': 'Aux T1',
            'duration': '工步執行時間(秒)'
        }

        # 確保所有要顯示的欄位都存在於資料中
        display_columns = [col for col in column_order if col in step_df.columns]

        # 按照指定順序顯示欄位，使用中文名稱
        st.dataframe(
            step_df[display_columns].rename(columns=column_mapping),
            use_container_width=True,
            height=300
        )

    # Tab 2: Detail Data
    with table_tabs[1]:
        st.write("### Detail Data Preview")

        # For large datasets, show only a sample
        if len(detail_df) > 10000:
            st.info(f"Showing a sample of {10000} records out of {len(detail_df)} total records.")
            display_df = detail_df.sample(10000) if len(detail_df) > 10000 else detail_df
        else:
            display_df = detail_df

        st.dataframe(
            display_df,
            use_container_width=True,
            height=300
        )


def display_visualizations(step_df: pd.DataFrame, detail_df: pd.DataFrame):
    """
    Display visualizations with tabs for different plot types.

    Args:
        step_df: DataFrame containing step data
        detail_df: DataFrame containing detail data
    """
    st.subheader("Data Visualization")

    # Create tabs for different visualization types
    viz_tabs = st.tabs([
        "Voltage-Time",
        "Current-Time",
        "Combined Plots"
    ])

    # Tab 1: Voltage vs Time
    with viz_tabs[0]:
        st.write("### Voltage vs Time")

        try:
            # Use detail data for time series plots
            # Limit to 10,000 points for performance
            if len(detail_df) > 10000:
                st.info(f"Showing plot with 10,000 sample points out of {len(detail_df)} total points for performance.")
                plot_data = detail_df.sample(10000)
            else:
                plot_data = detail_df

            vt_fig = plot_voltage_vs_time(
                plot_data,
                voltage_col='voltage',
                time_col='timestamp',
                step_type_col='step_type',
                step_number_col='step_number',
                title='Voltage vs Time by Step Type'
            )
            st.plotly_chart(vt_fig, use_container_width=True)
        except Exception as e:
            st.error(f"Error generating Voltage vs Time plot: {str(e)}")
            st.info("This plot requires 'voltage', 'timestamp', and 'step_type' columns in the detail data.")

    # Tab 2: Current vs Time
    with viz_tabs[1]:
        st.write("### Current vs Time")

        try:
            # Use detail data for time series plots
            # Limit to 10,000 points for performance
            if len(detail_df) > 10000:
                plot_data = detail_df.sample(10000)
            else:
                plot_data = detail_df

            ct_fig = plot_current_vs_time(
                plot_data,
                current_col='current',
                time_col='timestamp',
                step_type_col='step_type',
                step_number_col='step_number',
                title='Current vs Time by Step Type'
            )
            st.plotly_chart(ct_fig, use_container_width=True)
        except Exception as e:
            st.error(f"Error generating Current vs Time plot: {str(e)}")
            st.info("This plot requires 'current', 'timestamp', and 'step_type' columns in the detail data.")

    # Tab 3: Combined Plots
    with viz_tabs[2]:
        st.write("### Combined Voltage, Current, and Temperature")

        try:
            # Use detail data for time series plots
            # Limit to 10,000 points for performance
            if len(detail_df) > 10000:
                plot_data = detail_df.sample(10000)
            else:
                plot_data = detail_df

            combined_fig = plot_combined_voltage_current(
                plot_data,
                voltage_col='voltage',
                current_col='current',
                temperature_col='temperature',
                time_col='timestamp',
                step_type_col='step_type',
                step_number_col='step_number',
                include_temperature=True,
                title='Voltage, Current, and Temperature vs Time'
            )
            st.plotly_chart(combined_fig, use_container_width=True)
        except Exception as e:
            st.error(f"Error generating Combined plot: {str(e)}")
            st.info("This plot requires 'voltage', 'current', 'temperature', 'timestamp', and 'step_type' columns in the detail data.")
