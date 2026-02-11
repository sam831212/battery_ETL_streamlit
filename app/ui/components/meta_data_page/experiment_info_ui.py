"""
Manages the UI for experiment metadata input
"""

import streamlit as st


from datetime import datetime


def save_experiment_metadata(
    experiment_name,
    nominal_capacity,
    selected_cell_id,
    experiment_date,
    operator,
    description,
    selected_machine_id,
    cells,
    machines
):
    """Save experiment metadata to session state"""
    # Validate required fields
    if not experiment_name:
        st.error("Experiment name is required")
        return False

    if not selected_cell_id:
        st.error("Cell selection is required")
        return False

    if not selected_machine_id:
        st.error("Machine selection is required")
        return False

    if not operator:
        st.error("Operator name is required")
        return False

    # Save to session state
    st.session_state["experiment_name"] = experiment_name
    st.session_state["nominal_capacity"] = nominal_capacity
    st.session_state["selected_cell_id"] = selected_cell_id
    st.session_state["experiment_date"] = experiment_date
    st.session_state["operator"] = operator
    st.session_state["description"] = description
    st.session_state["selected_machine_id"] = selected_machine_id

    # Get cell and machine info
    selected_cell = None
    for cell in cells:
        if cell.id == selected_cell_id:
            selected_cell = cell
            break

    selected_machine = None
    for machine in machines:
        if machine.id == selected_machine_id:
            selected_machine = machine
            break

    # Display success message with details
    if selected_cell and selected_machine:
        st.success(f"""
        Experiment information saved:
        - Name: {experiment_name}
        - Cell: {selected_cell.name or f'Cell {selected_cell.id}'} ({selected_cell.chemistry.value})
        - Machine: {selected_machine.name or f'Machine {selected_machine.id}'}
        - Nominal Capacity: {nominal_capacity} Ah
        - Date: {experiment_date}
        - Operator: {operator}
        """)
    else:
        st.success("Experiment information saved.")

    return True


def render_experiment_metadata(cells, machines, has_data_from_preview, projects):
    """Render experiment metadata form"""
    # Create form for experiment metadata
    st.header("Experiment Information")

    with st.form("experiment_metadata_form"):
        # Project selection
        project_id = None
        if projects:
            project_options = {p.id: p.name for p in projects}
            project_id = st.selectbox(
                "Project",
                options=list(project_options.keys()),
                format_func=lambda x: project_options.get(x, "Unknown"),
                index=0 if st.session_state.get("selected_project_id") is None else
                      list(project_options.keys()).index(st.session_state["selected_project_id"])
                      if st.session_state.get("selected_project_id") in project_options else 0,
                help="Select the project for this experiment"
            )
            st.session_state["selected_project_id"] = project_id

        # Basic metadata
        experiment_name = st.text_input(
            "Experiment Name*",
            key="experiment_name_input",
            value=st.session_state.get("experiment_name", ""),
            help="A unique name for this experiment"
        )

        # Cell selection
        cell_options = {cell.id: f"{cell.name or 'Cell '+str(cell.id)} ({cell.chemistry.value}, {cell.capacity} Ah)" for cell in cells}

        if not cell_options:
            st.warning("No cells available. Please add a cell first.")
            selected_cell_id = None
        else:
            selected_cell_id = st.selectbox(
                "Select Cell*",
                options=list(cell_options.keys()),
                format_func=lambda x: cell_options.get(x, "Unknown"),
                index=0 if st.session_state.get("selected_cell_id") is None else
                      list(cell_options.keys()).index(st.session_state["selected_cell_id"])
                      if st.session_state.get("selected_cell_id") in cell_options else 0,
                help="The cell used in this experiment"
            )

        # Machine selection
        machine_options = {machine.id: f"{machine.name or 'Machine '+str(machine.id)}"
                          for machine in machines}

        if not machine_options:
            st.warning("No machines available. Please add a machine first.")
            selected_machine_id = None
        else:
            selected_machine_id = st.selectbox(
                "Select Machine*",
                options=list(machine_options.keys()),
                format_func=lambda x: machine_options.get(x, "Unknown"),
                index=0 if st.session_state.get("selected_machine_id") is None else
                      list(machine_options.keys()).index(st.session_state["selected_machine_id"])
                      if st.session_state.get("selected_machine_id") in machine_options else 0,
                help="The machine used for testing"
            )

        # Get the selected cell to use its nominal capacity as default
        selected_cell = None
        if selected_cell_id:
            for cell in cells:
                if cell.id == selected_cell_id:
                    selected_cell = cell
                    break

        # Nominal capacity
        nominal_capacity = st.number_input(
            "Nominal Capacity (Ah)*",
            min_value=0.001,
            value=float(st.session_state.get("nominal_capacity",
                                            selected_cell.capacity if selected_cell else 1.0)),
            help="The nominal capacity of the battery used for normalization"
        )

        # Additional metadata
        col1, col2 = st.columns(2)

        with col1:
            experiment_date = st.date_input(
                "Experiment Date*",
                value=st.session_state.get("experiment_date", datetime.now().date()),
                help="The date when the experiment was conducted"
            )

        with col2:
            operator = st.text_input(
                "Operator*",
                value=st.session_state.get("operator", ""),
                help="The person who conducted the experiment"
            )

        # Description
        description = st.text_area(
            "Description",
            value=st.session_state.get("description", ""),
            help="Additional notes about the experiment"
        )

        # Submit button
        submit_button = st.form_submit_button("Save Experiment Information")

        if submit_button:
            # Save metadata to session state
            save_experiment_metadata(
                experiment_name,
                nominal_capacity,
                selected_cell_id,
                experiment_date,
                operator,
                description,
                selected_machine_id,
                cells,
                machines
            )