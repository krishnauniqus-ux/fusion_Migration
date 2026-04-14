"""
File handling utilities - EXACT from vnew.py
"""
import pandas as pd
import io
import re
import streamlit as st
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings("ignore")

def detect_file_type(file_name: str) -> str:
    """Detect file type from extension"""
    if file_name.lower().endswith('.csv'):
        return 'csv'
    elif file_name.lower().endswith(('.xlsx', '.xls', '.xlsm', '.xlsb')):
        return 'excel'
    return 'unknown'

def _get_excel_engine(file_bytes: bytes, file_name: str = '') -> str:
    """
    Pick the right engine based on actual file content (magic bytes) first,
    falling back to extension. This handles Windows 8.3 short names like
    EMD659~1.XLS that are actually .xlsm/.xlsx files.
    
    Returns: 'openpyxl' or 'xlrd'
    """
    if not file_bytes or len(file_bytes) < 8:
        return 'openpyxl'  # default fallback
    
    # ZIP magic bytes = PK\x03\x04 → xlsx / xlsm / xlsb (openpyxl)
    if file_bytes[:4] == b'PK\x03\x04':
        return 'openpyxl'
    
    # Compound Document magic bytes = \xD0\xCF\x11\xE0 → legacy .xls (xlrd)
    if file_bytes[:8] == b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1':
        return 'xlrd'
    
    # Fall back to extension only if magic bytes are inconclusive
    name = file_name.lower()
    if name.endswith('.xls') and not name.endswith(('.xlsx', '.xlsm', '.xlsb')):
        return 'xlrd'
    
    return 'openpyxl'

def _scalar_isna(val) -> bool:
    """Safe scalar NA check that never raises 'truth value of Series is ambiguous'."""
    try:
        result = pd.isna(val)
        # pd.isna on a scalar returns bool; on array-like returns array
        if isinstance(result, (bool, int)):
            return bool(result)
        # array-like: treat as NA only if ALL elements are NA
        return bool(result.all())
    except Exception:
        return False

def _safe_tolist(row_data):
    """Safely convert a DataFrame row to a list, handling Series and edge cases."""
    try:
        if hasattr(row_data, 'tolist'):
            result = row_data.tolist()
        elif hasattr(row_data, 'values'):
            result = row_data.values.tolist()
        else:
            result = list(row_data)
        # Ensure we got a list of scalars, not nested structures
        return [x if not hasattr(x, '__iter__') or isinstance(x, str) else str(x) for x in result]
    except Exception:
        return []

def clean_column_names(columns, header_row=None):
    """
    Clean column names by handling unnamed columns and stripping whitespace.
    Preserves actual header values from the selected row.
    Only replaces truly empty/NaN values with Column_N placeholders.
    """
    cleaned = []
    for i, col in enumerate(columns):
        col_str = str(col).strip()
        
        # Check if this is a truly empty/invalid value
        is_empty = (
            col_str.lower() in ['nan', 'none', ''] or
            _scalar_isna(col) or
            col_str == 'nan' or
            col_str.startswith('Unnamed:')  # Pandas generated placeholder
        )
        
        if is_empty:
            # Replace with generic name only for truly empty values
            cleaned.append(f"Column_{i+1}")
        else:
            # Keep the original value (even if it starts with Column_)
            cleaned.append(col_str)
    return cleaned

def is_generic_column(column_name: str) -> bool:
    """
    Check if a column name is auto-generated placeholder (Column_X, Unnamed:).
    Returns True only for pandas-generated placeholders, not actual column names.
    """
    col_str = str(column_name).strip()
    
    # Only check for pandas auto-generated patterns
    generic_patterns = [
        r'^Column_\d+$',           # Column_1, Column_2, Column_92, etc. (pandas generated)
        r'^Unnamed:\s*\d+$',       # Unnamed: 0, Unnamed: 1, etc. (pandas generated)
    ]
    
    for pattern in generic_patterns:
        if re.match(pattern, col_str, re.IGNORECASE):
            return True
    
    return False

def filter_generic_columns(columns: List[str]) -> List[str]:
    """
    Filter out only pandas auto-generated column names.
    Returns all actual columns from the file.
    """
    return [col for col in columns if not is_generic_column(col)]

def filter_empty_and_generic_columns(df: pd.DataFrame, threshold: float = 0.95) -> pd.DataFrame:
    """
    Filter out columns that are:
    1. Auto-generated placeholders (Column_X, Unnamed:)
    2. Completely empty (100% null values)
    
    Keeps all actual columns from the file, even if they have names like "Role 1", "Field 1", etc.
    
    Args:
        df: DataFrame to filter
        threshold: Not used anymore, kept for compatibility
    
    Returns:
        Filtered DataFrame with only actual columns from the file
    """
    if df.empty or len(df.columns) == 0:
        return df
    
    valid_columns = []
    
    for col in df.columns:
        try:
            # Ensure col is a scalar string, not a Series or array
            col_name = str(col) if not isinstance(col, str) else col
            
            # Check if column name is auto-generated placeholder
            if is_generic_column(col_name):
                continue
            
            # Check if column is completely empty (all null)
            # Use the original col for indexing, not col_name
            if df[col].isna().all():
                continue
            
            # Keep this column - it's an actual column from the file
            valid_columns.append(col)
        except Exception as e:
            # If any error, skip this column
            continue
    
    # Return filtered dataframe
    if len(valid_columns) > 0:
        return df[valid_columns]
    else:
        # If no valid columns found, return empty dataframe
        return pd.DataFrame()

