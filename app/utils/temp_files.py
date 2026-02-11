"""
Temporary file utilities for the Battery ETL Dashboard

This module provides utilities for handling temporary files during data processing.
"""
import os
import tempfile
import hashlib
import atexit
from typing import Tuple, Optional, BinaryIO, Generator, Any, Dict
import shutil
from contextlib import contextmanager
import streamlit as st


# Global registry to track temporary files created for the session
# This registry is initialized in streamlit_app.py


@contextmanager
def temp_file_from_upload(uploaded_file, suffix: Optional[str] = None) -> Generator[str, Any, None]:
    """
    Creates a temporary file from a Streamlit uploaded file object and
    manages its lifecycle with a context manager.
    
    Note: This function is maintained for backward compatibility but is not recommended
    for new code. Use create_session_temp_file instead, which persists throughout the session.
    
    Args:
        uploaded_file: Streamlit UploadedFile object
        suffix: Optional file extension (e.g., '.csv')
        
    Yields:
        Path to the temporary file
    """
    # Create a temporary file
    temp_fd, temp_path = tempfile.mkstemp(suffix=suffix)
    
    try:
        # Write the file data to the temporary file
        with os.fdopen(temp_fd, 'wb') as temp_file:
            temp_file.write(uploaded_file.getbuffer())
        
        # Yield the path for use in the with block
        yield temp_path
    finally:
        # Clean up the temporary file when done
        if os.path.exists(temp_path):
            os.remove(temp_path)


def create_session_temp_file(uploaded_file, file_key: Optional[str] = None, suffix: Optional[str] = None) -> str:
    """
    Creates a temporary file from a Streamlit uploaded file object that persists
    for the entire session. Files are tracked and cleaned up when the application exits.
    
    Args:
        uploaded_file: Streamlit UploadedFile object
        file_key: Optional key to identify the file in the registry. If not provided,
                 a key will be generated based on the file content hash.
        suffix: Optional file extension (e.g., '.csv')
        
    Returns:
        Path to the temporary file
    """
    # If no file key is provided, use the file name or content hash
    if file_key is None:
        file_key = calculate_file_hash_from_memory(uploaded_file.getbuffer())
        
    # Check if we already have this file in our registry
    if file_key in st.session_state.temp_files_registry:
        temp_path = st.session_state.temp_files_registry[file_key]
        # Verify the file still exists
        if os.path.exists(temp_path):
            return temp_path
    
    # Create a new temporary file in the system's temp directory
    temp_fd, temp_path = tempfile.mkstemp(suffix=suffix)
    
    # Write the file data to the temporary file
    with os.fdopen(temp_fd, 'wb') as temp_file:
        temp_file.write(uploaded_file.getbuffer())
    
    # Register the file for cleanup when the application exits
    st.session_state.temp_files_registry[file_key] = temp_path
    
    return temp_path


# Register a cleanup function to remove temporary files at exit
def cleanup_temp_files():
    """Remove all temporary files registered in the session state."""
    if "temp_files_registry" in st.session_state:
        for file_key, file_path in st.session_state.temp_files_registry.items():
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except Exception as e:
                    print(f"Error removing temporary file {file_path}: {e}")
                    
# Register the cleanup function
atexit.register(cleanup_temp_files)


def calculate_file_hash_from_memory(file_content) -> str:
    """
    Calculate MD5 hash of file content in memory.
    
    Args:
        file_content: File content as bytes-like object
        
    Returns:
        MD5 hash as a hexadecimal string
    """
    hash_md5 = hashlib.md5()
    hash_md5.update(file_content)
    return hash_md5.hexdigest()


def calculate_file_hash(file_path: str) -> str:
    """
    Calculate MD5 hash of a file.
    
    Args:
        file_path: Path to the file
        
    Returns:
        MD5 hash as a hexadecimal string
    """
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        # Read file in chunks to handle large files
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()