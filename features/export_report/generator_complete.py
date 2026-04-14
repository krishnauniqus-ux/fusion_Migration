"""
Complete Excel Report Generator - EXACT COPY from DataProfilingTool
Generates the same report format as Demo_Supplier_Consolidated_Data_Profile_20260323_205024.xlsx
"""

import pandas as pd
import io
import os
import re
import unicodedata
from datetime import datetime
from typing import Dict, List
from collections import Counter
from itertools import combinations
from core.profiler_engine import ColumnProfile


# Import quality scorer
try:
    from core.data_cleaner import QualityScorer
except ImportError:
    QualityScorer = None


# ==========================================
# HELPER FUNCTIONS - EXACT COPY from DataProfilingTool
# ==========================================

def get_duplicate_count_values(df, col, max_items=5):
    """Get top duplicate values with their counts - EXACT COPY from DataProfilingTool"""
    if col not in df.columns:
        return "N/A"
    
    try:
        value_counts = df[col].value_counts(dropna=False)
        duplicates = value_counts[value_counts > 1]
        
        if len(duplicates) == 0:
            return "No duplicates"
        
        dup_strings = []
        for val, count in duplicates.items():
            if pd.isna(val) or (isinstance(val, str) and val.strip() == ''):
                dup_strings.append(f"Missing Values({count})")
            else:
                val_str = str(val).strip()
                dup_strings.append(f"{val_str}({count})")
        
        return ", ".join(dup_strings)
    except Exception as e:
        return "Error"


def _analyze_special_chars_detailed(df):
    """Analyze special characters - EXACT COPY from DataProfilingTool"""
    data = []
    for col in df.select_dtypes(include=['object']).columns:
        counter = Counter()
        for val in df[col].dropna().astype(str):
            for char in set(val):
                if ord(char) > 127 or (not char.isalnum() and not char.isspace()):
                    counter[char] += val.count(char)
        for char, count in counter.most_common():
            try: 
                uname = unicodedata.name(char)
            except: 
                uname = "UNKNOWN"
            data.append({'Column': col, 'Character': char, 'Unicode Name': uname, 'Count': count})
    return data


