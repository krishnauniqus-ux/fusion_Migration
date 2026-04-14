"""
template_tab.py - Template tab - EXACT from vnew.py
"""
import streamlit as st
import pandas as pd
import io
from core.models import ColumnRule, FileData
from utils.file_utils import detect_file_type, get_header_preview, auto_detect_header, read_uploaded_file, _get_excel_engine
from utils.tab_helpers import _refresh_template_data

def render_template_tab():
    # File Upload
    uploaded = st.file_uploader(
        "Upload Template (Excel or CSV)",
        type=['csv', 'xlsx', 'xls', 'xlsm'],
        key='template_upload',
        help="Upload your template file with the desired column structure"
    )

    if uploaded:
        # Store raw file for re-reading with different headers
        file_bytes = uploaded.getvalue()

        # Check if new file
        if st.session_state.template_file.name != uploaded.name:
            # First, get all available sheet names
            try:
                file_type = detect_file_type(uploaded.name)
                if file_type == 'excel':
                    engine = _get_excel_engine(file_bytes, uploaded.name)
                    excel_file = pd.ExcelFile(io.BytesIO(file_bytes), engine=engine)
                    all_available_sheets = excel_file.sheet_names
                else:
                    all_available_sheets = ['Sheet1']  # CSV only has one sheet
            except:
                all_available_sheets = []
            
            st.session_state.template_file = FileData(
                name=uploaded.name,
                raw_data=file_bytes,
                all_sheets=all_available_sheets
            )
            # Auto-read to get available sheets only
            _refresh_template_data()

        # Simple Configuration - Auto-detect everything
        st.markdown('<div class="section-container">', unsafe_allow_html=True)

        # Only show sheet selector if multiple sheets
        if len(st.session_state.template_file.sheets) > 1:
            selected_sheet = st.selectbox(
                "📄 Select Sheet",
                st.session_state.template_file.sheets,
                index=(
                    st.session_state.template_file.sheets.index(
                        st.session_state.template_file.selected_sheet
                    )
                    if (
                        st.session_state.template_file.selected_sheet
                        and st.session_state.template_file.selected_sheet
                            in st.session_state.template_file.sheets
                    )
                    else 0
                ),
                key='template_sheet_select'
            )
            if selected_sheet != st.session_state.template_file.selected_sheet:
                st.session_state.template_file.selected_sheet = selected_sheet
        elif st.session_state.template_file.sheets:
            st.session_state.template_file.selected_sheet = st.session_state.template_file.sheets[0]

        selected_sheet = st.session_state.template_file.selected_sheet

        if selected_sheet and st.session_state.template_file.raw_data:
            try:
                file_type = detect_file_type(st.session_state.template_file.name)
                raw_prev = get_header_preview(
                    st.session_state.template_file.raw_data,
                    file_type,
                    selected_sheet,
                    max_rows=8,
                    file_name=st.session_state.template_file.name
                )

                if raw_prev is not None and len(raw_prev) > 0:
                    # Auto-detect header row
                    detected = auto_detect_header(raw_prev)
                    
                    # Simple expander for advanced users
                    with st.expander("⚙️ Advanced: Change Header Row", expanded=False):
                        st.dataframe(raw_prev.fillna(""), use_container_width=True, height=180)
                        max_rows = len(raw_prev) - 1 if len(raw_prev) > 1 else 10
                        header_row = st.number_input(
                            "Header row (0 = first row)",
                            min_value=0,
                            max_value=max(10, max_rows),
                            value=detected,
                            key='template_header_row'
                        )
                    
                    # Use detected header row if expander is closed
                    if 'template_header_row' not in st.session_state:
                        header_row = detected
                    else:
                        header_row = st.session_state.template_header_row

                    # Single Load button
                    if st.button(f"✅ Load Template", type="primary", use_container_width=True, key='load_template_btn'):
                        try:
                            with st.spinner("Loading..."):
                                st.session_state.template_file.header_row = int(header_row)
                                _refresh_template_data()
                                
                                df_check = st.session_state.template_file.data.get(selected_sheet, pd.DataFrame())
                                if len(df_check.columns) == 0:
                                    st.error(f"❌ No valid columns found")
                                else:
                                    st.success(f"✅ Loaded {len(df_check.columns)} columns")
                                    st.rerun()
                        except Exception as e:
                            st.error(f"❌ Error: {str(e)}")

            except Exception as e:
                st.error(f"❌ Error: {e}")

        st.markdown('</div>', unsafe_allow_html=True)

        # Show loaded data
        if st.session_state.template_file.selected_sheet:
            df = st.session_state.template_file.data.get(
                st.session_state.template_file.selected_sheet,
                pd.DataFrame()
            )

            if len(df.columns) > 0:
                st.markdown('<div class="section-container">', unsafe_allow_html=True)
                
                # Simple sheet switcher
                if len(st.session_state.template_file.all_sheets) > 1:
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        new_sheet = st.selectbox(
                            "📄 Switch Sheet",
                            st.session_state.template_file.all_sheets,
                            index=st.session_state.template_file.all_sheets.index(st.session_state.template_file.selected_sheet) if st.session_state.template_file.selected_sheet in st.session_state.template_file.all_sheets else 0,
                            key='template_sheet_changer'
                        )
                    with col2:
                        st.markdown("<br>", unsafe_allow_html=True)
                        if new_sheet != st.session_state.template_file.selected_sheet:
                            if st.button("🔄", key='switch_template_sheet', use_container_width=True):
                                st.session_state.template_file.selected_sheet = new_sheet
                                _refresh_template_data()
                                st.rerun()

                st.metric("✅ Valid Columns", len(df.columns))
                
                if len(df.columns) == 0:
                    st.error("❌ No valid columns found")
                else:
                    with st.expander("📋 View Columns", expanded=False):
                        cols_list = list(df.columns)
                        for i in range(0, len(cols_list), 4):
                            cols = st.columns(4)
                            for j, col in enumerate(cols_list[i:i+4]):
                                with cols[j]:
                                    st.markdown(f"<code>{col}</code>", unsafe_allow_html=True)

                st.markdown('</div>', unsafe_allow_html=True)

                # Initialize column rules if not present (needed for mapping)
                for col in df.columns:
                    if col not in st.session_state.column_rules:
                        st.session_state.column_rules[col] = ColumnRule(column_name=col)

                # Mark step as complete
                if 'template_file' not in st.session_state.completed_steps:
                    st.session_state.completed_steps.add('template_file')
                    
                st.success("✅ Template loaded successfully!")

        # Navigation button - always at bottom of tab
        st.markdown("---")
        if st.session_state.template_file.selected_sheet and len(st.session_state.template_file.data.get(st.session_state.template_file.selected_sheet, pd.DataFrame()).columns) > 0:
            if st.button("➡️ Proceed to Data Source", type="primary", use_container_width=True, key='btn_template_to_source'):
                st.session_state.active_tab = 1
                st.session_state.tab_change_requested = True
                st.rerun()
        else:
            st.info("ℹ️ Load template file to proceed")

# =============================================================================
# TAB 2: DATA SOURCE FILE UPLOAD - FIXED
# =============================================================================

