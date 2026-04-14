"""
Helper functions for tabs - EXACT from vnew.py
"""
import streamlit as st
import io
from utils.file_utils import read_uploaded_file

def _refresh_template_data():
    """Refresh template data from stored bytes with current header row setting"""
    if st.session_state.template_file.raw_data:
        raw = st.session_state.template_file.raw_data
        file_bytes = raw if isinstance(raw, bytes) else raw.getvalue()

        # BytesIO with .name so engine detection works for .xls / .xlsm / .xlsx
        file_obj = io.BytesIO(file_bytes)
        file_obj.name = st.session_state.template_file.name or ''

        data, sheets, columns = read_uploaded_file(
            file_obj,
            st.session_state.template_file.header_row,
            st.session_state.template_file.selected_sheet
        )
        st.session_state.template_file.data = data
        st.session_state.template_file.sheets = sheets
        st.session_state.template_file.columns = columns
        if sheets and st.session_state.template_file.selected_sheet not in sheets:
            st.session_state.template_file.selected_sheet = sheets[0] if sheets else None

def _refresh_source_data():
    """Refresh source data from stored bytes with current header row setting"""
    if st.session_state.source_file.raw_data:
        raw = st.session_state.source_file.raw_data
        file_bytes = raw if isinstance(raw, bytes) else raw.getvalue()

        file_obj = io.BytesIO(file_bytes)
        file_obj.name = st.session_state.source_file.name or ''

        data, sheets, columns = read_uploaded_file(
            file_obj,
            st.session_state.source_file.header_row,
            st.session_state.source_file.selected_sheet
        )
        st.session_state.source_file.data = data
        st.session_state.source_file.sheets = sheets
        st.session_state.source_file.columns = columns
        if sheets and st.session_state.source_file.selected_sheet not in sheets:
            st.session_state.source_file.selected_sheet = sheets[0] if sheets else None