def generate_match_rules(df, profiles):
    """Generate match rules - EXACT COPY from DataProfilingTool"""
    rules = []
    counter = 1

    analysis = {}
    for col, prof in profiles.items():
        total_rows = int(getattr(prof, 'total_rows', 0) or 0)
        unique_count = int(getattr(prof, 'unique_count', 0) or 0)
        dup_count = max(0, total_rows - unique_count)
        dup_pct = (dup_count / total_rows * 100) if total_rows > 0 else 0

        dtype = getattr(prof, 'dtype', '') or ''

        analysis[col] = {
            'null_pct': getattr(prof, 'null_percentage', 0),
            'unique_pct': getattr(prof, 'unique_percentage', 0),
            'dup_pct': dup_pct,
            'dup_count': dup_count,
            'is_text': dtype == 'object',
            'is_num': any(t in dtype for t in ['int', 'float']),
            'avg_len': getattr(prof, 'avg_length', 0),
            'max_len': getattr(prof, 'max_length', 0),
            'min_len': getattr(prof, 'min_length', 0),
            'total_rows': total_rows
        }

    # EXACT MATCH CANDIDATES
    exact_candidates = []
    for col, a in analysis.items():
        if a['unique_pct'] == 100 or a['dup_count'] == 0:
            continue

        score = 0
        reasons = []

        if 95 <= a['unique_pct'] < 100:
            score += 35
            reasons.append(f"Near-unique ({a['unique_pct']:.1f}%)")
        elif 80 <= a['unique_pct'] < 95:
            score += 25
            reasons.append(f"High uniqueness ({a['unique_pct']:.1f}%)")

        if a['null_pct'] < 1:
            score += 20
            reasons.append("Complete data (no nulls)")
        elif a['null_pct'] < 5:
            score += 15
            reasons.append("Low null rate")

        if a['is_text'] and a['max_len'] == a['min_len'] and 4 <= a['avg_len'] <= 20:
            score += 25
            reasons.append(f"Fixed length ({int(a['avg_len'])} chars)")

        if 0 < a['dup_pct'] < 5:
            score += 15
            reasons.append(f"Low duplicates ({a['dup_pct']:.1f}%)")

        if score >= 50 and a['dup_count'] > 0:
            exact_candidates.append({
                'column': col,
                'score': score,
                'reasons': reasons,
                'dup_count': a['dup_count'],
                'unique_pct': a['unique_pct']
            })

    exact_candidates.sort(key=lambda x: x['score'], reverse=True)

    for cand in exact_candidates[:4]:
        prob = "Strongest" if cand['score'] >= 85 else "Very Strong" if cand['score'] >= 75 else "Strong" if cand['score'] >= 65 else "Good"
        rules.append({
            'Rule No': f"R{counter:02d}",
            'Rule Type': 'Exact',
            'Columns': cand['column'],
            'Match Probability': prob,
            'Rationale': f"{'; '.join(cand['reasons'][:2])} | Duplicates: {cand['dup_count']}",
            'Confidence': cand['score']
        })
        counter += 1

    # FUZZY MATCH CANDIDATES
    fuzzy_candidates = []
    for col, a in analysis.items():
        if not a['is_text']:
            continue

        score = 0
        reasons = []

        if 30 <= a['unique_pct'] <= 90:
            score += 35
            reasons.append(f"Medium uniqueness ({a['unique_pct']:.1f}%)")
        elif 10 <= a['unique_pct'] < 30:
            score += 20
            reasons.append(f"Low-medium uniqueness ({a['unique_pct']:.1f}%)")

        if 10 <= a['avg_len'] <= 100:
            score += 25
            reasons.append(f"Name/description length ({a['avg_len']:.0f} chars)")
        elif a['avg_len'] > 100:
            score += 15
            reasons.append("Long text field")

        name_indicators = ['name', 'desc', 'title', 'product', 'customer', 'company', 'vendor', 'supplier', 'brand', 'item']
        if any(ind in col.lower() for ind in name_indicators):
            score += 25
            reasons.append("Name/description column")

        if a['dup_count'] > 1:
            score += 15
            reasons.append(f"Has duplicates to match ({a['dup_count']})")

        if score >= 45:
            fuzzy_candidates.append({
                'column': col,
                'score': score,
                'reasons': reasons,
                'unique_pct': a['unique_pct']
            })

    fuzzy_candidates.sort(key=lambda x: x['score'], reverse=True)

    for cand in fuzzy_candidates[:4]:
        prob = "Strong" if cand['score'] >= 70 else "Good" if cand['score'] >= 60 else "Medium"
        rules.append({
            'Rule No': f"R{counter:02d}",
            'Rule Type': 'Fuzzy',
            'Columns': cand['column'],
            'Match Probability': prob,
            'Rationale': '; '.join(cand['reasons'][:3]),
            'Confidence': cand['score']
        })
        counter += 1

    # COMBINED RULES
    if exact_candidates and fuzzy_candidates:
        for e in exact_candidates[:2]:
            for f in fuzzy_candidates[:3]:
                if e['column'] != f['column'] and len(rules) < 10:
                    score = (e['score'] + f['score']) / 2
                    prob = "Enterprise" if score >= 75 else "Strong" if score >= 65 else "Good"
                    rules.append({
                        'Rule No': f"R{counter:02d}",
                        'Rule Type': 'Combined',
                        'Columns': f"{e['column']} (Exact) + {f['column']} (Fuzzy)",
                        'Match Probability': prob,
                        'Rationale': f"Exact on {e['column']}; Fuzzy match on {f['column']}",
                        'Confidence': score
                    })
                    counter += 1
                    if len(rules) >= 10:
                        break
            if len(rules) >= 10:
                break

    if not rules and analysis:
        first = list(analysis.keys())[0]
        rules.append({
            'Rule No': 'R01',
            'Rule Type': 'Exact',
            'Columns': first,
            'Match Probability': 'Medium',
            'Rationale': 'Default fallback rule',
            'Confidence': 50
        })

    rules.sort(key=lambda x: x['Confidence'], reverse=True)
    for i, r in enumerate(rules[:10], 1):
        r['Rule No'] = f"R{i:02d}"

    return rules[:10]


# ==========================================
# MAIN REPORT GENERATION - EXACT COPY from DataProfilingTool
# ==========================================