def parse_dates_in_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Automatically detect and parse date/datetime columns in various formats.
    Supports: ISO 8601, date-only, datetime, timestamps, and common date formats.
    """
    for col in df.columns:
        # Skip if already datetime
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            continue
            
        # Only try to parse object/string columns
        if df[col].dtype == 'object' or df[col].dtype == 'string':
            try:
                # Try to parse as datetime (pandas now infers format by default)
                # This handles ISO 8601, common formats, timestamps, etc.
                parsed = pd.to_datetime(df[col], errors='coerce')
                
                # Only convert if at least 50% of non-null values were successfully parsed
                non_null_count = df[col].notna().sum()
                parsed_count = parsed.notna().sum()
                
                if non_null_count > 0 and (parsed_count / non_null_count) >= 0.5:
                    df[col] = parsed
            except:
                # If parsing fails, leave as is
                pass
    
    return df

def read_uploaded_file(uploaded_file, header_row: int = 0, selected_sheet: str = None) -> Tuple[Dict[str, pd.DataFrame], List[str], Dict[str, List[str]]]:
    """
    Read uploaded file and return data dictionary, sheet names, and column mapping.
    Uses the specified header_row to read column names dynamically.
    Ensures column headers are always captured even if no data rows exist.
    """
    if uploaded_file is None:
        return {}, [], {}
    
    try:
        # Handle both uploaded files and BytesIO objects
        if hasattr(uploaded_file, 'name') and uploaded_file.name:
            file_type = detect_file_type(uploaded_file.name)
            fname = uploaded_file.name
        else:
            fname = ''
            file_type = 'excel'  # default, will be confirmed below

        if hasattr(uploaded_file, 'getvalue'):
            file_bytes = uploaded_file.getvalue()
        else:
            file_bytes = uploaded_file.read()
            if hasattr(uploaded_file, 'seek'):
                uploaded_file.seek(0)

        # If no name, sniff the format from content
        if not fname:
            try:
                pd.ExcelFile(io.BytesIO(file_bytes), engine='openpyxl')
                file_type = 'excel'
                fname = 'file.xlsx'
            except Exception:
                try:
                    pd.ExcelFile(io.BytesIO(file_bytes), engine='xlrd')
                    file_type = 'excel'
                    fname = 'file.xls'
                except Exception:
                    file_type = 'csv'
                    fname = 'file.csv'
        
        data = {}
        
        if file_type == 'csv':
            # First, read without headers to get the raw data preview
            raw_df = pd.read_csv(io.BytesIO(file_bytes), header=None, nrows=50)
            
            # Extract column names from the selected header row if it exists
            if header_row < len(raw_df):
                column_names = clean_column_names(_safe_tolist(raw_df.iloc[header_row]), header_row)
            else:
                # Fallback to generic names if header row is beyond data
                column_names = [f"Column_{i+1}" for i in range(len(raw_df.columns))]
            
            # Read again with the specified header row - READ ALL AS STRING to preserve exact values
            df = pd.read_csv(io.BytesIO(file_bytes), header=header_row, dtype=str, keep_default_na=False)
            
            # Ensure dataframe has the correct column names
            if len(df) == 0:
                # No data rows - create empty df with extracted column names
                if len(column_names) > 0:
                    df = pd.DataFrame(columns=column_names)
                # else: keep pandas default columns from header row
            else:
                # Has data rows - clean the column names from header row
                df.columns = clean_column_names(_safe_tolist(df.columns), header_row)
            
            # Drop rows that are completely empty
            df = df.dropna(how='all')
            
            # DO NOT parse dates automatically - it converts phone numbers to dates
            # df = parse_dates_in_dataframe(df)
            
            data['Sheet1'] = df
            sheets = ['Sheet1']
            
        elif file_type == 'excel':
            # Pick engine: xlrd for .xls, openpyxl for everything else
            engine = _get_excel_engine(file_bytes, fname)

            try:
                # Read all sheets from Excel
                excel_file = pd.ExcelFile(io.BytesIO(file_bytes), engine=engine)
                all_sheets = excel_file.sheet_names
            except Exception as e:
                st.error(f"❌ Cannot open Excel file with {engine} engine: {str(e)}")
                # Try the other engine as fallback
                fallback_engine = 'xlrd' if engine == 'openpyxl' else 'openpyxl'
                try:
                    excel_file = pd.ExcelFile(io.BytesIO(file_bytes), engine=fallback_engine)
                    all_sheets = excel_file.sheet_names
                    engine = fallback_engine
                except Exception as e2:
                    st.error(f"❌ Fallback to {fallback_engine} also failed: {str(e2)}")
                    return {}, [], {}
            
            # If specific sheet requested, only process that one
            sheets_to_process = [selected_sheet] if selected_sheet and selected_sheet in all_sheets else all_sheets
            
            for sheet in sheets_to_process:
                try:
                    # Read the full sheet WITHOUT headers first - READ ALL AS STRING to preserve exact values
                    raw_df = pd.read_excel(io.BytesIO(file_bytes), sheet_name=sheet, header=None,
                                           dtype=str, keep_default_na=False, engine=engine)
                    
                    # Get total rows and columns
                    total_rows = len(raw_df)
                    total_cols = len(raw_df.columns)
                    
                    if total_rows == 0:
                        st.warning(f"⚠ Sheet '{sheet}' is empty, skipping")
                        continue
                    
                    # Extract column names from the selected header row
                    if header_row < total_rows:
                        header_values = _safe_tolist(raw_df.iloc[header_row])
                        
                        # Convert to strings and use as column names directly
                        column_names = []
                        for i, val in enumerate(header_values):
                            # Safe string conversion that handles Series, None, NaN, etc.
                            try:
                                val_str = str(val).strip() if not _scalar_isna(val) else ''
                            except Exception:
                                val_str = ''
                            
                            if val_str == '' or val_str.lower() == 'nan':
                                column_names.append(f"Column_{i+1}")
                            else:
                                column_names.append(val_str)
                    else:
                        # Fallback if header row is beyond data
                        column_names = [f"Column_{i+1}" for i in range(total_cols)]
                    
                    # Extract data rows (everything after header row)
                    if header_row + 1 < total_rows:
                        data_df = raw_df.iloc[header_row + 1:].copy()
                        data_df.columns = column_names
                        data_df = data_df.reset_index(drop=True)
                    else:
                        # No data rows - create empty dataframe with headers
                        data_df = pd.DataFrame(columns=column_names)
                    
                    # Only drop rows that are completely empty, NOT columns
                    # This preserves all columns the user selected
                    data_df = data_df.dropna(how='all')
                    
                    # DO NOT parse dates automatically - it converts phone numbers to dates
                    # data_df = parse_dates_in_dataframe(data_df)
                    
                    data[sheet] = data_df
                except Exception as e:
                    st.warning(f"⚠ Error reading sheet '{sheet}': {str(e)}")
                    import traceback
                    st.text(traceback.format_exc())
                    continue
                    
            sheets = list(data.keys())
        else:
            st.error("❌ Unsupported file format. Please upload CSV or Excel files.")
            return {}, [], {}
        
        # Extract columns for each sheet and filter out auto-generated placeholders
        columns = {}
        for sheet, df in data.items():
            # Apply filtering: remove Column_X, Unnamed:, and completely empty columns
            filtered_df = filter_empty_and_generic_columns(df)
            valid_cols = list(filtered_df.columns)
            columns[sheet] = valid_cols
            # Update the dataframe to only include valid columns
            data[sheet] = filtered_df
        
        return data, sheets, columns
        
    except Exception as e:
        st.error(f"❌ Error reading file: {str(e)}")
        import traceback
        st.text(traceback.format_exc())
        return {}, [], {}

def get_header_preview(file_bytes: bytes, file_type: str, sheet_name: str = None, max_rows: int = 10, file_name: str = '') -> Optional[pd.DataFrame]:
    """Get preview of file for header row selection"""
    try:
        if file_type == 'csv':
            return pd.read_csv(io.BytesIO(file_bytes), header=None, nrows=max_rows)
        else:
            engine = _get_excel_engine(file_bytes, file_name)
            return pd.read_excel(io.BytesIO(file_bytes), sheet_name=sheet_name, header=None,
                                 nrows=max_rows, engine=engine)
    except:
        return None

def auto_detect_header(df: pd.DataFrame, max_rows: int = 10) -> int:
    """Auto-detect which row contains the header"""
    if df is None or len(df) == 0:
        return 0
    
    # Check first few rows
    check_rows = min(max_rows, len(df))
    
    best_row = 0
    best_score = 0
    
    for row_idx in range(check_rows):
        row = df.iloc[row_idx]
        score = 0
        
        # Score based on:
        # 1. Non-null values
        score += row.notna().sum() * 2
        
        # 2. String values (headers are usually strings)
        score += sum(1 for val in row if isinstance(val, str)) * 3
        
        # 3. Unique values (headers should be unique)
        score += len(set(row.dropna())) * 2
        
        # 4. No numeric-only values (headers rarely all numbers)
        numeric_count = sum(1 for val in row if isinstance(val, (int, float)) and not isinstance(val, bool))
        if numeric_count < len(row) * 0.5:
            score += 5
        
        if score > best_score:
            best_score = score
            best_row = row_idx
    
    return best_row
