"""
UI helper functions
"""
import streamlit as st

def show_loading_spinner(duration: float = 0.5):
    """
    Show loading spinner for specified duration
    
    Args:
        duration: Duration in seconds
    """
    import time
    with st.spinner("Loading..."):
        time.sleep(duration)

def format_number(num: int) -> str:
    """
    Format number with thousand separators
    
    Args:
        num: Number to format
        
    Returns:
        Formatted string
    """
    return f"{num:,}"

def create_download_button(data, filename: str, label: str = "Download"):
    """
    Create a download button for data
    
    Args:
        data: Data to download
        filename: Name of file
        label: Button label
    """
    st.download_button(
        label=label,
        data=data,
        file_name=filename,
        mime="application/octet-stream"
    )