def generate_complete_profiling_report(df: pd.DataFrame, profiles: Dict[str, ColumnProfile], 
                                      filename: str = "source_data") -> bytes:
    """
    Generate COMPLETE Excel report - EXACT SAME as DataProfilingTool + Quality Enhancements
    Same format as Demo_Supplier_Consolidated_Data_Profile_20260323_205024.xlsx
    
    Sheets:
    1. Executive Summary (Enhanced with Quality Scores)
    2. Column Profiles  
    3. Special Characters
    4. Match Rules
    5. Duplicates
    6. Exact Duplicate
    
    Returns:
        bytes: Excel file content
    """
    output = io.BytesIO()
    
    try:
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Calculate quality scores
            quality_scores = {}
            if QualityScorer:
                quality_scores = QualityScorer.calculate_quality_score(df, profiles)
            
            # Sheet 1: Executive Summary (Enhanced)
            total_missing = sum(p.null_count for p in profiles.values())
            quality = sum(getattr(p, 'non_null_percentage', 100) for p in profiles.values()) / len(profiles) if profiles else 0
            completeness_pct = ((len(df)*len(df.columns)-total_missing)/(len(df)*len(df.columns))*100) if len(df)*len(df.columns) > 0 else 0

            summary_data = {
                'Metric': [
                    'Total Rows', 
                    'Total Columns', 
                    'Total Cells', 
                    'Missing Cells', 
                    'Completeness %', 
                    'Quality Score',
                    'Generated At'
                ],
                'Value': [
                    len(df), 
                    len(df.columns), 
                    len(df)*len(df.columns), 
                    total_missing, 
                    f"{completeness_pct:.2f}%",
                    f"{quality:.1f}%", 
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                ]
            }
            
            # Add quality metrics if available
            if quality_scores:
                summary_data['Metric'].extend([
                    'Overall Quality',
                    'Data Completeness',
                    'Data Uniqueness',
                    'Data Consistency',
                    'Data Accuracy',
                    'Quality Grade'
                ])
                summary_data['Value'].extend([
                    f"{quality_scores.get('overall_score', 0):.1f}%",
                    f"{quality_scores.get('completeness', 0):.1f}%",
                    f"{quality_scores.get('uniqueness', 0):.1f}%",
                    f"{quality_scores.get('consistency', 0):.1f}%",
                    f"{quality_scores.get('accuracy', 0):.1f}%",
                    quality_scores.get('grade', 'N/A')
                ])
            
            pd.DataFrame(summary_data).to_excel(writer, sheet_name='Executive Summary', index=False)

            # Sheet 2: Column Profiles
            profile_data = []
            for col, p in profiles.items():
                dup_count = p.total_rows - p.unique_count
                dup_values_str = get_duplicate_count_values(df, col, max_items=None)
                profile_data.append({
                    'Column Name': col,
                    'Data Type': p.dtype,
                    'Total Rows': p.total_rows,
                    'Non-Null Count': p.total_rows - p.null_count,
                    'Null Count': p.null_count,
                    'Null Percentage': f"{p.null_percentage:.2f}%",
                    'Unique Count': p.unique_count,
                    'Duplicate Count': dup_count,
                    'Duplicate Count Values': dup_values_str,
                    'Unique Percentage': f"{p.unique_percentage:.2f}%",
                    'Min Length': getattr(p, 'min_length', 'N/A'),
                    'Max Length': getattr(p, 'max_length', 'N/A'),
                    'Avg Length': f"{getattr(p, 'avg_length', 0):.2f}",
                    'Risk Level': getattr(p, 'risk_level', 'Low'),
                    'Risk Score': getattr(p, 'risk_score', 0)
                })
            pd.DataFrame(profile_data).to_excel(writer, sheet_name='Column Profiles', index=False)

            # Sheet 3: Special Characters
            chars = _analyze_special_chars_detailed(df)
            (pd.DataFrame(chars) if chars else pd.DataFrame({'Message': ['No special characters found']})).to_excel(
                writer, sheet_name='Special Characters', index=False)

            # Sheet 4: Match Rules
            match_rules = generate_match_rules(df, profiles)
            pd.DataFrame(match_rules).to_excel(writer, sheet_name='Match Rules', index=False)

            # Sheet 5: Duplicates (Column-wise with fuzzy matching logic)
            _write_duplicates_sheet(writer, df)

            # Sheet 6: Exact Duplicate (Row-wise with advanced detection)
            _write_exact_duplicates_sheet(writer, df)

        output.seek(0)
        return output.getvalue()
        
    except Exception as e:
        print(f"Error generating report: {str(e)}")
        raise


