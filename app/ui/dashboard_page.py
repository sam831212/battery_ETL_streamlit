"""
Dashboard UI components for the Battery ETL Dashboard

This module provides UI components for visualizing and analyzing battery test data.
"""

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
            
            # Display Meta Data with Cell and Machine details
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