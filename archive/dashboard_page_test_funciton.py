
# # function taken from dashboard_page.py, not use in main program
#  Additional functions for test compatibility, need to remove after testing
# def render_overview_tab():
#     """Render overview tab - wrapper for test compatibility"""
#     selected_experiment_id = st.session_state.get("selected_experiment_id")
    
#     if not selected_experiment_id:
#         st.info("Please select an experiment from the sidebar or adjust filters to view its overview.")
#         return
    
#     try:
#         with get_session() as session:
#             experiment = session.get(Experiment, selected_experiment_id)
#             if not experiment:
#                 st.error("Experiment not found.")
#                 return
            
#             # Get steps for this experiment
#             steps = session.exec(
#                 select(Step).where(Step.experiment_id == selected_experiment_id)
#             ).all()
            
#             if not steps:
#                 st.info("No discharge capacity data (from 'discharge' steps) available to display for this experiment.")
#                 return
            
#             # Calculate metrics - handle both real model and test mock attributes
#             discharge_steps = []
#             charge_steps = []
            
#             for s in steps:
#                 # Get capacity - handle both 'capacity' (real model) and 'capacity_ah' (test mock)
#                 step_capacity = getattr(s, 'capacity_ah', getattr(s, 'capacity', None))
#                 if s.step_type == "discharge" and step_capacity:
#                     discharge_steps.append((s, step_capacity))
#                 elif s.step_type == "charge" and step_capacity:
#                     charge_steps.append((s, step_capacity))
            
#             total_discharge_capacity = sum(capacity for _, capacity in discharge_steps) if discharge_steps else 0
#             total_charge_capacity = sum(capacity for _, capacity in charge_steps) if charge_steps else 0
            
#             # Cycle count - use cycle_number if available (test mock), otherwise approximate from step count
#             if discharge_steps and hasattr(discharge_steps[0][0], 'cycle_number'):
#                 cycle_count = len(set(getattr(s, 'cycle_number') for s, _ in discharge_steps if hasattr(s, 'cycle_number') and getattr(s, 'cycle_number') is not None))
#             else:
#                 cycle_count = len(discharge_steps)
            
#             # Efficiency calculation
#             efficiency = (total_discharge_capacity / total_charge_capacity * 100) if total_charge_capacity > 0 else 0
            
#             # Max temperature from measurements
#             max_temp = None
#             # Prepare step_ids for query
#             step_ids_for_query = [s.id for s, _ in discharge_steps + charge_steps]
            
#             if step_ids_for_query:
#                 try:
#                     # Try with temperature first (test mock attribute)
#                     max_temp_val_c = session.exec(
#                         select(func.max(Measurement.temperature)).where(
#                             col(Measurement.step_id).in_(step_ids_for_query)
#                         )
#                     ).one_or_none()
#                     if max_temp_val_c is not None:
#                         max_temp = max_temp_val_c
#                 except Exception:
#                     pass

#                 if max_temp is None:
#                     try:
#                         # Fallback to temperature (real model attribute)
#                         max_temp_val = session.exec(
#                             select(func.max(Measurement.temperature)).where(
#                                 col(Measurement.step_id).in_(step_ids_for_query)
#                             )
#                         ).one_or_none()
#                         if max_temp_val is not None:
#                             max_temp = max_temp_val
#                     except Exception:
#                         pass
#             # Display metrics
#             col1, col2, col3, col4 = st.columns(4)
            
#             with col1:
#                 st.metric("Total Discharge Capacity (Ah)", f"{total_discharge_capacity:.2f}" if total_discharge_capacity > 0 else "--")
            
#             with col2:
#                 st.metric("Cycle Count", str(cycle_count))
            
#             with col3:
#                 st.metric("Overall C/D Efficiency (%)", f"{efficiency:.2f}%" if efficiency > 0 else "0.00%")
            
#             with col4:
#                 st.metric("Max Temperature (°C)", f"{max_temp:.2f}" if max_temp is not None else "--")
            