def _write_duplicates_sheet(writer, df):
    """Write Duplicates sheet - EXACT COPY from DataProfilingTool"""
    all_duplicate_records = []
    
    for col in df.columns:
        try:
            if not pd.api.types.is_string_dtype(df[col]) and df[col].dtype != 'object':
                continue
            
            unique_values = df[col].dropna().unique()
            
            if len(unique_values) < 2:
                continue
            
            # EXACT DUPLICATES
            value_counts = df[col].value_counts(dropna=True)
            duplicate_values = value_counts[value_counts > 1]
            
            for dup_val in duplicate_values.index:
                if isinstance(dup_val, str):
                    dup_str = str(dup_val).strip().upper()
                    if dup_str in ['', 'NULL', 'NONE', 'NA', 'N/A', 'NAN', 'BLANK', '-', '--', '---']:
                        continue
                
                matching_rows = df[df[col] == dup_val]
                
                for idx, row in matching_rows.iterrows():
                    record = {orig_col: 'Missing' for orig_col in df.columns}
                    record[col] = dup_val
                    all_duplicate_records.append(record)
        
        except Exception:
            continue
    
    if all_duplicate_records:
        duplicates_df = pd.DataFrame(all_duplicate_records)
        duplicates_df = duplicates_df.sort_values(by=df.columns.tolist())
        duplicates_df.to_excel(writer, sheet_name='Duplicates', index=False)
    else:
        pd.DataFrame({
            'Message': ['No duplicate or similar values found (nulls/empty excluded)']
        }).to_excel(writer, sheet_name='Duplicates', index=False)


