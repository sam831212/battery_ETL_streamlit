from typing import Any, Dict, List
import pandas as pd
import streamlit as st


def display_file_statistics(step_df: pd.DataFrame, detail_df: pd.DataFrame):
    """
    Display statistics for uploaded CSV files.

    Args:
        step_df: Step data DataFrame
        detail_df: Detail data DataFrame
    """
    st.subheader("File Statistics")

    col1, col2 = st.columns(2)

    with col1:
        st.write("### Step File")
        st.write(f"**Rows:** {len(step_df):,}")
        st.write(f"**Columns:** {len(step_df.columns)}")

        # Get step types and show breakdown
        if "Step_Type" in step_df.columns:
            st.write("#### Step Types")
            step_types = step_df["Step_Type"].value_counts().reset_index()
            step_types.columns = ["Step Type", "Count"]
            st.dataframe(step_types, use_container_width=True)

        # Show time range if available
        if "Date_Time" in step_df.columns:
            try:
                min_time = pd.to_datetime(step_df["Date_Time"].min())
                max_time = pd.to_datetime(step_df["Date_Time"].max())
                st.write("#### Time Range")
                st.write(f"From: {min_time}")
                st.write(f"To: {max_time}")
                duration = max_time - min_time
                st.write(f"Duration: {duration}")
            except Exception as e:
                st.warning(f"Could not determine time range: {str(e)}")

    with col2:
        st.write("### Detail File")
        st.write(f"**Rows:** {len(detail_df):,}")
        st.write(f"**Columns:** {len(detail_df.columns)}")

        # Show basic statistics for key columns
        numeric_cols = detail_df.select_dtypes(include=['number']).columns.tolist()
        key_cols = [col for col in ['Voltage', 'Current', 'Capacity', 'Energy'] if col in numeric_cols]

        if key_cols:
            st.write("#### Key Measurements")
            stats_df = pd.DataFrame()

            for col in key_cols:
                stats_df.loc["Min", col] = detail_df[col].min()
                stats_df.loc["Max", col] = detail_df[col].max()
                stats_df.loc["Mean", col] = detail_df[col].mean()
                stats_df.loc["Std", col] = detail_df[col].std()

            st.dataframe(stats_df.style.format("{:.4f}"), use_container_width=True)

        # Show time range if available
        datetime_col = next((col for col in ['Date_Time', 'DateTime'] if col in detail_df.columns), None)
        if datetime_col:
            try:
                min_time = pd.to_datetime(detail_df[datetime_col].min())
                max_time = pd.to_datetime(detail_df[datetime_col].max())
                st.write("#### Time Range")
                st.write(f"From: {min_time}")
                st.write(f"To: {max_time}")
                duration = max_time - min_time
                st.write(f"Duration: {duration}")

                # Show measurement frequency
                total_seconds = duration.total_seconds()
                if total_seconds > 0:
                    frequency = len(detail_df) / total_seconds
                    st.write(f"Measurement Frequency: {frequency:.2f} samples/second")
            except Exception as e:
                st.warning(f"Could not determine time range: {str(e)}")


def display_validation_results(
    step_valid: bool,
    detail_valid: bool,
    step_missing: List[str],
    detail_missing: List[str]
):
    """
    Display validation results for the files.

    Args:
        step_valid: Whether step file is valid
        detail_valid: Whether detail file is valid
        step_missing: Missing headers in step file
        detail_missing: Missing headers in detail file
    """
    # Create columns for the results
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Step File Validation")
        if step_valid:
            st.success("Step file is valid ✅")
        else:
            st.error("Step file is missing required headers ❌")
            if step_missing:
                st.warning(f"Missing headers: {', '.join(step_missing)}")

    with col2:
        st.subheader("Detail File Validation")
        if detail_valid:
            st.success("Detail file is valid ✅")
        else:
            st.error("Detail file is missing required headers ❌")
            if detail_missing:
                st.warning(f"Missing headers: {', '.join(detail_missing)}")

    # Overall status
    if step_valid and detail_valid:
        st.success("Both files are valid and ready for processing.")
    else:
        st.error("Please provide valid files with the required headers before processing.")


def display_validation_summary(
    validation_status: bool,
    step_validation_report: Dict[str, Any],
    detail_validation_report: Dict[str, Any]
):
    """
    Display validation summary for the data.

    Args:
        validation_status: Overall validation status
        step_validation_report: Step validation report
        detail_validation_report: Detail validation report
    """
    st.subheader("Data Validation Summary")

    # Overall status
    if validation_status:
        st.success("✅ Data validation passed - files are ready for processing")
    else:
        st.error("❌ Data validation failed - please check the issues below")

    # Create tabs for detailed reports
    step_tab, detail_tab = st.tabs(["Step Data", "Detail Data"])

    # Step data validation summary
    with step_tab:
        st.write("### Step Data Summary")

        # Display basic stats
        st.write(f"**Total rows:** {step_validation_report.get('row_count', 0)}")
        st.write(f"**Total columns:** {step_validation_report.get('column_count', 0)}")

        # Column validation
        if step_validation_report.get('has_required_columns', False):
            st.success("All required columns are present")
        else:
            st.error(f"Missing required columns: {', '.join(step_validation_report.get('missing_columns', []))}")

        # Display step types if available
        if step_validation_report.get('step_types'):
            st.write("### Step Types Breakdown")
            step_types_df = pd.DataFrame(
                list(step_validation_report.get('step_types', {}).items()),
                columns=["Step Type", "Count"]
            )
            st.dataframe(step_types_df)

            # Optional: Add visualization
            if not step_types_df.empty:
                st.bar_chart(step_types_df.set_index("Step Type"))

        # Time range info
        if step_validation_report.get('time_range_valid', False):
            st.write("### Time Range")
            st.write(f"**Start time:** {step_validation_report.get('start_time')}")
            st.write(f"**End time:** {step_validation_report.get('end_time')}")

    # Detail data validation summary
    with detail_tab:
        st.write("### Detail Data Summary")

        # Display basic stats
        st.write(f"**Total rows:** {detail_validation_report.get('row_count', 0)}")
        st.write(f"**Total columns:** {detail_validation_report.get('column_count', 0)}")

        # Column validation
        if detail_validation_report.get('has_required_columns', False):
            st.success("All required columns are present")
        else:
            st.error(f"Missing required columns: {', '.join(detail_validation_report.get('missing_columns', []))}")

        # Value ranges for key columns
        st.write("### Value Ranges")
        range_data = []

        for col in ["Voltage", "Current", "Capacity"]:
            if all(k in detail_validation_report for k in [f"{col}_min", f"{col}_max", f"{col}_mean"]):
                range_data.append({
                    "Column": col,
                    "Min": round(detail_validation_report.get(f"{col}_min", 0), 4),
                    "Max": round(detail_validation_report.get(f"{col}_max", 0), 4),
                    "Mean": round(detail_validation_report.get(f"{col}_mean", 0), 4)
                })

        if range_data:
            range_df = pd.DataFrame(range_data)
            st.dataframe(range_df)

        # Time range info
        if detail_validation_report.get('time_range_valid', False):
            st.write("### Time Range")
            st.write(f"**Start time:** {detail_validation_report.get('start_time')}")
            st.write(f"**End time:** {detail_validation_report.get('end_time')}")

    # Show overall validation decision
    if validation_status:
        st.success("Files are valid and can be processed")
    else:
        st.error("Please fix the validation issues before processing")