#             # Plot discharge capacity
#             if discharge_steps:
#                 # Use cycle_number if available, otherwise step_number
#                 if hasattr(discharge_steps[0], 'cycle_number'):
#                     df_plot = pd.DataFrame([{
#                         'Cycle': getattr(s, 'cycle_number', i+1),
#                         'Discharge Capacity (Ah)': capacity
#                     } for i, (s, capacity) in enumerate(discharge_steps)])
                    
#                     fig = px.line(df_plot, x='Cycle', y='Discharge Capacity (Ah)', 
#                                 title='Discharge Capacity per Cycle')
#                 else:
#                     df_plot = pd.DataFrame([{
#                         'Step': s.step_number,
#                         'Discharge Capacity (Ah)': capacity
#                     } for s, capacity in discharge_steps])
                    
#                     fig = px.line(df_plot, x='Step', y='Discharge Capacity (Ah)', 
#                                 title='Discharge Capacity per Step')
                
#                 st.plotly_chart(fig, use_container_width=True)
#             else:
#                 st.info("No discharge capacity data (from 'discharge' steps) available to display for this experiment.")
                
#     except Exception as e:
#         st.error(f"Error loading overview data: {str(e)}")


# def render_capacity_tab():
#     """Render capacity tab - wrapper for test compatibility"""
#     selected_experiment_id = st.session_state.get("selected_experiment_id")
    
#     if not selected_experiment_id:
#         st.info("Please select an experiment from the sidebar or adjust filters to view capacity analysis.")
#         return
    
#     try:
#         with get_session() as session:
#             # Get discharge steps
#             discharge_steps = session.exec(
#                 select(Step).where(
#                     Step.experiment_id == selected_experiment_id,
#                     Step.step_type == "discharge"
#                 )
#             ).all()
            
#             # Extract capacity data - handle both 'capacity' and 'capacity_ah'
#             discharge_data = []
#             for s in discharge_steps:
#                 step_capacity = getattr(s, 'capacity_ah', getattr(s, 'capacity', None))
#                 if step_capacity is not None:
#                     # Use cycle_number if available, otherwise step_number
#                     x_value = getattr(s, 'cycle_number', s.step_number)
#                     discharge_data.append((x_value, step_capacity))
            
#             if not discharge_data:
#                 st.info("No discharge capacity data available for this experiment.")
#                 return
            
#             # Create dataframe and plot
#             x_label = 'Cycle' if hasattr(discharge_steps[0], 'cycle_number') else 'Step'
#             df = pd.DataFrame(discharge_data, columns=[x_label, 'Discharge Capacity (Ah)'])
            
#             if not df.empty:
#                 initial_capacity = df['Discharge Capacity (Ah)'].iloc[0]
#                 final_capacity = df['Discharge Capacity (Ah)'].iloc[-1]
#                 retention = (final_capacity / initial_capacity * 100) if initial_capacity > 0 else 0
                
#                 st.caption(f"Capacity retention: {retention:.1f}% (from {initial_capacity:.3f} Ah to {final_capacity:.3f} Ah)")
                
#                 fig = px.line(df, x=x_label, y='Discharge Capacity (Ah)', 
#                             title=f'Discharge Capacity vs {x_label}')
#                 st.plotly_chart(fig, use_container_width=True)
            
#     except Exception as e:
#         st.error(f"Error loading capacity data: {str(e)}")


# def render_voltage_tab():
#     """Render voltage tab - wrapper for test compatibility"""
#     selected_experiment_id = st.session_state.get("selected_experiment_id")
    
#     if not selected_experiment_id:
#         st.info("Please select an experiment from the sidebar or adjust filters to view voltage analysis.")
#         return
    
#     try:
#         with get_session() as session:
#             # Get steps for this experiment
#             steps = session.exec(
#                 select(Step).where(Step.experiment_id == selected_experiment_id)
#             ).all()
            
#             if not steps:
#                 st.warning("No steps available for this experiment.")
#                 return
            
