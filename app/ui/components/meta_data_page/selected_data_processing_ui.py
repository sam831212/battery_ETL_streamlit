"""UI related to processing data that might have been selected or prepared in a previous step/preview."""
import streamlit as st
import pandas as pd
from sqlmodel import desc, func, select
from datetime import datetime
import traceback

from app.etl import convert_numpy_types
from app.models import Cell, Experiment, Machine, Measurement, Step
from app.utils.data_helpers import convert_datetime_to_python
from app.utils.database import get_session as get_db_session
from app.services.database_service import save_measurements_to_db


def handle_selected_steps_save():
    """Handle saving selected steps to database"""
    if "selected_steps" not in st.session_state or len(st.session_state["selected_steps"]) == 0:
        st.error("No steps selected. Please select steps first.")
        return

    if not st.session_state.get("experiment_name"):
        st.error("Please fill in experiment information first.")
        return

    # Get experiment metadata from session state
    experiment_name = st.session_state["experiment_name"]
    nominal_capacity = st.session_state["nominal_capacity"]
    cell_id = st.session_state["selected_cell_id"]
    machine_id = st.session_state["selected_machine_id"]
    experiment_date = st.session_state["experiment_date"]
    operator = st.session_state["operator"]
    description = st.session_state.get("description", "")

    # Process selected steps
    with st.spinner("Processing selected steps..."):
        try:
            # Create connection to the database
            with get_db_session() as session:
                # Check if cell exists
                cell = session.query(Cell).filter(Cell.id == cell_id).first()
                if not cell:
                    st.error(f"Cell with ID {cell_id} not found. Please select a valid cell.")
                    return

                # Check if machine exists
                machine = session.query(Machine).filter(Machine.id == machine_id).first()
                if not machine:
                    st.error(f"Machine with ID {machine_id} not found. Please select a valid machine.")
                    return                # Get the transformed data if available, otherwise use the original selected steps
                if "steps_df_transformed" in st.session_state and st.session_state["steps_df_transformed"] is not None:
                    # Get selected step numbers and use the transformed dataframe
                    selected_step_numbers = [step["step_number"] for step in st.session_state["selected_steps"]]
                    print(f"[DEBUG] selected_step_numbers: {selected_step_numbers}")

                    # Map step numbers to indices in the transformed dataframe
                    transformed_df = st.session_state["steps_df_transformed"]
                    print(f"[DEBUG] transformed_df 包含 {len(transformed_df)} 個工步")
                    print(f"[DEBUG] transformed_df 工步編號: {sorted(transformed_df['step_number'].unique()) if 'step_number' in transformed_df.columns else 'No step_number column'}")
                    
                    # 檢查 pre_test_rest_time 欄位
                    if 'pre_test_rest_time' in transformed_df.columns:
                        non_null_count = transformed_df['pre_test_rest_time'].notna().sum()
                        print(f"[DEBUG] transformed_df 中 pre_test_rest_time 欄位存在，{non_null_count}/{len(transformed_df)} 個工步有值")
                        
                        # 顯示前幾個工步的 pre_test_rest_time 值
                        for _, row in transformed_df.head(10).iterrows():
                            print(f"[DEBUG] 工步 {row['step_number']}: pre_test_rest_time = {row['pre_test_rest_time']}")
                    else:
                        print(f"[DEBUG] 警告：transformed_df 中沒有 pre_test_rest_time 欄位！")
                        print(f"[DEBUG] transformed_df 欄位: {list(transformed_df.columns)}")
                    
                    if "step_number" in transformed_df.columns:
                        steps_df_to_use = transformed_df[transformed_df["step_number"].isin(selected_step_numbers)].copy()
                        print(f"[DEBUG] 過濾後的 steps_df_to_use 包含 {len(steps_df_to_use)} 個工步")
                        
                        # IMPORTANT: Merge data_meta from selected_steps into the transformed dataframe
                        # Create a mapping of step_number to data_meta from selected_steps
                        data_meta_mapping = {step["step_number"]: step.get("data_meta", "") for step in st.session_state["selected_steps"]}
                        
                        # Add data_meta column to the transformed dataframe
                        steps_df_to_use["data_meta"] = steps_df_to_use["step_number"].map(data_meta_mapping).fillna("")
                    else:
                        print(f"[DEBUG] 警告：transformed_df 中沒有 step_number 欄位，使用原始 selected_steps")
                        steps_df_to_use = pd.DataFrame(st.session_state["selected_steps"])
                else:
                    print(f"[DEBUG] 沒有 steps_df_transformed，使用原始 selected_steps")
                    steps_df_to_use = pd.DataFrame(st.session_state["selected_steps"])                # Calculate average temperature from transformed data
                temperature = 25.0  # Default value
                if "temperature" in steps_df_to_use.columns:
                    temperature = float(steps_df_to_use["temperature"].mean())

                # Get project_id from session state
                project_id = st.session_state.get("selected_project_id")
                print(f"[DEBUG] handle_selected_steps_save project_id: {project_id}")
                print(f"[DEBUG] session_state keys: {list(st.session_state.keys())}")

                # Create experiment metadata
                experiment = Experiment(
                    name=experiment_name,
                    start_date=experiment_date,                    
                    operator=operator,
                    description=description,
                    cell_id=cell_id,
                    machine_id=machine_id,
                    nominal_capacity=nominal_capacity,
                    battery_type=cell.chemistry,
                    temperature=temperature,
                    project_id=project_id  # Add project_id here
                )
                
                session.add(experiment)
                session.flush()  # Flush to get experiment ID
                
                # Verify experiment got a valid ID
                if experiment.id is None:
                    st.error("Error: Failed to create experiment in database")
                    session.rollback() # Rollback before returning
                    return

                # Process steps using transformed data
                steps = []

                print(f"[DEBUG] handle_selected_steps_save: 開始處理 {len(steps_df_to_use)} 個工步")
                
                for idx, row in steps_df_to_use.iterrows():
                    row_dict = convert_numpy_types(row.to_dict())
                    step_number = row_dict.get("step_number") if isinstance(row_dict, dict) else getattr(row, "step_number", None)
                    pre_test_rest_time_value = row_dict.get("pre_test_rest_time") if isinstance(row_dict, dict) else getattr(row, "pre_test_rest_time", None)
                    
                    # DEBUG: 印出每個工步的 pre_test_rest_time 值
                    print(f"[DEBUG] 工步 {step_number}: pre_test_rest_time = {pre_test_rest_time_value} (類型: {type(pre_test_rest_time_value)})")
                    
                    if isinstance(row_dict, dict):                        step = Step(
                            experiment_id=experiment.id,
                            step_number=row_dict.get("step_number"),
                            step_type=row_dict.get("step_type"),
                            original_step_type=row_dict.get("original_step_type"),
                            start_time=convert_datetime_to_python(row_dict.get("start_time")),
                            end_time=convert_datetime_to_python(row_dict.get("end_time")),
                            duration=row_dict.get("duration", 0.0),
                            voltage_start=row_dict.get("voltage_start", 0.0),
                            voltage_end=row_dict.get("voltage_end", 0.0),
                            current=row_dict.get("current", 0.0),
                            capacity=row_dict.get("capacity", 0.0),
                            energy=row_dict.get("energy", 0.0),
                            temperature_start=row_dict.get("temperature_start"),
                            temperature_end=row_dict.get("temperature_end"),
                            c_rate=row_dict.get("c_rate", 0.0),
                            soc_start=row_dict.get("soc_start"),
                            soc_end=row_dict.get("soc_end"),
                            pre_test_rest_time=row_dict.get("pre_test_rest_time"),
                            data_meta=row_dict.get("data_meta", {})
                        )
                    else:                        step = Step(
                            experiment_id=experiment.id,
                            step_number=getattr(row, "step_number", None),
                            step_type=getattr(row, "step_type", None),
                            original_step_type=getattr(row, "original_step_type", None),
                            start_time=convert_datetime_to_python(getattr(row, "start_time", None)),
                            end_time=convert_datetime_to_python(getattr(row, "end_time", None)),
                            duration=getattr(row, "duration", 0.0),
                            voltage_start=getattr(row, "voltage_start", 0.0),
                            voltage_end=getattr(row, "voltage_end", 0.0),
                            current=getattr(row, "current", 0.0),
                            capacity=getattr(row, "capacity", 0.0),
                            energy=getattr(row, "energy", 0.0),
                            temperature_start=getattr(row, "temperature_start", None),
                            temperature_end=getattr(row, "temperature_end", None),
                            c_rate=getattr(row, "c_rate", 0.0),
                            soc_start=getattr(row, "soc_start", None),
                            soc_end=getattr(row, "soc_end", None),
                            pre_test_rest_time=getattr(row, "pre_test_rest_time", None),
                            data_meta=getattr(row, "data_meta", {})
                        )
                    
                    # DEBUG: 印出 Step 物件建立後的 pre_test_rest_time 值
                    print(f"[DEBUG] Step 物件 {step.step_number}: pre_test_rest_time = {step.pre_test_rest_time}")
                    
                    session.add(step)
                    steps.append(step)
                # Flush to ensure step IDs are assigned before creating mapping
                session.flush()
                
                # Create step ID mapping
                step_mapping = {step.step_number: step.id for step in steps}
                
                # Verify all steps have valid IDs
                invalid_steps = [step.step_number for step in steps if step.id is None]
                if invalid_steps:
                    st.error(f"Error: Steps {invalid_steps} did not receive valid database IDs")
                    session.rollback() # Rollback before returning
                    return
                
                # Commit Experiment and Steps before processing measurements
                try:
                    session.commit() 
                    st.info(f"Experiment '{experiment.name}' and {len(steps)} steps initially saved with ID {experiment.id}.")
                except Exception as e:
                    st.error(f"Error committing experiment and steps: {str(e)}")
                    session.rollback()
                    st.exception(e)
                    return

                print(f"DEBUG: Created step mapping: {step_mapping}")
                
                # Process measurement data if available
                if "selected_steps_details_df" in st.session_state and st.session_state["selected_steps_details_df"] is not None:
                    details_df = st.session_state["selected_steps_details_df"]

                    # Get transformed details if available
                    if "details_df_transformed" in st.session_state and st.session_state["details_df_transformed"] is not None:
                        # Filter to only include selected steps
                        selected_step_numbers = steps_df_to_use["step_number"].unique()
                        details_df = st.session_state["details_df_transformed"][
                            st.session_state["details_df_transformed"]["step_number"].isin(selected_step_numbers)
                        ]

                    # Use the improved save_measurements_to_db function instead of inline processing
                    print(f"DEBUG: About to save {len(details_df)} measurements using save_measurements_to_db")
                    print(f"DEBUG: Step mapping: {step_mapping}")
                    print(f"DEBUG: Available step numbers in details: {sorted(details_df['step_number'].unique()) if 'step_number' in details_df.columns else 'No step_number column'}")
                      # Import and use the proven save_measurements_to_db function
                    # from app.services.database_service import save_measurements_to_db # Moved to top
                    # from sqlmodel import select, func # Moved to top
                    
                    try:
                        with st.spinner(f"Processing {len(details_df)} measurements..."):
                            # Count existing measurements before (using the current session, which is now in a new transaction)
                            existing_count = 0
                            for step_id in step_mapping.values():
                                count = session.exec(
                                    select(func.count(Measurement.id)).where(Measurement.step_id == step_id)
                                ).one()
                                existing_count += count
                            
                            save_measurements_to_db(
                                experiment_id=experiment.id, # experiment.id is available after the commit
                                details_df=details_df,
                                step_mapping=step_mapping,
                                nominal_capacity=nominal_capacity
                            )
                            
                            # Post-processing verification: Count actual measurements saved
                            actual_count = 0
                            for step_id in step_mapping.values():
                                count = session.exec(
                                    select(func.count(Measurement.id)).where(Measurement.step_id == step_id)
                                ).one()
                                actual_count += count
                            
                            new_measurements = actual_count - existing_count
                            
                            if new_measurements > 0:
                                print(f"Successfully processed measurements using save_measurements_to_db")
                                st.success(f"Successfully saved {new_measurements} new measurements to database (Total: {actual_count})")
                            else:
                                st.warning(f"⚠️ No new measurements were saved to database. Expected: {len(details_df)}, Actual: 0")
                                print(f"WARNING: Expected {len(details_df)} measurements but 0 were saved")
                                
                    except Exception as e:
                        error_msg = str(e)
                        print(f"Error in save_measurements_to_db: {error_msg}")
                        
                        # Show specific error messages based on error type
                        if "database is locked" in error_msg:
                            st.error("❌ Database is locked. This might be due to concurrent operations. The system attempted retries. Please try again later if the issue persists.")
                        elif "step_id" in error_msg and "None" in error_msg: # This condition might need review based on database_service changes
                            st.error("❌ Data validation failed: Invalid step mapping detected during measurement processing. Please check your data.")
                        else:
                            st.error(f"❌ Error saving measurements: {error_msg}")
                            
                        import traceback
                        traceback.print_exc()
                        return  # Don't proceed with saving file records if measurement saving failed

                # Generate unique file hashes with timestamp to avoid duplicates
                timestamp_str = datetime.now().strftime("%Y%m%d%H%M%S%f")
                step_file_hash = f"selected_steps_{timestamp_str}"
                detail_file_hash = f"selected_details_{timestamp_str}"


                # Update experiment temperature based on all measurements
                # For now, skip the temperature average calculation to avoid join complexity
                # It will be calculated based on step data instead
                if len(steps) > 0:
                    step_temps = []
                    for step in steps:
                        if hasattr(step, 'temperature_start') and step.temperature_start is not None:
                            step_temps.append(step.temperature_start)
                        if hasattr(step, 'temperature_end') and step.temperature_end is not None:
                            step_temps.append(step.temperature_end)
                    if step_temps:
                        experiment.temperature = sum(step_temps) / len(step_temps)
                # Commit the changes (temp_avg updates)
                session.commit()

                st.success(f"""
                Successfully saved experiment '{experiment_name}' with {len(steps)} steps.
                
                You can view the results in the dashboard or add more data.
                """)

                # Clear session state for processed data
                st.session_state.pop("selected_steps", None)

        except Exception as e:
            st.error(f"Error saving data to database: {str(e)}")
            # Avoid explicit rollback here if session context manager handles it
            st.exception(e)


def render_preview_data_section():
    """Render UI section for data from preview page"""
    if "selected_steps" not in st.session_state:
        st.info("No data available from Step Selection. Please select steps first.")
        return

    # Show preview of selected steps
    st.header("Data from Step Selection")
    st.success(f"{len(st.session_state['selected_steps'])} steps selected from Step Selection.")

    # Display info about the steps
    if len(st.session_state["selected_steps"]) > 0:
        step_numbers = [step["step_number"] for step in st.session_state["selected_steps"]]
        step_types = set([step["step_type"] for step in st.session_state["selected_steps"]])

        st.info(f"""
        Selected Steps: {', '.join(str(s) for s in sorted(step_numbers))}
        Step Types: {', '.join(sorted(step_types))}
        """)

    # Add a button to process the selected steps
    if st.button("Process Selected Steps", type="primary"):
        if not st.session_state.get("experiment_name"):
            st.error("Please fill in and save the experiment information before processing steps.")
        else:
            handle_selected_steps_save()