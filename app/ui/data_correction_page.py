import streamlit as st
from sqlalchemy.orm import Session
from app.models import Experiment, Step, Measurement # Assuming these are your SQLAlchemy models
from app.utils.database import get_session # MODIFIED: Import get_session

def show_data_correction_page():
    st.title("Data Correction")

    st.subheader("Select Table to Correct")
    table_to_correct = st.selectbox("Table", ["Experiment", "Step"], key="table_select")

    if table_to_correct == "Experiment":
        correct_experiment_data()
    elif table_to_correct == "Step":
        correct_step_data()

    # Placeholder for future tables
    # elif table_to_correct == "OtherTable":
    #     correct_other_table_data()

def correct_experiment_data():
    st.subheader("Correct Experiment Metadata")
    # session: Session = get_session() # Use the imported get_session directly
    with get_session() as session: # MODIFIED: Use context manager for session
        try:
            experiments = session.query(Experiment).all()
            experiment_ids = [exp.id for exp in experiments]
            
            if not experiment_ids:
                st.warning("No experiments found in the database.")
                return

            selected_experiment_id = st.selectbox("Select Experiment ID to Correct", experiment_ids, key="exp_id_select")
            
            if selected_experiment_id:
                experiment_to_edit = session.query(Experiment).filter(Experiment.id == selected_experiment_id).first()
                if experiment_to_edit:
                    st.write(f"Editing Experiment: {experiment_to_edit.name} (ID: {experiment_to_edit.id})") # MODIFIED: experiment_name to name
                    
                    # Example: Correcting experiment_name
                    # Add more fields as needed based on your Experiment model
                    new_experiment_name = st.text_input("New Experiment Name", value=experiment_to_edit.name, key=f"exp_name_{selected_experiment_id}") # MODIFIED: experiment_name to name
                    new_description = st.text_area("New Description", value=experiment_to_edit.description or "", key=f"exp_desc_{selected_experiment_id}")

                    if st.button("Save Experiment Changes", key=f"save_exp_{selected_experiment_id}"):
                        experiment_to_edit.name = new_experiment_name # MODIFIED: experiment_name to name
                        experiment_to_edit.description = new_description
                        # Update other fields here
                        try:
                            session.commit()
                            st.success(f"Experiment ID {selected_experiment_id} updated successfully!")
                            st.rerun() # MODIFIED: Changed to st.rerun()
                        except Exception as e:
                            session.rollback()
                            st.error(f"Error updating experiment: {e}")
                else:
                    st.error(f"Experiment with ID {selected_experiment_id} not found.")
        except Exception as e: # Catch potential errors during initial query or session handling
            st.error(f"An error occurred: {e}")

def correct_step_data():
    st.subheader("Correct Step Metadata")
    # session: Session = get_session() # Use the imported get_session directly
    with get_session() as session: # MODIFIED: Use context manager for session
        try:
            experiments = session.query(Experiment).all()
            experiment_names = {exp.id: exp.name for exp in experiments} # MODIFIED: experiment_name to name

            if not experiments:
                st.warning("No experiments found. Steps are associated with experiments.")
                return

            selected_exp_id_for_step = st.selectbox(
                "Select Experiment to view its Steps", 
                options=list(experiment_names.keys()), 
                format_func=lambda x: f"{experiment_names[x]} (ID: {x})",
                key="exp_for_step_select"
            )

            if selected_exp_id_for_step:
                steps = session.query(Step).filter(Step.experiment_id == selected_exp_id_for_step).all()
                step_details = {step.id: f"Step ID: {step.id}, Type: {step.step_type}, Number: {step.step_number}" for step in steps}

                if not steps:
                    st.warning(f"No steps found for Experiment ID {selected_exp_id_for_step}.")
                    return

                selected_step_id = st.selectbox(
                    "Select Step ID to Correct", 
                    options=list(step_details.keys()),
                    format_func=lambda x: step_details[x],
                    key="step_id_select"
                )

                if selected_step_id:
                    step_to_edit = session.query(Step).filter(Step.id == selected_step_id).first()
                    if step_to_edit:
                        st.write(f"Editing Step ID: {step_to_edit.id}")
                        
                        new_step_number = st.number_input("New Step Number", value=step_to_edit.step_number, key=f"step_num_{selected_step_id}", step=1)
                        new_step_type = st.text_input("New Step Type", value=step_to_edit.step_type, key=f"step_type_{selected_step_id}")
                        new_description = st.text_area("New Description", value=step_to_edit.description or "", key=f"step_desc_{selected_step_id}")

                        if st.button("Save Step Changes", key=f"save_step_{selected_step_id}"):
                            step_to_edit.step_number = int(new_step_number)
                            step_to_edit.step_type = new_step_type
                            step_to_edit.description = new_description
                            try:
                                session.commit()
                                st.success(f"Step ID {selected_step_id} updated successfully!")
                                st.rerun() # MODIFIED: Changed to st.rerun()
                            except Exception as e:
                                session.rollback()
                                st.error(f"Error updating step: {e}")
                    else:
                        st.error(f"Step with ID {selected_step_id} not found.")
        except Exception as e: # Catch potential errors during initial query or session handling
            st.error(f"An error occurred: {e}")

if __name__ == "__main__":
    show_data_correction_page()
