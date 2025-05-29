"""
Dashboard UI components for the Battery ETL Dashboard

This module provides UI components for visualizing and analyzing battery test data.
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from app.models.database import Experiment, Step, Measurement, ProcessedFile, Cell, Machine
from app.utils.database import get_session
from sqlmodel import select, desc, func


def render_dashboard_page():
    """Render the dashboard page UI
    
    This function displays the dashboard UI components for visualizing and
    analyzing battery test data.
    """
    st.header("Battery Test Data Dashboard")
    
    # Initialize session state for filters if they don't exist
    if 'start_date_filter' not in st.session_state:
        st.session_state['start_date_filter'] = datetime.now().date() - timedelta(days=30)
    if 'end_date_filter' not in st.session_state:
        st.session_state['end_date_filter'] = datetime.now().date()
    if 'selected_step_types_filter' not in st.session_state:
        st.session_state['selected_step_types_filter'] = ["Charge", "Discharge", "Rest", "Waveform"]

    # Create sidebar filters
    with st.sidebar:
        st.markdown("## Dashboard Filters")
        
        # Date range filter
        st.subheader("Date Range (Experiment Creation Date)")
        start_date_input = st.date_input(
            "Start Date",
            value=st.session_state.start_date_filter,
            help="Filter experiments created from this date.",
        )
        
        end_date_input = st.date_input(
            "End Date",
            value=st.session_state.end_date_filter,
            help="Filter experiments created until this date.",
        )
        # Update session state on change
        if start_date_input != st.session_state.start_date_filter:
            st.session_state.start_date_filter = start_date_input
            st.rerun() # Rerun to apply filter
        if end_date_input != st.session_state.end_date_filter:
            st.session_state.end_date_filter = end_date_input
            st.rerun()

        # Convert date to datetime for query (start of day for start_date, end of day for end_date)
        start_datetime = datetime.combine(st.session_state.start_date_filter, datetime.min.time())
        end_datetime = datetime.combine(st.session_state.end_date_filter, datetime.max.time())

        # Get available experiments from database based on date range
        available_experiments = []
        with get_session() as session:
            query = select(Experiment, Cell, Machine).\
                outerjoin(Cell, Experiment.cell_id == Cell.id).\
                outerjoin(Machine, Experiment.machine_id == Machine.id).\
                where(Experiment.created_at >= start_datetime).\
                where(Experiment.created_at <= end_datetime).\
                order_by(desc(Experiment.created_at))
            
            results = session.exec(query).all()
            
            if results:
                available_experiments_data = []
                for exp, cell, machine in results:
                    cell_name = f"{cell.name}" if cell and cell.name else ""
                    cell_name_display = f"{cell_name}: " if cell_name else ""
                    cell_info = f" | Cell: {cell_name_display}{cell.chemistry.value} {cell.capacity}Ah" if cell else ""
                    machine_info = f" | Machine: {machine.name}" if machine else ""
                    label = f"{exp.name} ({exp.battery_type}){cell_info}{machine_info}"
                    available_experiments_data.append({"id": exp.id, "label": label})
                
                experiment_options = [data["label"] for data in available_experiments_data]
                experiment_ids = [data["id"] for data in available_experiments_data]

                if not experiment_options:
                    experiment_options = ["No experiments match date range"]
                    experiment_ids = []
            else:
                experiment_options = ["No experiments available"]
                experiment_ids = []
        
        st.subheader("Experiment")
        # If current selected experiment is not in the filtered list, reset it
        if st.session_state.get("selected_experiment_id") not in experiment_ids:
            st.session_state["selected_experiment_id"] = experiment_ids[0] if experiment_ids else None

        selected_experiment_label = st.selectbox(
            "Select Experiment",
            options=experiment_options,
            index=experiment_ids.index(st.session_state["selected_experiment_id"]) if st.session_state["selected_experiment_id"] in experiment_ids else 0,
            disabled=not experiment_ids,
            help="Select an experiment to visualize data for. Filtered by date range.",
        )
        
        if experiment_ids:
            # Find the ID corresponding to the selected label
            selected_id = next((data["id"] for data in available_experiments_data if data["label"] == selected_experiment_label), None)
            if selected_id != st.session_state.get("selected_experiment_id"):
                st.session_state["selected_experiment_id"] = selected_id
                # st.rerun() # Rerun if selection changes, might be handled by Streamlit implicitly for selectbox
        elif st.session_state.get("selected_experiment_id") is not None:
             st.session_state["selected_experiment_id"] = None


        # Step type filter
        st.subheader("Step Type (for Voltage/Temp step charts)")
        step_types_options = ["Charge", "Discharge", "Rest", "Waveform"]
        selected_step_types_input = st.multiselect(
            "Select Step Types",
            options=step_types_options,
            default=st.session_state.selected_step_types_filter,
            help="Filter step types for detailed plots in Voltage and Temperature tabs.",
        )
        if selected_step_types_input != st.session_state.selected_step_types_filter:
            st.session_state.selected_step_types_filter = selected_step_types_input
            st.rerun()
            
    # Display selected experiment details
    if st.session_state.get("selected_experiment_id"):
        with get_session() as session:
            exp_id = st.session_state["selected_experiment_id"]
            # Fetch experiment with cell and machine
            detailed_exp_stmt = select(Experiment, Cell, Machine).\
                outerjoin(Cell, Experiment.cell_id == Cell.id).\
                outerjoin(Machine, Experiment.machine_id == Machine.id).\
                where(Experiment.id == exp_id)
            
            result = session.exec(detailed_exp_stmt).first()

            if result:
                exp, cell, machine = result
                st.markdown("### Selected Experiment Details")
                details_cols = st.columns(3)
                details_cols[0].metric("Experiment Name", exp.name)
                details_cols[1].metric("Battery Type", exp.battery_type)
                details_cols[2].metric("Creation Date", exp.created_at.strftime("%Y-%m-%d %H:%M"))

                cell_info_str = "N/A"
                if cell:
                    cell_name_display = f"{cell.name}: " if cell.name else ""
                    cell_info_str = f"{cell_name_display}{cell.chemistry.value} {cell.capacity}Ah, Form: {cell.form.value}"
                details_cols[0].markdown(f"**Cell:** {cell_info_str}")

                machine_info_str = "N/A"
                if machine:
                    machine_info_str = f"{machine.name} (Model: {machine.model_number or 'N/A'})"
                details_cols[1].markdown(f"**Machine:** {machine_info_str}")
                details_cols[2].markdown(f"**Nominal Capacity:** {exp.nominal_capacity if exp.nominal_capacity is not None else 'N/A'} Ah")
                st.markdown("---")
            else:
                st.warning("Could not load details for the selected experiment.")
    else:
        st.info("No experiment selected or available with the current filters. Please adjust filters or select an experiment.")

    # Create tabs for different visualizations
    overview_tab, capacity_tab, voltage_tab, temperature_tab, validation_tab = st.tabs([
        "Overview", "Capacity Analysis", "Voltage Analysis", "Temperature Analysis", "Validation"
    ])
    
    with overview_tab:
        render_overview_tab()
    
    with capacity_tab:
        render_capacity_tab()
    
    with voltage_tab:
        render_voltage_tab()
    
    with temperature_tab:
        render_temperature_tab()
        
    with validation_tab:
        render_validation_tab()


def render_overview_tab():
    """Render the overview tab content"""
    st.subheader("Experiment Overview")

    selected_experiment_id = st.session_state.get("selected_experiment_id")
    if not selected_experiment_id:
        st.info("Please select an experiment from the sidebar or adjust filters to view its overview.")
        return

    with st.spinner("Loading overview data..."):
        with get_session() as session:
            # Experiment details are already fetched and displayed above the tabs
            # Fetch steps for the selected experiment
        steps_statement = select(Step).where(Step.experiment_id == selected_experiment_id)
        all_steps_for_experiment = session.exec(steps_statement).all()

        total_discharge_capacity_ah = 0
        total_charge_capacity_ah = 0
        discharge_cycle_numbers = set() # For cycle count based on discharge steps
        discharge_capacities_per_cycle = []

        if all_steps_for_experiment:
            for step in all_steps_for_experiment:
                if step.step_type == "discharge" and step.capacity_ah is not None:
                    total_discharge_capacity_ah += step.capacity_ah
                    if step.cycle_number is not None:
                        discharge_cycle_numbers.add(step.cycle_number)
                        discharge_capacities_per_cycle.append({"cycle": step.cycle_number, "capacity": step.capacity_ah})
                elif step.step_type == "charge" and step.capacity_ah is not None:
                    total_charge_capacity_ah += step.capacity_ah
            
            discharge_capacities_per_cycle = sorted(discharge_capacities_per_cycle, key=lambda x: x['cycle'])

        cycle_count = len(discharge_cycle_numbers)
        
        efficiency = (total_discharge_capacity_ah / total_charge_capacity_ah * 100) \
            if total_charge_capacity_ah > 0 else 0

        # Fetch max temperature for the selected experiment
        max_temp_statement = select(func.max(Measurement.temperature_c)).\
            where(Measurement.experiment_id == selected_experiment_id)
        max_temp = session.exec(max_temp_statement).one_or_none()
        max_temp_display = f"{max_temp:.2f}" if max_temp is not None else "--"

    # Create metrics row
    metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
    with metric_col1:
        st.metric("Total Discharge Capacity (Ah)", f"{total_discharge_capacity_ah:.2f}" if total_discharge_capacity_ah else "--", help="Sum of discharge capacities of all 'discharge' type steps in the selected experiment.")
    with metric_col2:
        st.metric("Cycle Count", str(cycle_count) if cycle_count else "--", help="Total number of unique cycles identified from 'discharge' type steps in the selected experiment.")
    with metric_col3:
        st.metric("Overall C/D Efficiency (%)", f"{efficiency:.2f}%" if efficiency else "--", help="Ratio of total discharge capacity to total charge capacity for 'discharge' and 'charge' steps in the selected experiment.")
    with metric_col4:
        st.metric("Max Temperature (°C)", max_temp_display, help="Highest temperature recorded across all measurements for the selected experiment.")

    st.subheader("Discharge Capacity per Cycle")
    if discharge_capacities_per_cycle:
        df_capacity_cycle = pd.DataFrame(discharge_capacities_per_cycle)
        # Aggregate capacity if multiple discharge steps exist for the same cycle
        df_capacity_cycle_agg = df_capacity_cycle.groupby('cycle', as_index=False)['capacity'].sum()
        
        fig = px.bar(df_capacity_cycle_agg, x='cycle', y='capacity',
                       labels={'cycle': 'Cycle Number', 'capacity': 'Discharge Capacity (Ah)'},
                       title="Discharge Capacity vs. Cycle Number (Discharge Steps Only)")
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No discharge capacity data (from 'discharge' steps) available to display for this experiment.")


def render_capacity_tab():
    """Render the capacity analysis tab content"""
    st.subheader("Capacity Analysis (Based on 'Discharge' Steps)")

    selected_experiment_id = st.session_state.get("selected_experiment_id")
    if not selected_experiment_id:
        st.info("Please select an experiment from the sidebar or adjust filters to view capacity analysis.")
        return

    with st.spinner("Loading capacity analysis data..."):
        with get_session() as session:
            # Fetch discharge steps with capacity and cycle number for the selected experiment
            stmt = select(Step.cycle_number, Step.capacity_ah).\
            where(Step.experiment_id == selected_experiment_id).\
            where(Step.step_type == "discharge").\ # Explicitly for discharge steps
            where(Step.capacity_ah.isnot(None)).\
            where(Step.cycle_number.isnot(None)).\
            order_by(Step.cycle_number)
        
        discharge_data = session.exec(stmt).all()

        if not discharge_data:
            st.info("No discharge capacity data available for this experiment (check filters and data).")
            # Create an empty figure with a message
            fig = go.Figure()
            fig.add_annotation(x=0.5, y=0.5, text="No discharge capacity data available.", showarrow=False, font=dict(size=16))
            fig.update_layout(height=400, xaxis_title="Cycle Number", yaxis_title="Discharge Capacity (Ah)")
            st.plotly_chart(fig, use_container_width=True)
            return

        df_discharge = pd.DataFrame(discharge_data, columns=['cycle_number', 'capacity_ah'])
        
        # Aggregate capacity if multiple discharge steps exist for the same cycle
        df_discharge_agg = df_discharge.groupby('cycle_number')['capacity_ah'].sum().reset_index()

        fig = px.line(df_discharge_agg, x='cycle_number', y='capacity_ah',
                        title='Discharge Capacity vs. Cycle Number',
                        labels={'cycle_number': 'Cycle Number', 'capacity_ah': 'Discharge Capacity (Ah)'},
                        markers=True)
        fig.update_layout(height=500)
        st.plotly_chart(fig, use_container_width=True)
        
        # Capacity Retention
        if not df_discharge_agg.empty:
            initial_capacity = df_discharge_agg['capacity_ah'].iloc[0]
            if initial_capacity > 0:
                df_discharge_agg['capacity_retention_percent'] = (df_discharge_agg['capacity_ah'] / initial_capacity) * 100
                
                fig_retention = px.line(df_discharge_agg, x='cycle_number', y='capacity_retention_percent',
                                     title='Capacity Retention vs. Cycle Number',
                                     labels={'cycle_number': 'Cycle Number', 'capacity_retention_percent': 'Capacity Retention (%)'},
                                     markers=True)
                fig_retention.update_layout(height=500, yaxis_range=[0, df_discharge_agg['capacity_retention_percent'].max() * 1.1 if not df_discharge_agg['capacity_retention_percent'].empty else 110])
                st.plotly_chart(fig_retention, use_container_width=True)
                st.caption("This chart shows how much of the initial capacity is retained over cycles. A steeper decline may indicate faster degradation.")
            else:
                st.info("Initial capacity is zero or invalid, cannot calculate capacity retention.")
        else:
            st.info("No aggregated discharge data available to calculate capacity retention.")


def render_voltage_tab():
    """Render the voltage analysis tab content"""
    st.subheader("Voltage Analysis")

    selected_experiment_id = st.session_state.get("selected_experiment_id")
    selected_step_types_filter = st.session_state.get('selected_step_types_filter', [])
    # Convert to lowercase for DB query if necessary (assuming DB stores lowercase)
    selected_step_types_filter_lower = [stype.lower() for stype in selected_step_types_filter]


    if not selected_experiment_id:
        st.info("Please select an experiment from the sidebar or adjust filters to view voltage analysis.")
        return
    
    if not selected_step_types_filter_lower:
        st.warning("Please select at least one step type in the sidebar filter to see voltage plots.")
        return

    with st.spinner("Loading voltage analysis data..."):
        with get_session() as session:
            # Get available steps based on selected experiment AND step_type filter
            stmt_steps_filtered = select(Step.cycle_number, Step.step_type, Step.id, Step.step_number).\
            where(Step.experiment_id == selected_experiment_id).\
            where(Step.cycle_number.isnot(None)).\
            where(Step.step_type.in_(selected_step_types_filter_lower)).\
            order_by(Step.cycle_number, Step.step_number) # Use step_number for better ordering
        
        available_steps = session.exec(stmt_steps_filtered).all()

        if not available_steps:
            st.info(f"No steps matching the selected types ({', '.join(selected_step_types_filter)}) and cycle criteria found for this experiment.")
            # Create empty figures with messages
            fig_vc = go.Figure()
            fig_vc.add_annotation(x=0.5, y=0.5, text="No data for Voltage vs. Capacity.", showarrow=False, font=dict(size=16))
            fig_vc.update_layout(height=400, xaxis_title="Capacity (Ah)", yaxis_title="Voltage (V)")
            st.plotly_chart(fig_vc, use_container_width=True)

            fig_vt = go.Figure()
            fig_vt.add_annotation(x=0.5, y=0.5, text="No data for Voltage vs. Time.", showarrow=False, font=dict(size=16))
            fig_vt.update_layout(height=400, xaxis_title="Time (s)", yaxis_title="Voltage (V)")
            st.plotly_chart(fig_vt, use_container_width=True)
            return

        step_options = {
    f"Step {s.step_number} (Cycle {s.cycle_number if s.cycle_number is not None else 'N/A'}) - {s.step_type.capitalize()}": s.id 
    for s in available_steps
}
        
        selected_step_label = st.selectbox(
            "Select Step for Voltage Plots", 
            options=list(step_options.keys()),
            key="voltage_step_select",
            help="Select a specific step to view its detailed voltage vs. capacity and voltage vs. time profiles. Filtered by 'Step Type' selection in the sidebar."
        )
        
        if not selected_step_label: # Should not happen if available_steps is not empty
            st.info("No steps available for selection.")
            return

        selected_step_id = step_options[selected_step_label]
        selected_step_info = next(s for s in available_steps if s.id == selected_step_id)


        # Fetch measurements for the selected step
        stmt_measurements = select(Measurement.voltage_v, Measurement.charge_capacity_ah, Measurement.discharge_capacity_ah, Measurement.step_time_s).\
            where(Measurement.step_id == selected_step_id).\
            order_by(Measurement.step_time_s)
        
        measurements = session.exec(stmt_measurements).all()

        if not measurements:
            st.warning(f"No measurement data found for the selected step: {selected_step_label}. Check data integrity or filters.")
            # Create empty figures with messages
            fig_vc = go.Figure()
            fig_vc.add_annotation(x=0.5, y=0.5, text=f"No measurements for {selected_step_label}.", showarrow=False, font=dict(size=16))
            fig_vc.update_layout(height=400, xaxis_title="Capacity (Ah)", yaxis_title="Voltage (V)")
            st.plotly_chart(fig_vc, use_container_width=True)

            fig_vt = go.Figure()
            fig_vt.add_annotation(x=0.5, y=0.5, text=f"No measurements for {selected_step_label}.", showarrow=False, font=dict(size=16))
            fig_vt.update_layout(height=400, xaxis_title="Time (s)", yaxis_title="Voltage (V)")
            st.plotly_chart(fig_vt, use_container_width=True)
            return

        df_measurements = pd.DataFrame(measurements, columns=['voltage_v', 'charge_capacity_ah', 'discharge_capacity_ah', 'step_time_s'])
        
        capacity_column_name = 'Charge Capacity (Ah)' if selected_step_info.step_type == 'charge' else 'Discharge Capacity (Ah)'
        df_measurements['capacity_ah_plot'] = df_measurements['charge_capacity_ah'] if selected_step_info.step_type == 'charge' else df_measurements['discharge_capacity_ah']

        # Voltage vs. Capacity
        fig_vc = px.line(df_measurements, x='capacity_ah_plot', y='voltage_v',
                         title=f'Voltage vs. Capacity ({selected_step_label})',
                         labels={'capacity_ah_plot': capacity_column_name, 'voltage_v': 'Voltage (V)'})
        fig_vc.update_layout(height=500)
        st.plotly_chart(fig_vc, use_container_width=True)

        # Voltage vs. Time
        fig_vt = px.line(df_measurements, x='step_time_s', y='voltage_v',
                         title=f'Voltage vs. Time ({selected_step_label})',
                         labels={'step_time_s': 'Step Time (s)', 'voltage_v': 'Voltage (V)'})
        fig_vt.update_layout(height=500)
        st.plotly_chart(fig_vt, use_container_width=True)


def render_temperature_tab():
    """Render the temperature analysis tab content"""
    st.subheader("Temperature Analysis")

    selected_experiment_id = st.session_state.get("selected_experiment_id")
    selected_step_types_filter = st.session_state.get('selected_step_types_filter', [])
    selected_step_types_filter_lower = [stype.lower() for stype in selected_step_types_filter]

    if not selected_experiment_id:
        st.info("Please select an experiment from the sidebar or adjust filters to view temperature analysis.")
        return

    with st.spinner("Loading temperature analysis data..."):
        with get_session() as session:
            # Overall Experiment Temperature vs. Time (respects experiment date filter)
            st.markdown("#### Overall Experiment Temperature Profile")
            stmt_overall_temp = select(Measurement.experiment_time_s, Measurement.temperature_c).\
            where(Measurement.experiment_id == selected_experiment_id).\
            where(Measurement.temperature_c.isnot(None)).\
            where(Measurement.experiment_time_s.isnot(None)).\
            order_by(Measurement.experiment_time_s)
        
        overall_temperature_data = session.exec(stmt_overall_temp).all()

        if not overall_temperature_data:
            st.info("No overall temperature data available for this experiment (check filters and data).")
            # Create an empty figure with a message
            fig_overall = go.Figure()
            fig_overall.add_annotation(x=0.5, y=0.5, text="No overall temperature data available.", showarrow=False, font=dict(size=16))
            fig_overall.update_layout(height=400, xaxis_title="Experiment Time (s)", yaxis_title="Temperature (°C)")
            st.plotly_chart(fig_overall, use_container_width=True)
        else:
            df_overall_temp = pd.DataFrame(overall_temperature_data, columns=['experiment_time_s', 'temperature_c'])
            fig_overall = px.line(df_overall_temp, x='experiment_time_s', y='temperature_c',
                            title='Overall Experiment Temperature vs. Time',
                            labels={'experiment_time_s': 'Experiment Time (s)', 'temperature_c': 'Temperature (°C)'},
                            markers=False)
            fig_overall.update_layout(height=500)
            st.plotly_chart(fig_overall, use_container_width=True)
        
        st.markdown("---")
        st.subheader("Temperature Profile for Specific Step")
        
        if not selected_step_types_filter_lower:
            st.warning("Please select at least one step type in the sidebar filter to see detailed temperature profiles.")
            return

        stmt_steps_for_temp_profile = select(Step.id, Step.step_type, Step.cycle_number, Step.step_number).\
            where(Step.experiment_id == selected_experiment_id).\
            where(Step.step_type.in_(selected_step_types_filter_lower)).\
            order_by(Step.step_number)
        
        available_steps_for_temp_profile = session.exec(stmt_steps_for_temp_profile).all()

        if not available_steps_for_temp_profile:
            st.info(f"No steps matching the selected types ({', '.join(selected_step_types_filter)}) found for detailed temperature profile.")
            return

        step_options_temp = {
            f"Step {s.step_number} (Cycle {s.cycle_number if s.cycle_number is not None else 'N/A'}) - {s.step_type.capitalize()}": s.id 
            for s in available_steps_for_temp_profile
        }
        
        selected_step_label_temp = st.selectbox(
            "Select Step for Temperature Profile", 
            options=list(step_options_temp.keys()),
            key="temp_profile_step_select",
            help="Select a specific step to view its detailed temperature vs. time profile. Filtered by 'Step Type' selection in the sidebar."
        )
        
        if selected_step_label_temp: # Should always be true if available_steps_for_temp_profile is not empty
            selected_step_id_temp = step_options_temp[selected_step_label_temp]

            stmt_measurements_temp = select(Measurement.step_time_s, Measurement.temperature_c).\
                where(Measurement.step_id == selected_step_id_temp).\
                where(Measurement.temperature_c.isnot(None)).\
                order_by(Measurement.step_time_s)
            
            measurements_temp_data = session.exec(stmt_measurements_temp).all()

            if measurements_temp_data:
                df_measurements_temp = pd.DataFrame(measurements_temp_data, columns=['step_time_s', 'temperature_c'])
                fig_step_temp = px.line(df_measurements_temp, x='step_time_s', y='temperature_c',
                                 title=f'Step Temperature vs. Step Time ({selected_step_label_temp})',
                                 labels={'step_time_s': 'Step Time (s)', 'temperature_c': 'Temperature (°C)'})
                fig_step_temp.update_layout(height=450)
                st.plotly_chart(fig_step_temp, use_container_width=True)
            else:
                st.info(f"No temperature data for the selected step: {selected_step_label_temp}. Check data or filters.")
        else: # Fallback, though selectbox usually has a default
             st.info("Select a step to view its temperature profile.")


def render_validation_tab():
    """Render the validation results tab content"""
    st.subheader("Data Validation Results")
    
    # Check if an experiment is selected
    selected_experiment_id = st.session_state.get("selected_experiment_id")
    
    if not selected_experiment_id:
        st.info("Please select an experiment from the sidebar or adjust filters to view validation results.")
        return
    
    with st.spinner("Loading validation report..."):
        # Get experiment data from database
        with get_session() as session:
            experiment = session.get(Experiment, selected_experiment_id)
            
            if not experiment:
                st.error("Selected experiment not found.")
                return
            
            # Check if validation results exist
            if experiment.validation_report is None:
                st.warning("No validation data available for this experiment.")
                return
            
            # Display experiment info with Cell and Machine details
        st.write(f"#### Experiment: {experiment.name}")
        st.write(f"Battery Type: {experiment.battery_type}")
        st.write(f"Nominal Capacity: {experiment.nominal_capacity} Ah")
        
        # Get cell and machine info if available
        if experiment.cell_id:
            cell = session.get(Cell, experiment.cell_id)
            if cell:
                cell_name_display = f"{cell.name}: " if cell.name else ""
                st.write(f"Cell: {cell_name_display}{cell.chemistry.value}, {cell.capacity} Ah, {cell.form.value}")
        
        if experiment.machine_id:
            machine = session.get(Machine, experiment.machine_id)
            if machine:
                machine_info = [f"Machine: {machine.name}"]
                if machine.model_number:
                    machine_info.append(f"Model: {machine.model_number}")
                st.write(" | ".join(machine_info))
        
        # Display validation status with appropriate icon
        if experiment.validation_status:
            st.success("All validation checks passed! ✅")
        else:
            st.warning("Validation found potential issues with the data. ⚠️")
        
        # Create expandable sections for validation details
        validation_report = experiment.validation_report
        
        # Extract and display step validation results
        with st.expander("Step Data Validation", expanded=not experiment.validation_status):
            step_validation = validation_report.get('step_validation', {})
            step_summary = step_validation.get('summary', {})
            
            if step_summary:
                # Create metrics for validation issues
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Issues", step_summary.get('total_issues', 0))
                with col2:
                    st.metric("Critical Issues", step_summary.get('critical_issues', 0))
                with col3:
                    st.metric("Warning Issues", step_summary.get('warning_issues', 0))
                
                # Display critical issues
                critical_issues = step_validation.get('issues_by_severity', {}).get('critical', [])
                if critical_issues:
                    st.markdown("##### Critical Issues:")
                    for issue in critical_issues:
                        st.error(f"**{issue.get('validation', '')}**: {issue.get('issue', '')}")
                
                # Display warnings
                warning_issues = step_validation.get('issues_by_severity', {}).get('warning', [])
                if warning_issues:
                    st.markdown("##### Warnings:")
                    for issue in warning_issues:
                        st.warning(f"**{issue.get('validation', '')}**: {issue.get('issue', '')}")
                
                # Display info issues
                info_issues = step_validation.get('issues_by_severity', {}).get('info', [])
                if info_issues:
                    st.markdown("##### Information:")
                    for issue in info_issues:
                        st.info(f"**{issue.get('validation', '')}**: {issue.get('issue', '')}")
            else:
                st.info("No step validation data available.")
        
        # Extract and display detail validation results
        with st.expander("Measurement Data Validation", expanded=not experiment.validation_status):
            detail_validation = validation_report.get('detail_validation', {})
            detail_summary = detail_validation.get('summary', {})
            
            if detail_summary:
                # Create metrics for validation issues
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Issues", detail_summary.get('total_issues', 0))
                with col2:
                    st.metric("Critical Issues", detail_summary.get('critical_issues', 0))
                with col3:
                    st.metric("Warning Issues", detail_summary.get('warning_issues', 0))
                
                # Display critical issues
                critical_issues = detail_validation.get('issues_by_severity', {}).get('critical', [])
                if critical_issues:
                    st.markdown("##### Critical Issues:")
                    for issue in critical_issues:
                        st.error(f"**{issue.get('validation', '')}**: {issue.get('issue', '')}")
                
                # Display warnings
                warning_issues = detail_validation.get('issues_by_severity', {}).get('warning', [])
                if warning_issues:
                    st.markdown("##### Warnings:")
                    for issue in warning_issues:
                        st.warning(f"**{issue.get('validation', '')}**: {issue.get('issue', '')}")
                
                # Display info issues
                info_issues = detail_validation.get('issues_by_severity', {}).get('info', [])
                if info_issues:
                    st.markdown("##### Information:")
                    for issue in info_issues:
                        st.info(f"**{issue.get('validation', '')}**: {issue.get('issue', '')}")
            else:
                st.info("No measurement validation data available.")
                
        # Add validation metadata
        with st.expander("Validation Metadata"):
            st.write(f"Validation Timestamp: {validation_report.get('timestamp', 'Not available')}")
            st.json(validation_report)