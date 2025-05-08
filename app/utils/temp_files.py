"""
Temporary file utilities for the Battery ETL Dashboard

This module provides utilities for handling temporary files during data processing.
"""
import os
import tempfile
import hashlib
from typing import Tuple, Optional, BinaryIO
import shutil
from contextlib import contextmanager


@contextmanager
def temp_file_from_upload(uploaded_file, suffix: Optional[str] = None) -> str:
    """
    Creates a temporary file from a Streamlit uploaded file object and
    manages its lifecycle with a context manager.
    
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