def _write_exact_duplicates_sheet(writer, df):
    """Write Exact Duplicate sheet - EXACT COPY from DataProfilingTool"""
    
    def _is_valid_value(val) -> bool:
        if pd.isna(val):
            return False
        str_val = str(val).strip().upper()
        invalid_values = ['', 'NULL', 'NONE', 'NA', 'N/A', 'NAN', 'BLANK', '-', '--', '---']
        return str_val not in invalid_values
    
    def _has_valid_values(df: pd.DataFrame, indices: List, columns: List[str]) -> List:
        valid_indices = []
        for idx in indices:
            all_valid = all(_is_valid_value(df.loc[idx, col]) for col in columns)
            if all_valid:
                valid_indices.append(idx)
        return valid_indices
    
    def _categorize_columns(df: pd.DataFrame) -> Dict[str, List[str]]:
        categories = {
            'unique_identifiers': [],
            'critical_business': [],
            'descriptive': [],
            'metadata': []
        }
        
        for col in df.columns:
            col_lower = str(col).lower()
            series = df[col]
            unique_pct = (series.nunique() / len(series)) * 100 if len(series) > 0 else 0
            
            if any(kw in col_lower for kw in ['_id', 'id', 'key', 'uuid', 'guid', 'serial', 'sequence']) and unique_pct > 95:
                categories['unique_identifiers'].append(col)
            elif any(kw in col_lower for kw in ['name', 'number', 'email', 'phone', 'mobile', 'tax', 'pan', 'gstin', 'account', 'code', 'vendor', 'supplier', 'customer']):
                categories['critical_business'].append(col)
            elif any(kw in col_lower for kw in ['batch', 'import', 'action', 'status', 'created', 'updated', 'modified', 'date', 'time', 'user']):
                categories['metadata'].append(col)
            else:
                categories['descriptive'].append(col)
        
        return categories
    
    col_categories = _categorize_columns(df)
    all_duplicate_results = []
    processed_indices = set()
    
    all_comparison_cols = [col for col in df.columns if col not in col_categories['unique_identifiers']]
    if not all_comparison_cols:
        all_comparison_cols = df.columns.tolist()
    
    # STRATEGY 1: Single Column Duplicates
    important_cols = col_categories['critical_business'] + col_categories['descriptive'][:5]
    
    for col in important_cols:
        col_dups = df[df.duplicated(subset=[col], keep=False)]
        
        if len(col_dups) > 0:
            valid_dup_indices = _has_valid_values(df, col_dups.index.tolist(), [col])
            
            if valid_dup_indices:
                new_indices = [idx for idx in valid_dup_indices if idx not in processed_indices]
                
                if new_indices:
                    new_dups = df.loc[new_indices].copy()
                    new_dups_sorted = new_dups.sort_values(by=col)
                    new_dups_sorted.insert(0, 'Matched_Fields', col)
                    
                    all_duplicate_results.append((f'Single: {col}', new_dups_sorted))
                    processed_indices.update(new_indices)
    
    # STRATEGY 2: Two Column Combinations
    if len(important_cols) >= 2:
        for col1, col2 in combinations(important_cols[:8], 2):
            two_col_dups = df[df.duplicated(subset=[col1, col2], keep=False)]
            
            if len(two_col_dups) > 0:
                valid_dup_indices = _has_valid_values(df, two_col_dups.index.tolist(), [col1, col2])
                
                if valid_dup_indices:
                    new_indices = [idx for idx in valid_dup_indices if idx not in processed_indices]
                    
                    if new_indices:
                        new_dups = df.loc[new_indices].copy()
                        new_dups_sorted = new_dups.sort_values(by=[col1, col2])
                        new_dups_sorted.insert(0, 'Matched_Fields', f'{col1}, {col2}')
                        
                        all_duplicate_results.append((f'Pair: {col1}+{col2}', new_dups_sorted))
                        processed_indices.update(new_indices)
    
    # STRATEGY 3: Three Column Combinations
    if len(important_cols) >= 3:
        for col1, col2, col3 in combinations(important_cols[:6], 3):
            three_col_dups = df[df.duplicated(subset=[col1, col2, col3], keep=False)]
            
            if len(three_col_dups) > 0:
                valid_dup_indices = _has_valid_values(df, three_col_dups.index.tolist(), [col1, col2, col3])
                
                if valid_dup_indices:
                    new_indices = [idx for idx in valid_dup_indices if idx not in processed_indices]
                    
                    if new_indices:
                        new_dups = df.loc[new_indices].copy()
                        new_dups_sorted = new_dups.sort_values(by=[col1, col2, col3])
                        new_dups_sorted.insert(0, 'Matched_Fields', f'{col1}, {col2}, {col3}')
                        
                        all_duplicate_results.append((f'Triple: {col1}+{col2}+{col3}', new_dups_sorted))
                        processed_indices.update(new_indices)
    
    # STRATEGY 4: Critical Business Fields
    if col_categories['critical_business']:
        biz_dups = df[df.duplicated(subset=col_categories['critical_business'], keep=False)]
        
        if len(biz_dups) > 0:
            valid_dup_indices = _has_valid_values(df, biz_dups.index.tolist(), col_categories['critical_business'])
            
            if valid_dup_indices:
                new_indices = [idx for idx in valid_dup_indices if idx not in processed_indices]
                
                if new_indices:
                    new_dups = df.loc[new_indices].copy()
                    new_dups_sorted = new_dups.sort_values(by=col_categories['critical_business'][:3])
                    new_dups_sorted.insert(0, 'Matched_Fields', ', '.join(col_categories['critical_business']))
                    
                    all_duplicate_results.append(('Business Keys', new_dups_sorted))
                    processed_indices.update(new_indices)
    
    # STRATEGY 5: Complete Row Duplicates
    complete_dups = df[df.duplicated(subset=all_comparison_cols, keep=False)]
    
    if len(complete_dups) > 0:
        valid_dup_indices = _has_valid_values(df, complete_dups.index.tolist(), all_comparison_cols)
        
        if valid_dup_indices:
            new_indices = [idx for idx in valid_dup_indices if idx not in processed_indices]
            
            if new_indices:
                new_dups = df.loc[new_indices].copy()
                new_dups_sorted = new_dups.sort_values(by=all_comparison_cols[:3])
                new_dups_sorted.insert(0, 'Matched_Fields', 'All fields')
                
                all_duplicate_results.append(('Complete Match', new_dups_sorted))
                processed_indices.update(new_indices)
    
    # Write results
    if all_duplicate_results:
        combined_results = []
        for tier_name, tier_df in all_duplicate_results:
            combined_results.append(tier_df)
        
        if combined_results:
            final_duplicates = pd.concat(combined_results, ignore_index=True)
            final_duplicates.to_excel(writer, sheet_name='Exact Duplicate', index=False)
        else:
            pd.DataFrame({
                'Message': ['No duplicates found (null/empty values excluded)']
            }).to_excel(writer, sheet_name='Exact Duplicate', index=False)
    else:
        pd.DataFrame({
            'Message': ['No duplicates detected (null/empty values excluded)'],
            'Detection_Method': ['Partial & Complete match analysis'],
            'Columns_Analyzed': [f'{len(all_comparison_cols)} columns']
        }).to_excel(writer, sheet_name='Exact Duplicate', index=False)
