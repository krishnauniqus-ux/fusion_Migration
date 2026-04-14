"""
source_tab.py - Source tab - EXACT from vnew.py
"""
import streamlit as st
import pandas as pd
import io
from core.models import FileData
from utils.file_utils import detect_file_type, read_uploaded_file, _get_excel_engine
from utils.tab_helpers import _refresh_source_data
from utils.data_utils import filter_empty_and_generic_columns
from config.settings import CSV_CHUNK_LOAD_MIN_BYTES, CSV_READ_CHUNKSIZE

def render_source_tab():
    """Render Data Source File Upload Tab"""
    st.markdown('<div class="section-title">📤 Step 2: Upload Data Source File</div>', 
                unsafe_allow_html=True)

    st.markdown("""
    <div class="alert alert-info">
        <strong>Data Source File</strong> contains your raw data that needs to be 
        mapped and transformed to match the template structure.
    </div>
    """, unsafe_allow_html=True)

    # File Upload - Always visible
    st.markdown('<div class="section-container">', unsafe_allow_html=True)
    st.markdown("**📁 File Selection**")
    
    uploaded = st.file_uploader(
        "Choose your source data file",
        type=['csv', 'xlsx', 'xls', 'xlsm'],
        key='source_upload',
        help="Upload Excel or CSV file"
    )

    if uploaded:
        file_bytes = uploaded.getvalue()

        # Check if new file
        if st.session_state.source_file.name != uploaded.name:
            # First, get all available sheet names
            try:
                file_type = detect_file_type(uploaded.name)
                if file_type == 'excel':
                    excel_file = pd.ExcelFile(io.BytesIO(file_bytes))
                    all_available_sheets = excel_file.sheet_names
                else:
                    all_available_sheets = ['CSV']
            except:
                all_available_sheets = []
            
            st.session_state.source_file = FileData(
                name=uploaded.name,
                raw_data=file_bytes,
                all_sheets=all_available_sheets
            )
            st.session_state.source_file.data = {}
            st.session_state.source_file.columns = {}

        is_csv = uploaded.name.lower().endswith('.csv')

        # Sheet Selection - Always visible for Excel
        if not is_csv:
            try:
                xl = pd.ExcelFile(io.BytesIO(file_bytes))
                src_sheets = xl.sheet_names
                
                st.markdown("**� Sheet Selection**")
                if len(src_sheets) > 1:
                    chosen_s = st.selectbox(
                        "Select sheet to load",
                        src_sheets,
                        index=src_sheets.index(st.session_state.source_file.selected_sheet) 
                        if st.session_state.source_file.selected_sheet in src_sheets else 0,
                        key='source_sheet_select'
                    )
                else:
                    st.info(f"📄 Single sheet: {src_sheets[0]}")
                    chosen_s = src_sheets[0]
            except Exception as e:
                st.error(f"❌ Error reading file: {e}")
                st.markdown('</div>', unsafe_allow_html=True)
                return
        else:
            chosen_s = 'CSV'

        # Preview and Load Section
        st.markdown("**📊 Preview & Load**")
        
        try:
            # Show preview
            if is_csv:
                df_preview = pd.read_csv(io.BytesIO(file_bytes), nrows=5)
            else:
                # Use header row from session state or default to 0
                src_hdr = st.session_state.source_file.header_row if hasattr(st.session_state.source_file, 'header_row') else 0
                
                # Advanced header row option
                with st.expander("⚙️ Advanced: Change Header Row", expanded=False):
                    src_hdr = st.number_input("Header row (0 = first row)", 0, 10, src_hdr, key='source_header_row')
                
                src_engine = _get_excel_engine(file_bytes, uploaded.name)
                df_preview = pd.read_excel(io.BytesIO(file_bytes), sheet_name=chosen_s, 
                                          header=src_hdr, engine=src_engine, nrows=5)
            
            st.dataframe(df_preview.fillna(""), use_container_width=True, height=160)

            # Load button
            if st.button("✅ Load Source Data", type="primary", use_container_width=True, key='btn_load_source'):
                with st.spinner("Loading..."):
                    try:
                        if is_csv:
                            # Read as string to preserve exact values (phone numbers, etc.)
                            # Large files: chunked read then concat — same result as one-shot read, lower peak RAM
                            bio = io.BytesIO(file_bytes)
                            if len(file_bytes) >= CSV_CHUNK_LOAD_MIN_BYTES:
                                df = pd.concat(
                                    pd.read_csv(
                                        bio,
                                        dtype=str,
                                        keep_default_na=False,
                                        chunksize=CSV_READ_CHUNKSIZE,
                                    ),
                                    ignore_index=True,
                                )
                            else:
                                df = pd.read_csv(
                                    bio, dtype=str, keep_default_na=False
                                )
                            src_hdr = 0
                        else:
                            # Read as string to preserve exact values (phone numbers, etc.)
                            src_engine = _get_excel_engine(file_bytes, uploaded.name)
                            df = pd.read_excel(io.BytesIO(file_bytes), sheet_name=chosen_s,
                                              header=src_hdr, engine=src_engine, dtype=str, keep_default_na=False)
                        
                        df = df.dropna(how='all')
                        # DO NOT parse dates automatically - it converts phone numbers to dates
                        # df = parse_dates_in_dataframe(df)
                        df = filter_empty_and_generic_columns(df)
                        valid_columns = list(df.columns)

                        st.session_state.source_file.data = {chosen_s: df}
                        st.session_state.source_file.sheets = [chosen_s]
                        st.session_state.source_file.columns = {chosen_s: valid_columns}
                        st.session_state.source_file.selected_sheet = chosen_s
                        st.session_state.source_file.header_row = src_hdr

                        st.success(f"✅ Loaded {len(valid_columns)} columns, {len(df):,} rows")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error: {e}")

        except Exception as e:
            st.error(f"❌ Error: {e}")

        st.markdown('</div>', unsafe_allow_html=True)

    # Show loaded data summary
    if st.session_state.source_file.selected_sheet:
        df = st.session_state.source_file.data.get(
            st.session_state.source_file.selected_sheet,
            pd.DataFrame()
        )

        if len(df.columns) > 0:
            st.markdown('<div class="section-container">', unsafe_allow_html=True)
            st.markdown("**✅ Loaded Data Summary**")
            
            # Simple metrics
            cols = st.columns(3)
            cols[0].metric("📊 Rows", f"{len(df):,}")
            cols[1].metric("📋 Columns", len(df.columns))
            cols[2].metric("⚠️ Nulls", f"{df.isnull().sum().sum():,}")

            # Data preview in expander
            with st.expander("📊 View Data Preview", expanded=False):
                    display_df = df.head(100) if len(df) > 0 else pd.DataFrame(columns=df.columns)

                    column_config = {}
                    for col in df.columns:
                        # Determine column type based on actual data
                        dtype = df[col].dtype
                        if pd.api.types.is_integer_dtype(dtype):
                            column_config[col] = st.column_config.NumberColumn(
                                col,
                                help=f"Type: {dtype}",
                                width="medium"
                            )
                        elif pd.api.types.is_float_dtype(dtype):
                            column_config[col] = st.column_config.NumberColumn(
                                col,
                                help=f"Type: {dtype}",
                                width="medium",
                                format="%.2f"
                            )
                        elif pd.api.types.is_bool_dtype(dtype):
                            column_config[col] = st.column_config.CheckboxColumn(
                                col,
                                help=f"Type: {dtype}",
                                width="medium"
                            )
                        elif pd.api.types.is_datetime64_any_dtype(dtype):
                            column_config[col] = st.column_config.DatetimeColumn(
                                col,
                                help=f"Type: {dtype}",
                                width="medium"
                            )
                        else:
                            column_config[col] = st.column_config.TextColumn(
                                col,
                                help=f"Type: {dtype}",
                                width="medium"
                            )

                    st.data_editor(
                        display_df,
                        column_config=column_config,
                        use_container_width=True,
                        height=400,
                        key='source_preview_editor',
                        disabled=True
                    )

            # Columns list in separate expander
            with st.expander("📋 View All Columns", expanded=False):
                cols_list = list(df.columns)
                for i in range(0, len(cols_list), 4):
                    cols = st.columns(4)
                    for j, col in enumerate(cols_list[i:i+4]):
                        with cols[j]:
                            st.markdown(f"<code>{col}</code>", unsafe_allow_html=True)

            st.markdown('</div>', unsafe_allow_html=True)

            if 'source_file' not in st.session_state.completed_steps:
                st.session_state.completed_steps.add('source_file')
                
            st.success("✅ Data Source loaded successfully!")

        # Navigation buttons - always at bottom of tab
        st.markdown("---")
        if st.session_state.source_file.selected_sheet and len(st.session_state.source_file.data.get(st.session_state.source_file.selected_sheet, pd.DataFrame()).columns) > 0:
            col1, col2 = st.columns(2)
            with col1:
                if st.button("⬅️ Back to Template", use_container_width=True, key='btn_source_to_template'):
                    st.session_state.active_tab = 0
                    st.session_state.tab_change_requested = True
                    st.rerun()
            with col2:
                if st.button("➡️ Next: Data Profiling", type="primary", use_container_width=True, key='btn_source_to_profile'):
                    st.session_state.active_tab = 2
                    st.session_state.tab_change_requested = True
                    st.rerun()
        else:
            st.info("ℹ️ Load source file to proceed")

# =============================================================================
# TAB 3: VALIDATION RULES CONFIGURATION
# =============================================================================

