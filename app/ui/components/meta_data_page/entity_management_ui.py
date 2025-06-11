"""
Handles UI for managing database entities like Cells and Machines
"""
from app.models import Cell, Experiment, Machine
from app.models.database import CellChemistry, CellFormFactor, Project
from app.utils.database import get_session as get_db_session


import streamlit as st


def render_entity_management(
    entity_type,
    entity_class,
    header_text,
    form_fields,
    display_fields,
    reference_check=None,
):
    """
    Generic entity management UI component

    Args:
        entity_type: String name of the entity type (e.g., "cell", "machine")
        entity_class: The SQLModel class for the entity
        header_text: Text to display as the header
        form_fields: List of dictionaries defining form fields for adding entities
        display_fields: List of dictionaries mapping entity attributes to display names
        reference_check: Optional function to check if entity can be deleted
    """
    st.subheader(header_text)

    # Create columns - one for adding new entities, one for listing existing ones
    col1, col2 = st.columns(2)

    # Add new entity section
    with col1:
        st.write(f"#### Add New {entity_type.capitalize()}")
        # Use a form to collect input data
        with st.form(f"add_{entity_type}_form"):
            # Create the fields based on provided form_fields
            field_values = {}
            for field in form_fields:
                field_name = field["name"]
                field_type = field.get("type", "text")
                field_label = field.get("label", field_name.replace("_", " ").capitalize())
                field_options = field.get("options", None)
                field_default = field.get("default", None)

                # Create different input types based on field_type
                if field_type == "text":
                    field_values[field_name] = st.text_input(field_label, value=field_default or "")
                elif field_type == "number":
                    field_values[field_name] = st.number_input(field_label, value=field_default or 0.0)
                elif field_type == "select":
                    field_values[field_name] = st.selectbox(field_label, options=field_options, index=0 if field_default is None else field_options.index(field_default))
                elif field_type == "date":
                    field_values[field_name] = st.date_input(field_label, value=field_default)
                elif field_type == "textarea":
                    field_values[field_name] = st.text_area(field_label, value=field_default or "")

            # Add submit button
            submit_button = st.form_submit_button(f"Add {entity_type.capitalize()}")

        # Process form submission
        if submit_button:
            try:
                # Create entity object with form data
                entity_data = {}
                for field in form_fields:
                    field_name = field["name"]
                    field_value = field_values[field_name]

                    # Special handling for empty string values
                    if isinstance(field_value, str) and field_value.strip() == "":
                        field_value = None

                    entity_data[field_name] = field_value

                # Handle special case for Cell model backward compatibility
                if entity_type == "cell":
                    # Map from new fields to legacy fields
                    if "nominal_capacity" in entity_data:
                        entity_data["capacity"] = entity_data["nominal_capacity"]
                    if "form_factor" in entity_data:
                        entity_data["form"] = CellFormFactor(entity_data["form_factor"])

                new_entity = entity_class(**entity_data)

                # Save to database
                with get_db_session() as session:
                    session.add(new_entity)
                    session.commit()
                    session.refresh(new_entity)

                st.success(f"{entity_type.capitalize()} added successfully!")

            except Exception as e:
                st.error(f"Error adding {entity_type}: {str(e)}")

    # Display existing entities
    with col2:
        st.write(f"#### Existing {entity_type.capitalize()}s")

        with get_db_session() as session:
            # Get all entities
            entities = session.query(entity_class).all()

            if not entities:
                st.info(f"No {entity_type}s found. Add one using the form.")
            else:
                # Display as a table
                for entity in entities:
                    # 顯示 cell/machine/project name，若無則 fallback 為 #id
                    if entity_type == "cell":
                        display_title = getattr(entity, 'name', None) or f"#{entity.id}"
                        expander_title = f"{entity_type.capitalize()}: {display_title}"
                    elif entity_type == "machine":
                        display_title = getattr(entity, 'name', None) or f"#{entity.id}"
                        expander_title = f"{entity_type.capitalize()}: {display_title}"
                    elif entity_type == "project":
                        display_title = getattr(entity, 'name', None) or f"#{entity.id}"
                        expander_title = f"{entity_type.capitalize()}: {display_title}"
                    else:
                        expander_title = f"{entity_type.capitalize()} #{entity.id}"
                    with st.expander(expander_title):
                        # Display each field defined in display_fields
                        for field in display_fields:
                            attr_name = field["attr"]
                            display_name = field["display"]
                            # Get attribute value, handle nested attributes with dots
                            if "." in attr_name:
                                parts = attr_name.split(".")
                                value = entity
                                for part in parts:
                                    value = getattr(value, part, None)
                            else:
                                value = getattr(entity, attr_name, None)

                            st.write(f"**{display_name}:** {value}")

                        # 編輯功能
                        edit_key = f"edit_{entity_type}_{entity.id}"
                        if st.button(f"Edit {entity_type.capitalize()}", key=edit_key):
                            st.session_state[f"editing_{entity_type}_{entity.id}"] = True
                        if st.session_state.get(f"editing_{entity_type}_{entity.id}", False):
                            with st.form(f"edit_{entity_type}_form_{entity.id}"):
                                edit_values = {}
                                for field in form_fields:
                                    field_name = field["name"]
                                    field_type = field.get("type", "text")
                                    field_label = field.get("label", field_name.replace("_", " ").capitalize())
                                    field_options = field.get("options", None)
                                    # 取得現有值
                                    current_value = getattr(entity, field_name, None)
                                    if field_type == "text":
                                        edit_values[field_name] = st.text_input(field_label, value=current_value or "")
                                    elif field_type == "number":
                                        edit_values[field_name] = st.number_input(field_label, value=current_value or 0.0)
                                    elif field_type == "select":
                                        options = field_options or []
                                        index = options.index(current_value) if current_value in options else 0
                                        edit_values[field_name] = st.selectbox(field_label, options=options, index=index)
                                    elif field_type == "date":
                                        edit_values[field_name] = st.date_input(field_label, value=current_value)
                                    elif field_type == "textarea":
                                        edit_values[field_name] = st.text_area(field_label, value=current_value or "")
                                save_button = st.form_submit_button("Save")
                            if save_button:
                                try:
                                    for field in form_fields:
                                        field_name = field["name"]
                                        value = edit_values[field_name]
                                        if isinstance(value, str) and value.strip() == "":
                                            value = None
                                        setattr(entity, field_name, value)
                                    # Cell 特殊欄位處理
                                    if entity_type == "cell":
                                        if "nominal_capacity" in edit_values:
                                            entity.capacity = edit_values["nominal_capacity"]
                                        if "form_factor" in edit_values:
                                            entity.form = CellFormFactor(edit_values["form_factor"])
                                    session.commit()
                                    st.success(f"{entity_type.capitalize()} updated successfully!")
                                    st.session_state[f"editing_{entity_type}_{entity.id}"] = False
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error updating {entity_type}: {str(e)}")
                        # Add delete button
                        if st.button(f"Delete {entity_type.capitalize()}", key=f"delete_{entity_type}_{entity.id}"):
                            # Check if entity can be deleted
                            can_delete = True
                            message = ""

                            if reference_check:
                                can_delete, message = reference_check(session, entity.id)

                            if can_delete:
                                try:
                                    # Delete the entity
                                    session.delete(entity)
                                    session.commit()
                                    st.success(f"{entity_type.capitalize()} deleted successfully!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error deleting {entity_type}: {str(e)}")
                            else:
                                st.error(message)


