"""UI related to processing data that might have been selected or prepared in a previous step/preview."""




import pandas as pd
from sqlmodel import desc, func
from datetime import datetime
import streamlit as st

from app.etl import convert_numpy_types
from app.models import Cell, Experiment, Machine, Measurement, ProcessedFile, Step
from app.utils.data_helpers import convert_datetime_to_python
from app.utils.database import get_session as get_db_session


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
                    return

                # Get the transformed data if available, otherwise use the original selected steps
                if "steps_df_transformed" in st.session_state and st.session_state["steps_df_transformed"] is not None:
                    # Get selected step numbers and use the transformed dataframe
                    selected_step_numbers = [step["step_number"] for step in st.session_state["selected_steps"]]

                    # Map step numbers to indices in the transformed dataframe
                    transformed_df = st.session_state["steps_df_transformed"]
                    if "step_number" in transformed_df.columns:
                        steps_df_to_use = transformed_df[transformed_df["step_number"].isin(selected_step_numbers)]
                    else:
                        steps_df_to_use = pd.DataFrame(st.session_state["selected_steps"])
                else:
                    steps_df_to_use = pd.DataFrame(st.session_state["selected_steps"])

                # Calculate average temperature from transformed data
                temperature_avg = 25.0  # Default value
                if "temperature_avg" in steps_df_to_use.columns:
                    temperature_avg = float(steps_df_to_use["temperature_avg"].mean())

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
                    temperature_avg=temperature_avg
                )

                session.add(experiment)
                session.flush()  # Flush to get experiment ID

                # Process steps using transformed data
                steps = []

                for _, row in steps_df_to_use.iterrows():
                    row_dict = convert_numpy_types(row.to_dict())

                    # 轉換日期時間
                    start_time = convert_datetime_to_python(row_dict.get("start_time"))
                    end_time = convert_datetime_to_python(row_dict.get("end_time"))

                    # Create Step with all the available data including SOC and temperature metrics
                    step = Step(
                        experiment_id=experiment.id,
                        step_number=row_dict["step_number"],
                        step_type=row_dict["step_type"],
                        start_time=start_time,
                        end_time=end_time,
                        duration=row_dict.get("duration", 0.0),
                        voltage_start=row_dict.get("voltage_start", 0.0),
                        voltage_end=row_dict.get("voltage_end", 0.0),
                        current=row_dict.get("current", 0.0),
                        capacity=row_dict.get("capacity", 0.0),
                        energy=row_dict.get("energy", 0.0),
                        temperature_avg=row_dict.get("temperature_avg", 25.0),
                        temperature_min=row_dict.get("temperature_min", 25.0),
                        temperature_max=row_dict.get("temperature_max", 25.0),
                        c_rate=row_dict.get("c_rate", 0.0),
                        soc_start=row_dict.get("soc_start"),
                        soc_end=row_dict.get("soc_end"),
                        ocv=row_dict.get("ocv")
                    )
                    session.add(step)
                    steps.append(step)

                # Create step ID mapping
                step_mapping = {step.step_number: step.id for step in steps}

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

                    # Save measurements to database
                    batch_size = 1000  # Use a batch size to avoid memory issues
                    detail_df_len = len(details_df)

                    with st.spinner(f"Processing {detail_df_len} measurements..."):
                        for i in range(0, detail_df_len, batch_size):
                            batch = details_df.iloc[i:min(i+batch_size, detail_df_len)]
                            measurements = []

                            for _, row in batch.iterrows():
                                row_dict = convert_numpy_types(row.to_dict())
                                step_number = row_dict.get("step_number")
                                step_id = step_mapping.get(step_number)

                                if step_id is not None:
                                    # 確保 execution_time 有值
                                    execution_time = row_dict.get("execution_time")
                                    if execution_time is None or pd.isna(execution_time):
                                        # 嘗試使用替代列
                                        execution_time = row_dict.get("execution_time_alt")
                                        if execution_time is None or pd.isna(execution_time):
                                            execution_time = 0.0

                                    # 確保所有數值欄位都是有效的浮點數
                                    voltage = row_dict.get("voltage", 0.0)
                                    if pd.isna(voltage):
                                        voltage = 0.0

                                    current = row_dict.get("current", 0.0)
                                    if pd.isna(current):
                                        current = 0.0

                                    temperature = row_dict.get("temperature", 25.0)
                                    if pd.isna(temperature):
                                        temperature = 25.0

                                    capacity = row_dict.get("capacity", 0.0)
                                    if pd.isna(capacity):
                                        capacity = 0.0

                                    energy = row_dict.get("energy", 0.0)
                                    if pd.isna(energy):
                                        energy = 0.0

                                    soc = row_dict.get("soc")
                                    if pd.isna(soc):
                                        soc = None

                                    try:
                                        measurement = Measurement(
                                            step_id=step_id,
                                            execution_time=float(execution_time),
                                            voltage=float(voltage),
                                            current=float(current),
                                            temperature=float(temperature),
                                            capacity=float(capacity),
                                            energy=float(energy),
                                            soc=soc
                                        )
                                        measurements.append(measurement)
                                    except Exception as e:
                                        print(f"Error creating measurement: {str(e)}")

                            # Add batch of measurements
                            if measurements:
                                try:
                                    session.add_all(measurements)
                                    session.flush()
                                    print(f"Saved batch of {len(measurements)} measurements")
                                except Exception as e:
                                    session.rollback()
                                    print(f"Error saving batch of measurements: {str(e)}")
                                    st.error(f"Error saving measurements: {str(e)}")

                # Generate unique file hashes with timestamp to avoid duplicates
                timestamp_str = datetime.now().strftime("%Y%m%d%H%M%S%f")
                step_file_hash = f"selected_steps_{timestamp_str}"
                detail_file_hash = f"selected_details_{timestamp_str}"

                # Save processed file records with unique hashes
                session.add(ProcessedFile(
                    experiment_id=experiment.id,
                    filename="Selected steps from session",
                    file_type="step",
                    file_hash=step_file_hash,
                    row_count=len(steps),
                    data_meta={"source": "selected_steps", "timestamp": timestamp_str}
                ))

                if "selected_steps_details_df" in st.session_state and st.session_state["selected_steps_details_df"] is not None:
                    detail_df_len = len(st.session_state["selected_steps_details_df"])
                    session.add(ProcessedFile(
                        experiment_id=experiment.id,
                        filename="Selected details from session",
                        file_type="detail",
                        file_hash=detail_file_hash,
                        row_count=detail_df_len,
                        data_meta={"source": "selected_details", "timestamp": timestamp_str}
                    ))

                # Update experiment end time based on the last measurement
                if len(steps) > 0:
                    last_step = session.query(Step).filter(
                        Step.experiment_id == experiment.id
                    ).order_by(desc(Step.end_time)).first()

                    if last_step and last_step.end_time:
                        experiment.end_date = last_step.end_time

                # Update experiment temperature_avg based on all measurements
                avg_temp = session.query(func.avg(Measurement.temperature)).join(
                    Step, Measurement.step_id == Step.id
                ).filter(
                    Step.experiment_id == experiment.id
                ).scalar()

                if avg_temp:
                    experiment.temperature_avg = float(avg_temp)

                # Commit the changes
                session.commit()

                st.success(f"""
                Successfully saved experiment '{experiment_name}' with {len(steps)} steps.
                
                You can view the results in the dashboard or add more data.
                """)

                # Clear session state for processed data
                st.session_state.pop("selected_steps", None)

                # Provide navigation to the dashboard
                if st.button("Go to Dashboard", type="primary"):
                    st.session_state["current_page"] = "Dashboard"
                    st.rerun()

        except Exception as e:
            st.error(f"Error saving data to database: {str(e)}")
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