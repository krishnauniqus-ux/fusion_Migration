"""
Data processing utilities - EXACT from vnew.py
"""
import pandas as pd
import re
from typing import List

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
        # Check if column name is auto-generated placeholder
        if is_generic_column(col):
            continue
        
        # Check if column is completely empty (all null)
        if df[col].isna().all():
            continue
        
        # Keep this column - it's an actual column from the file
        valid_columns.append(col)
    
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