def cell_reference_check(session, cell_id):
    """Check if a cell can be safely deleted"""
    # Check if cell is referenced in any experiments
    experiment_count = session.query(Experiment).filter(
        Experiment.cell_id == cell_id
    ).count()

    if experiment_count > 0:
        return False, f"Cannot delete cell: It is referenced by {experiment_count} experiments."

    return True, "Cell can be safely deleted."


def render_cell_management():
    """Render cell management UI"""
    form_fields = [
        {"name": "name", "type": "text", "label": "Cell Name"},
        {"name": "manufacturer", "type": "text", "label": "Manufacturer"},
        {"name": "chemistry", "type": "select", "label": "Chemistry",
         "options": [chemistry.value for chemistry in CellChemistry]},
        {"name": "form_factor", "type": "select", "label": "Form Factor",
         "options": [form_factor.value for form_factor in CellFormFactor]},
        {"name": "nominal_capacity", "type": "number", "label": "Nominal Capacity (Ah)"},
        {"name": "nominal_voltage", "type": "number", "label": "Nominal Voltage (V)"},
        {"name": "serial_number", "type": "text", "label": "Serial Number", "default": ""},
        {"name": "date_received", "type": "date", "label": "Date Received"},
        {"name": "notes", "type": "textarea", "label": "Notes", "default": ""}
    ]

    display_fields = [
        {"attr": "name", "display": "Name"},
        {"attr": "manufacturer", "display": "Manufacturer"},
        {"attr": "chemistry", "display": "Chemistry"},
        {"attr": "form_factor", "display": "Form Factor"},
        {"attr": "nominal_capacity", "display": "Nominal Capacity (Ah)"},
        {"attr": "nominal_voltage", "display": "Nominal Voltage (V)"},
        {"attr": "serial_number", "display": "Serial Number"},
        {"attr": "date_received", "display": "Date Received"},
        {"attr": "notes", "display": "Notes"}
    ]

    render_entity_management(
        entity_type="cell",
        entity_class=Cell,
        header_text="Cell Management",
        form_fields=form_fields,
        display_fields=display_fields,
        reference_check=cell_reference_check
    )


def machine_reference_check(session, machine_id):
    """Check if a machine can be safely deleted"""
    # Check if machine is referenced in any experiments
    experiment_count = session.query(Experiment).filter(
        Experiment.machine_id == machine_id
    ).count()

    if experiment_count > 0:
        return False, f"Cannot delete machine: It is referenced by {experiment_count} experiments."

    return True, "Machine can be safely deleted."


def render_machine_management():
    """Render machine management UI"""
    form_fields = [
        {"name": "name", "type": "text", "label": "Machine Name"},
        {"name": "description", "type": "textarea", "label": "Description", "default": ""},
        {"name": "model_number", "type": "text", "label": "Model Number", "default": ""}
    ]

    display_fields = [
        {"attr": "name", "display": "Name"},
        {"attr": "description", "display": "Description"},
        {"attr": "model_number", "display": "Model Number"}
    ]

    render_entity_management(
        entity_type="machine",
        entity_class=Machine,
        header_text="Machine Management",
        form_fields=form_fields,
        display_fields=display_fields,
        reference_check=machine_reference_check
    )


def render_project_management():
    """Render project management UI"""
    form_fields = [
        {"name": "name", "type": "text", "label": "Project Name"},
        {"name": "description", "type": "textarea", "label": "Description", "default": ""},
        {"name": "start_date", "type": "date", "label": "Start Date"},
        {"name": "end_date", "type": "date", "label": "End Date"}
    ]

    display_fields = [
        {"attr": "name", "display": "Name"},
        {"attr": "description", "display": "Description"},
        {"attr": "start_date", "display": "Start Date"},
        {"attr": "end_date", "display": "End Date"}
    ]

    render_entity_management(
        entity_type="project",
        entity_class=Project,
        header_text="Project Management",
        form_fields=form_fields,
        display_fields=display_fields
    )