#             # Step selection
#             step_options = [f"Step {s.step_number}: {s.step_type}" for s in steps]
#             selected_step_index = st.selectbox("Select a step to view voltage data:", 
#                                              range(len(step_options)), 
#                                              format_func=lambda x: step_options[x])
            
#             selected_step = steps[selected_step_index]
            
#             # Get measurements for selected step
#             measurements = session.exec(
#                 select(Measurement).where(Measurement.step_id == selected_step.id)
#             ).all()
            
#             if not measurements:
#                 st.warning(f"No measurement data available for {step_options[selected_step_index]}.")
#                 return
            
#             # Create voltage plot
#             df = pd.DataFrame([{
#                 'timestamp': m.execution_time,
#                 'voltage': m.voltage
#             } for m in measurements if m.voltage is not None])
            
#             if not df.empty:
#                 fig = px.line(df, x='timestamp', y='voltage', 
#                             title=f'Voltage vs Time - {step_options[selected_step_index]}')
#                 st.plotly_chart(fig, use_container_width=True)
#             else:
#                 st.warning("No voltage data available for the selected step.")
                
#     except Exception as e:
#         st.error(f"Error loading voltage data: {str(e)}")


# def render_temperature_tab():
#     """Render temperature tab - wrapper for test compatibility"""
#     selected_experiment_id = st.session_state.get("selected_experiment_id")
    
#     if not selected_experiment_id:
#         st.info("Please select an experiment from the sidebar or adjust filters to view temperature analysis.")
#         return
    
#     try:
#         with get_session() as session:
#             # Get steps for this experiment
#             steps = session.exec(
#                 select(Step).where(Step.experiment_id == selected_experiment_id)
#             ).all()
            
#             if not steps:
#                 st.info("No temperature data available for this experiment.")
#                 return
            
#             # Get temperature data from measurements - handle both real and mock data
#             step_ids = [s.id for s in steps]
#             measurements = session.exec(
#                 select(Measurement).where(col(Measurement.step_id).in_(step_ids))
#             ).all()
            
#             # Extract temperature data - handle both 'temperature' and 'temperature'
#             temp_measurements = []
#             for m in measurements:
#                 temp_value = getattr(m, 'temperature', getattr(m, 'temperature', None))
#                 if temp_value is not None:
#                     temp_measurements.append((m.execution_time, temp_value))
            
#             if temp_measurements:
#                 # Overall temperature plot
#                 df_temp = pd.DataFrame(temp_measurements, columns=['timestamp', 'temperature'])
                
#                 fig_overall = px.line(df_temp, x='timestamp', y='temperature',
#                                     title='Overall Temperature vs Time')
#                 st.plotly_chart(fig_overall, use_container_width=True)
#             else:
#                 st.info("No temperature data available for this experiment.")
#                 return
            
#             # Step-specific temperature analysis
#             if steps:
#                 step_options = [f"Step {s.step_number}: {s.step_type}" for s in steps]
#                 selected_step_index = st.selectbox("Select a step for detailed temperature analysis:", 
#                                                  range(len(step_options)), 
#                                                  format_func=lambda x: step_options[x])
                
#                 selected_step = steps[selected_step_index]
                
#                 step_measurements = session.exec(
#                     select(Measurement).where(Measurement.step_id == selected_step.id)
#                 ).all()
                
#                 # Extract step temperature data
#                 step_temp_data = []
#                 for m in step_measurements:
#                     temp_value = getattr(m, 'temperature', getattr(m, 'temperature', None))
#                     if temp_value is not None:
#                         step_temp_data.append((m.execution_time, temp_value))
                
#                 if step_temp_data:
#                     df_step = pd.DataFrame(step_temp_data, columns=['timestamp', 'temperature'])
                    
#                     fig_step = px.line(df_step, x='timestamp', y='temperature',
#                                      title=f'Temperature vs Time - {step_options[selected_step_index]}')
#                     st.plotly_chart(fig_step, use_container_width=True)
#                 else:
#                     st.info(f"No temperature measurements available for {step_options[selected_step_index]}.")
            
#     except Exception as e:
#         st.error(f"Error loading temperature data: {str(e)}")
