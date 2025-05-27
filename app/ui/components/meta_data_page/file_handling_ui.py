"""UI for uploading user files and loading example files"""


import os

from typing import List, Tuple
import streamlit as st

from app.services.file_processing_service import get_file_data_and_metadata, handle_file_processing_pipeline
from app.services.validation_service import validate_files
from app.ui.componenets.data_display_ui import display_file_statistics, display_validation_results
from app.ui.exp_meta_data_page import EXAMPLE_FOLDER


def process_uploaded_files(step_file, detail_file):
    """Process uploaded files from user"""
    st.info("Both files uploaded. Processing...")

    try:
        # Get file data and metadata using the unified helper
        file_data = get_file_data_and_metadata(
            step_file,
            detail_file,
            is_example_file=False
        )

        # Display file statistics
        display_file_statistics(file_data['step_df'], file_data['detail_df'])

        # Validate files
        step_valid, detail_valid, step_missing, detail_missing, _, _ = validate_files(
            file_data['step_file_path'],
            file_data['detail_file_path']
        )

        # Show validation results
        display_validation_results(step_valid, detail_valid, step_missing, detail_missing)

        # Process button
        if st.button("Process Files", type="primary"):
            if not st.session_state.get("experiment_name"):
                st.error("Please fill in and save the experiment information before processing files.")
            elif not step_valid or not detail_valid:
                st.error("Please upload valid files with the required headers.")
            else:
                # Process the files using the unified pipeline
                with st.spinner("Processing files..."):
                    success = handle_file_processing_pipeline(file_data)

                    if success:
                        # Add a button to navigate to step selection
                        if st.button("Go to Step Selection", type="primary"):
                            st.session_state['current_page'] = "Step Selection"
                            st.rerun()

                        # Clear file uploaders
                        st.session_state["step_file"] = None
                        st.session_state["detail_file"] = None

    except Exception as e:
        st.error(f"Error processing files: {str(e)}")
        st.exception(e)


def render_file_upload_section():
    """Render UI section for regular file uploads"""
    # Create upload columns
    col1, col2 = st.columns(2)

    with col1:
        step_file = st.file_uploader(
            "Upload Step.csv",
            type=["csv"],
            help="CSV file containing step-level data",
            key="step_file",
        )

    with col2:
        detail_file = st.file_uploader(
            "Upload Detail.csv",
            type=["csv"],
            help="CSV file containing detailed measurement data",
            key="detail_file",
        )

    # Process files when both are uploaded
    if step_file and detail_file:
        process_uploaded_files(step_file, detail_file)


def process_loaded_example_files():
    """Process loaded example files"""
    # Replace with the new unified approach
    step_pair = st.session_state.get("selected_example_pair")
    if step_pair:
        base_name, step_file_path, detail_file_path = step_pair

        # Validate files
        step_valid, detail_valid, step_missing, detail_missing, _, _ = validate_files(
            step_file_path, detail_file_path
        )

        # Display validation results
        display_validation_results(step_valid, detail_valid, step_missing, detail_missing)

        # Process button
        if st.button("Process Example Files", type="primary"):
            if not st.session_state.get("experiment_name"):
                st.error("Please fill in and save the experiment information before processing files.")
            elif not step_valid or not detail_valid:
                st.error("Please select valid files with the required headers.")
            else:
                # Process the files using the unified pipeline
                with st.spinner("Processing example files..."):
                    # Get file data and metadata
                    file_data = get_file_data_and_metadata(
                        step_file_path,
                        detail_file_path,
                        is_example_file=True
                    )

                    # Process files using the unified pipeline
                    success = handle_file_processing_pipeline(file_data)

                    if success:
                        # Add a button to navigate to step selection
                        if st.button("Go to Step Selection", type="primary"):
                            st.session_state['current_page'] = "Step Selection"
                            st.rerun()

                        # Clear file session state
                        st.session_state["selected_example_pair"] = None


def find_example_file_pairs() -> List[Tuple[str, str, str]]:
    """
    Find matching step and detail file pairs in the example folder.

    Returns:
        List of tuples containing (base_name, step_file, detail_file)
    """
    example_step_files = [f for f in os.listdir(EXAMPLE_FOLDER) if f.endswith("_Step.csv")]
    example_detail_files = [f for f in os.listdir(EXAMPLE_FOLDER) if f.endswith("_Detail.csv")]

    example_pairs = []
    for step_file in example_step_files:
        base_name = step_file.replace("_Step.csv", "")
        detail_file = f"{base_name}_Detail.csv"
        if detail_file in example_detail_files:
            example_pairs.append((base_name, os.path.join(EXAMPLE_FOLDER, step_file), os.path.join(EXAMPLE_FOLDER, detail_file)))

    return example_pairs


def render_example_files_section():
    """Render UI section for example files"""
    # Find example file pairs
    example_pairs = find_example_file_pairs()

    if not example_pairs:
        st.error("No example files found in the example_csv_chromaLex folder.")
        return

    st.success(f"Found {len(example_pairs)} step and detail file pairs.")

    # Display dropdown to select file pair
    selected_pair = st.selectbox(
        "Select example file pair:",
        options=range(len(example_pairs)),
        format_func=lambda i: example_pairs[i][0]
    )

    base_name, step_file_path, detail_file_path = example_pairs[selected_pair]

    st.info(f"Selected files: {os.path.basename(step_file_path)} and {os.path.basename(detail_file_path)}")

    # Load the selected example files
    if st.button("Load Example Files", type="primary"):
        # Store the selected pair in session state
        st.session_state["selected_example_pair"] = example_pairs[selected_pair]

        st.success(f"Example files loaded: {os.path.basename(step_file_path)} and {os.path.basename(detail_file_path)}")
        st.info("Click 'Process Example Files' below to process these example files.")

        st.rerun()

    # Process example files if loaded
    if "selected_example_pair" in st.session_state:
        process_loaded_example_files()
