"""
Excel Report Generator for Data Profiling
Generates comprehensive Excel report with multiple sheets
"""

import pandas as pd
import io
from datetime import datetime
from typing import Dict
from core.profiler_engine import ColumnProfile


def generate_profiling_report(df: pd.DataFrame, profiles: Dict[str, ColumnProfile], 
                              filename: str = "source_data") -> bytes:
    """
    Generate comprehensive Excel report with multiple sheets
    
    Returns:
        bytes: Excel file content
    """
    output = io.BytesIO()
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Sheet 1: Executive Summary
        _write_executive_summary(writer, df, profiles, filename)
        
        # Sheet 2: Column Profiles
        _write_column_profiles(writer, profiles)
        
        # Sheet 3: Special Characters
        _write_special_characters(writer, df, profiles)
        
        # Sheet 4: Duplicates Analysis
        _write_duplicates(writer, df, profiles)
        
        # Sheet 5: Exact Duplicates
        _write_exact_duplicates(writer, df)
        
        # Sheet 6: Data Sample
        _write_data_sample(writer, df)
    
    output.seek(0)
    return output.getvalue()


def _write_executive_summary(writer, df: pd.DataFrame, profiles: Dict[str, ColumnProfile], filename: str):
    """Write Executive Summary sheet"""
    total_rows = len(df)
    total_cols = len(df.columns)
    total_cells = total_rows * total_cols
    missing_cells = sum(p.null_count for p in profiles.values())
    completeness = ((total_cells - missing_cells) / total_cells) * 100 if total_cells else 0
    
    # Calculate quality scores
    quality_scores = []
    for p in profiles.values():
        comp = p.non_null_percentage
        uniq = min(100, p.unique_percentage * 1.2) if p.unique_percentage < 100 else 90
        quality = (comp * 0.6 + uniq * 0.4)
        quality_scores.append(quality)
    
    avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
    
    # High risk columns
    high_risk_cols = [p.column_name for p in profiles.values() if p.risk_level == 'High']
    
    # Duplicate analysis
    duplicate_cols = [p.column_name for p in profiles.values() if p.duplicate_count > 0]
    
    summary_data = {
        'Metric': [
            'Report Generated',
            'Source File',
            'Total Rows',
            'Total Columns',
            'Total Cells',
            'Missing Cells',
            'Completeness %',
            'Overall Quality Score',
            'High Risk Columns',
            'Columns with Duplicates',
            'Average Null %',
            'Average Unique %'
        ],
        'Value': [
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            filename,
            f"{total_rows:,}",
            total_cols,
            f"{total_cells:,}",
            f"{missing_cells:,}",
            f"{completeness:.2f}%",
            f"{avg_quality:.2f}%",
            len(high_risk_cols),
            len(duplicate_cols),
            f"{sum(p.null_percentage for p in profiles.values()) / len(profiles):.2f}%",
            f"{sum(p.unique_percentage for p in profiles.values()) / len(profiles):.2f}%"
        ]
    }
    
    summary_df = pd.DataFrame(summary_data)
    summary_df.to_excel(writer, sheet_name='Executive Summary', index=False)
    
    # Add high risk columns list
    if high_risk_cols:
        risk_df = pd.DataFrame({
            'High Risk Columns': high_risk_cols,
            'Risk Level': ['High'] * len(high_risk_cols)
        })
        risk_df.to_excel(writer, sheet_name='Executive Summary', 
                        startrow=len(summary_df) + 3, index=False)


def _write_column_profiles(writer, profiles: Dict[str, ColumnProfile]):
    """Write Column Profiles sheet"""
    profile_data = []
    
    for col, p in profiles.items():
        profile_data.append({
            'Column Name': col,
            'Data Type': p.dtype,
            'Total Rows': p.total_rows,
            'Non-Null Count': p.non_null_count,
            'Null Count': p.null_count,
            'Null %': f"{p.null_percentage:.2f}%",
            'Unique Count': p.unique_count,
            'Unique %': f"{p.unique_percentage:.2f}%",
            'Duplicate Count': p.duplicate_count,
            'Duplicate %': f"{p.duplicate_percentage:.2f}%",
            'Min Length': p.min_length,
            'Max Length': p.max_length,
            'Avg Length': f"{p.avg_length:.2f}",
            'Special Chars': ', '.join(p.special_chars) if p.special_chars else 'None',
            'Risk Level': p.risk_level,
            'Risk Score': p.risk_score,
            'Sample Values': ', '.join(str(v) for v in p.sample_values[:3])
        })
    
    profile_df = pd.DataFrame(profile_data)
    profile_df.to_excel(writer, sheet_name='Column Profiles', index=False)


def _write_special_characters(writer, df: pd.DataFrame, profiles: Dict[str, ColumnProfile]):
    """Write Special Characters sheet"""
    special_char_data = []
    
    for col, p in profiles.items():
        if p.special_chars:
            for char in p.special_chars:
                # Count occurrences
                if pd.api.types.is_string_dtype(df[col]) or df[col].dtype == 'object':
                    count = df[col].dropna().astype(str).str.contains(char, regex=False).sum()
                    percentage = (count / len(df)) * 100
                    
                    # Get examples
                    examples = df[df[col].astype(str).str.contains(char, regex=False)][col].head(3).tolist()
                    
                    special_char_data.append({
                        'Column': col,
                        'Special Character': char,
                        'Count': count,
                        'Percentage': f"{percentage:.2f}%",
                        'Examples': ', '.join(str(e)[:50] for e in examples)
                    })
    
    if special_char_data:
        special_df = pd.DataFrame(special_char_data)
        special_df.to_excel(writer, sheet_name='Special Characters', index=False)
    else:
        # Empty sheet with message
        pd.DataFrame({'Message': ['No special characters detected']}).to_excel(
            writer, sheet_name='Special Characters', index=False)


def _write_duplicates(writer, df: pd.DataFrame, profiles: Dict[str, ColumnProfile]):
    """Write Duplicates Analysis sheet"""
    duplicate_data = []
    
    for col, p in profiles.items():
        if p.duplicate_count > 0:
            # Find duplicate values
            value_counts = df[col].value_counts()
            duplicates = value_counts[value_counts > 1].head(10)
            
            for value, count in duplicates.items():
                percentage = (count / len(df)) * 100
                duplicate_data.append({
                    'Column': col,
                    'Duplicate Value': str(value)[:100],
                    'Occurrences': count,
                    'Percentage': f"{percentage:.2f}%"
                })
    
    if duplicate_data:
        dup_df = pd.DataFrame(duplicate_data)
        dup_df.to_excel(writer, sheet_name='Duplicates', index=False)
    else:
        pd.DataFrame({'Message': ['No duplicates detected']}).to_excel(
            writer, sheet_name='Duplicates', index=False)


def _write_exact_duplicates(writer, df: pd.DataFrame):
    """Write Exact Duplicate Rows sheet"""
    # Find exact duplicate rows
    duplicates = df[df.duplicated(keep=False)]
    
    if len(duplicates) > 0:
        # Limit to first 1000 rows to avoid Excel limits
        duplicates_sample = duplicates.head(1000)
        duplicates_sample.to_excel(writer, sheet_name='Exact Duplicates', index=True)
    else:
        pd.DataFrame({'Message': ['No exact duplicate rows found']}).to_excel(
            writer, sheet_name='Exact Duplicates', index=False)


def _write_data_sample(writer, df: pd.DataFrame):
    """Write Data Sample sheet"""
    # First 100 rows
    sample = df.head(100)
    sample.to_excel(writer, sheet_name='Data Sample', index=True)
