"""
Data Profiling UI Component for Template Mapping Tool
EXACT COPY of logic from DataProfilingTool - NO MODIFICATIONS
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import re
from datetime import datetime
from typing import List, Optional
from dataclasses import dataclass, field
from core.profiler_engine import SimpleProfiler
from core.data_cleaner import DataCleaner, DataValidator, QualityScorer
from features.export_report.generator_complete import generate_complete_profiling_report
from config.settings import PROFILE_DUP_DISPLAY_MAX_KEYS, QUALITY_WHITESPACE_CHUNK


@dataclass
class DuplicateGroup:
    """Duplicate group data structure - EXACT COPY from DataProfilingTool"""
    group_id: int
    indices: List[int]
    values: List[dict]
    match_type: str
    similarity_score: Optional[float] = None
    key_columns: List[str] = field(default_factory=list)
    representative_value: Optional[str] = None


# ==========================================
# HELPER FUNCTIONS - EXACT COPY from DataProfilingTool
# ==========================================

def safe_get_special_chars(prof):
    """EXACT COPY from DataProfilingTool"""
    try:
        if hasattr(prof, 'special_chars') and prof.special_chars:
            return [c for c in prof.special_chars if isinstance(c, dict) and 'count' in c]
    except: 
        pass
    return []


def find_exact_duplicates(df: pd.DataFrame, subset: Optional[List[str]] = None) -> List[DuplicateGroup]:
    """Find exact duplicate rows - EXACT COPY from DataProfilingTool/utils/data_utils.py"""
    try:
        if subset is None:
            subset = df.columns.tolist()
        
        # CRITICAL FIX: Filter out rows where ALL subset columns are null
        # This prevents null-to-null matches
        subset_df = df[subset]
        
        # Create mask for rows that have at least one non-null value in subset columns
        has_non_null = subset_df.notna().any(axis=1)
        
        # Only consider rows with at least one non-null value
        valid_df = df[has_non_null]
        
        if len(valid_df) == 0:
            return []
        
        # Use pandas hashing which is much faster than row-by-row
        # hash_pandas_object returns a Series of uint64 hashes
        hashes = pd.util.hash_pandas_object(valid_df[subset], index=False)
        
        # Find duplicates based on hash
        # duplicated(keep=False) marks all duplicates as True
        dup_mask = hashes.duplicated(keep=False)
        
        if not dup_mask.any():
            return []
            
        # Get only the duplicate hashes and their indices
        dup_hashes = hashes[dup_mask]
        
        # Group indices by hash
        # This is much faster than iterating
        hash_groups = dup_hashes.groupby(dup_hashes).groups
        
        groups = []
        group_id = 1
        
        for hash_val, indices in hash_groups.items():
            # hash_groups returns indices as Index object, convert to list
            idx_list = indices.tolist()
            
            if len(idx_list) < 2:
                continue
            
            # Additional check: Ensure the group doesn't consist of all-null rows
            # (This should already be filtered, but double-check)
            group_subset = valid_df.loc[idx_list, subset]
            if group_subset.isna().all().all():
                continue
                
            # Get representative value safely
            try:
                first_row_idx = idx_list[0]
                rep_val = str(valid_df.loc[first_row_idx, subset].to_dict())
            except:
                rep_val = "Error getting value"
            
            # For the group values, we must access the main DF
            # Optimization: If group is huge (>100), only store first 100 to save memory in state
            stored_indices = idx_list
            if len(idx_list) > 100:
                stored_values = [valid_df.loc[i, subset].to_dict() for i in idx_list[:100]]
            else:
                stored_values = [valid_df.loc[i, subset].to_dict() for i in idx_list]
            
            groups.append(DuplicateGroup(
                group_id=group_id,
                indices=stored_indices,
                values=stored_values,
                match_type='exact',
                similarity_score=100.0,
                key_columns=subset,
                representative_value=rep_val
            ))
            group_id += 1
            
        return groups
        
    except Exception as e:
        # Fallback to empty if error
        print(f"Error in find_exact_duplicates: {e}")
        return []


def find_duplicate_groups(df, col):
    """Find duplicate groups in a column - EXACT COPY from DataProfilingTool"""
    if col not in df.columns:
        return []

    value_counts = df[col].value_counts()
    duplicates = value_counts[value_counts > 1]

    groups = []
    for val, count in duplicates.head(10).items():
        matching_rows = df[df[col] == val]
        groups.append({
            'value': str(val)[:50],
            'count': int(count),
            'percentage': round((count / len(df)) * 100, 2),
            'row_indices': matching_rows.index.tolist()[:5]
        })

    return groups


def get_duplicate_count_values(df, col, max_items=None):
    """Get duplicate values with counts (same logic as before; optional display cap for huge cardinalities)."""
    if col not in df.columns:
        return "N/A"
    
    try:
        # Get value counts including nulls
        value_counts = df[col].value_counts(dropna=False)
        
        # Separate null and non-null duplicates
        duplicates = value_counts[value_counts > 1]
        
        if len(duplicates) == 0:
            return "No duplicates"
        
        dup_strings = []
        # None = list all keys, but cap string length for UI stability on GB-scale data
        cap = PROFILE_DUP_DISPLAY_MAX_KEYS if max_items is None else max_items
        n = 0
        for val, count in duplicates.items():
            if cap is not None and n >= cap:
                remaining = len(duplicates) - n
                if remaining > 0:
                    dup_strings.append(
                        f"… and {remaining:,} more duplicate value(s) (list capped for display)"
                    )
                break
            if pd.isna(val) or (isinstance(val, str) and val.strip() == ''):
                dup_strings.append(f"Missing Values({count})")
            else:
                val_str = str(val).strip()
                dup_strings.append(f"{val_str}({count})")
            n += 1
        
        return ", ".join(dup_strings)
    except Exception as e:
        return "Error"


# ==========================================
# UI RENDERING FUNCTIONS
# ==========================================


def render_data_profiling():
    """Render data profiling tab for source data"""
    
    # Check if source data is loaded
    if not st.session_state.source_file.selected_sheet:
        st.info("📤 Please upload source data first (Step 2)")
        return
    
    df = st.session_state.source_file.data.get(
        st.session_state.source_file.selected_sheet,
        pd.DataFrame()
    )
    
    if df.empty or len(df.columns) == 0:
        st.info("📤 No source data loaded")
        return
    
    if len(df) > 250_000:
        st.info(
            f"Large dataset ({len(df):,} rows): profiling uses chunked statistics where needed. "
            "Validation still evaluates every row."
        )
    
    # Get source filename
    source_filename = st.session_state.source_file.name
    
    st.markdown(f'<div class="section-title">📊 Data Profile: {source_filename}</div>', 
                unsafe_allow_html=True)
    
  
    
    # Data Cleaning Section
    st.markdown('<div class="section-container">', unsafe_allow_html=True)

    
    auto_clean = st.checkbox(
        "Auto-clean data before profiling", 
        value=True,
        help="Automatically remove whitespaces, standardize NULLs, and fix common data quality issues"
    )
        
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown("---")
    
    # Initialize profiler in session state
    if 'profiler' not in st.session_state or st.session_state.get('profiler_df_id') != id(df):
        with st.spinner("🔍 Analyzing data..."):
            # Clean data if auto_clean is enabled
            df_to_profile = df.copy()
            cleaning_report = None
            
            if auto_clean:
                cleaner = DataCleaner()
                df_to_profile, cleaning_report = cleaner.clean(df_to_profile, auto_clean=True)
                st.session_state.cleaning_report = cleaning_report
                st.session_state.cleaned_df = df_to_profile
            
            profiler = SimpleProfiler(df_to_profile)
            profiles = profiler.profile_all()
            
            # Calculate quality scores
            quality_scores = QualityScorer.calculate_quality_score(df_to_profile, profiles)
            
            st.session_state.profiler = profiler
            st.session_state.profiles = profiles
            st.session_state.quality_scores = quality_scores
            st.session_state.profiler_df_id = id(df)
    
    profiler = st.session_state.profiler
    profiles = st.session_state.profiles
    quality_scores = st.session_state.get('quality_scores', {})
    cleaning_report = st.session_state.get('cleaning_report', None)
    df_to_use = st.session_state.get('cleaned_df', df)
    
    # Show cleaning summary if data was cleaned
    if cleaning_report and auto_clean:
        if cleaning_report['whitespace_cleaned'] > 0 or cleaning_report['nulls_standardized'] > 0:
            with st.expander("🧹 Data Cleaning Summary", expanded=False):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Whitespace Fixed", cleaning_report['whitespace_cleaned'])
                with col2:
                    st.metric("NULLs Standardized", cleaning_report['nulls_standardized'])
                with col3:
                    st.metric("Columns Affected", len(set(cleaning_report['columns_affected'])))
    
    # Executive Dashboard
    _render_executive_dashboard(df_to_use, profiles, quality_scores)
    
    # Tabs for different views (Column Profiles tab removed from UI)
    tabs = st.tabs([
        "Overview", 
        "🔍 Duplicates",
        "✅ Data Quality",
        "📥 Export Report"
    ])
    
    with tabs[0]:
        _render_overview_tab(df_to_use, profiles)
    
    with tabs[1]:
        _render_duplicates_tab(df_to_use, profiles)
    
    with tabs[2]:
        _render_quality_tab(df_to_use, profiles, quality_scores, cleaning_report)
    
    with tabs[3]:
        _render_export_tab(df_to_use, profiles, source_filename)
    
    # Navigation Buttons at Bottom - Similar to Upload Source Tab
    st.markdown("---")
    nav_col1, nav_col2 = st.columns(2)
    
    with nav_col1:
        if st.button("⬅️ Back to Upload Source", use_container_width=True, key='btn_profile_to_source_bottom'):
            st.session_state.active_tab = 1  # Go to Upload Source Records tab
            st.session_state.tab_change_requested = True
            st.rerun()
    
    with nav_col2:
        if st.button("➡️ Next: Validation Rules", type="primary", use_container_width=True, key='btn_profile_to_rules_bottom'):
            st.session_state.active_tab = 3  # Go to Validation Rules tab
            st.session_state.tab_change_requested = True
            st.rerun()


def _render_executive_dashboard(df: pd.DataFrame, profiles: dict, quality_scores: dict):
    """Render executive KPI dashboard with quality scores"""
    total_rows = len(df)
    total_cols = len(df.columns)
    total_cells = total_rows * total_cols
    missing_cells = sum(p.null_count for p in profiles.values())
    completeness = ((total_cells - missing_cells) / total_cells) * 100 if total_cells else 0
    
    # Get quality scores
    overall_quality = quality_scores.get('overall_score', 0)
    quality_grade = quality_scores.get('grade', 'N/A')
    
    cols = st.columns(6)
    kpi_data = [
        ("📊", "Rows", f"{total_rows:,}"),
        ("📁", "Columns", total_cols),
        ("⭐", "Quality", f"{overall_quality:.0f}%"),
        ("✅", "Completeness", f"{completeness:.1f}%"),
        ("⚠️", "Missing", f"{missing_cells:,}"),
        ("🎯", "Grade", quality_grade.split('(')[0].strip())
    ]
    
    for col, (icon, label, value) in zip(cols, kpi_data):
        with col:
            # Color based on quality
            if label == "Quality":
                if overall_quality >= 90:
                    color = "linear-gradient(135deg, #00c853 0%, #64dd17 100%)"
                elif overall_quality >= 80:
                    color = "linear-gradient(135deg, #2196f3 0%, #00bcd4 100%)"
                elif overall_quality >= 70:
                    color = "linear-gradient(135deg, #ff9800 0%, #ffc107 100%)"
                else:
                    color = "linear-gradient(135deg, #f44336 0%, #e91e63 100%)"
            else:
                color = "linear-gradient(135deg, #667eea 0%, #764ba2 100%)"
            
            st.markdown(f"""
            <div style="background: {color}; 
                        padding: 15px; border-radius: 10px; text-align: center; color: white;">
                <div style="font-size: 24px;">{icon}</div>
                <div style="font-size: 12px; opacity: 0.9;">{label}</div>
                <div style="font-size: 20px; font-weight: bold;">{value}</div>
            </div>
            """, unsafe_allow_html=True)
    
    st.divider()


def _render_overview_tab(df: pd.DataFrame, profiles: dict):
    """Render overview with table only - charts removed"""
    
    # Prepare data for table
    profile_data = []
    for col, p in profiles.items():
        profile_data.append({
            'Column Name': col,
            'Data Type': p.dtype,
            'Null %': p.null_percentage,
            'Unique %': p.unique_percentage,
            'Duplicate Count': p.duplicate_count,
            'Risk Level': p.risk_level,
            'Risk Score': p.risk_score
        })
    
    profile_df = pd.DataFrame(profile_data)
    
    # Detailed Table Only - No Charts
    st.markdown("### 📋 Detailed Profile Table")
    st.dataframe(profile_df, use_container_width=True, height=600)


def _render_profiles_tab(df: pd.DataFrame, profiles: dict):
    """Render detailed column profiles - EXACT COPY from DataProfilingTool"""
    
    c1, c2, c3 = st.columns([3, 1, 1])
    with c1: 
        search = st.text_input("🔍 Search columns", key="profile_search")
    with c2: 
        dtype_filter = st.selectbox("Type", ["All", "Numeric", "Text", "Date", "High Risk"], key="profile_dtype")
    with c3: 
        sort_by = st.selectbox("Sort", ["Name", "Null %", "Uniqueness", "Risk"], key="profile_sort")

    filtered = {k: v for k, v in profiles.items() if not search or search.lower() in k.lower()}

    if dtype_filter == "Numeric":
        filtered = {k: v for k, v in filtered.items() if any(t in v.dtype for t in ['int', 'float'])}
    elif dtype_filter == "Text":
        filtered = {k: v for k, v in filtered.items() if v.dtype == 'object'}
    elif dtype_filter == "Date":
        filtered = {k: v for k, v in filtered.items() if 'date' in v.dtype}
    elif dtype_filter == "High Risk":
        filtered = {k: v for k, v in filtered.items() if getattr(v, 'risk_level', 'Low') == 'High'}

    if sort_by == "Null %":
        filtered = dict(sorted(filtered.items(), key=lambda x: x[1].null_percentage, reverse=True))
    elif sort_by == "Uniqueness":
        filtered = dict(sorted(filtered.items(), key=lambda x: x[1].unique_percentage, reverse=True))
    elif sort_by == "Risk":
        filtered = dict(sorted(filtered.items(), key=lambda x: getattr(x[1], 'risk_score', 0), reverse=True))

    st.write(f"Showing {len(filtered)} of {len(profiles)} columns")

    cols_per_row = 2
    items = list(filtered.items())  # Show all columns

    for i in range(0, len(items), cols_per_row):
        cols = st.columns(cols_per_row)

        for col_ui, (col, prof) in zip(cols, items[i:i+cols_per_row]):
            with col_ui:
                with st.expander(
                    f"📊 {col} | {prof.dtype} | Quality: {100-prof.null_percentage:.0f}%"
                ):
                    c1, c2, c3, c4 = st.columns(4)

                    with c1:
                        st.markdown("**Volume**")
                        st.write(f"Rows: {prof.total_rows:,}")
                        st.write(f"Non-null: {getattr(prof, 'non_null_count', prof.total_rows - prof.null_count):,}")
                        st.write(f"Null: {prof.null_count:,} ({prof.null_percentage:.1f}%)")

                    with c2:
                        st.markdown("**Uniqueness**")
                        dup = prof.total_rows - prof.unique_count
                        st.write(f"Unique: {prof.unique_count:,}")
                        st.write(f"Duplicates: {dup:,}")
                        st.write(f"Unique %: {prof.unique_percentage:.1f}%)")

                    with c3:
                        st.markdown("**Length**")
                        st.write(f"Min: {getattr(prof, 'min_length', 'N/A')}")
                        st.write(f"Max: {getattr(prof, 'max_length', 'N/A')}")
                        st.write(f"Avg: {getattr(prof, 'avg_length', 0):.1f}")

                    with c4:
                        st.markdown("**Risk**")
                        risk = getattr(prof, 'risk_level', 'Low')
                        color = "🔴" if risk == "High" else "🟡" if risk == "Medium" else "🟢"
                        st.write(f"Level: {color} {risk}")
                        st.write(f"Score: {getattr(prof, 'risk_score', 0)}/100")

                    # Show duplicate count values - EXACT COPY from DataProfilingTool
                    if prof.unique_count < prof.total_rows:
                        dup_values_str = get_duplicate_count_values(df, col, max_items=None)
                        st.markdown("**Duplicate Count Values**")
                        st.caption(dup_values_str)

                    if prof.unique_count < prof.total_rows:
                        dups = find_duplicate_groups(df, col)
                        if dups:
                            with st.expander(f"⚠️ Duplicates ({len(dups)} groups)"):
                                for d in dups[:5]:
                                    st.write(
                                        f"- Value '{d['value'][:30]}' "
                                        f"appears {d['count']} times ({d['percentage']}%)"
                                    )


def _render_duplicates_tab(df: pd.DataFrame, profiles: dict):
    """Render duplicates analysis - EXACT LOGIC from DataProfilingTool"""
    
    st.markdown("### 🔍 Duplicate Analysis")
    
    # Column-wise duplicates
    st.markdown("#### Duplicates by Column")
    
    dup_data = []
    for col, p in profiles.items():
        if p.duplicate_count > 0:
            # Use exact function from DataProfilingTool
            dup_values_str = get_duplicate_count_values(df, col, max_items=None)
            
            dup_data.append({
                'Column': col,
                'Duplicate Count': p.duplicate_count,
                'Duplicate %': f"{p.duplicate_percentage:.2f}%",
                'Duplicate Values': dup_values_str
            })
    
    if dup_data:
        dup_df = pd.DataFrame(dup_data)
        st.dataframe(dup_df, use_container_width=True, height=400)
    else:
        st.success("✅ No column-level duplicates found!")
    
    # Exact duplicate rows - using exact function from DataProfilingTool
    st.markdown("#### Exact Duplicate Rows")
    
    exact_dup_groups = find_exact_duplicates(df)
    
    if len(exact_dup_groups) > 0:
        total_dup_rows = sum(len(g.indices) for g in exact_dup_groups)
        st.warning(f"⚠️ Found {len(exact_dup_groups)} duplicate groups with {total_dup_rows} total duplicate rows")
        
        # Show summary
        summary_data = []
        for group in exact_dup_groups[:20]:  # Show first 20 groups
            summary_data.append({
                'Group ID': group.group_id,
                'Duplicate Count': len(group.indices),
                'Representative Value': group.representative_value[:100] if group.representative_value else 'N/A'
            })
        
        if summary_data:
            summary_df = pd.DataFrame(summary_data)
            st.dataframe(summary_df, use_container_width=True)
        
        # Show detailed view
        with st.expander("View Detailed Duplicate Rows"):
            # Create a dataframe with all duplicate rows
            all_dup_indices = []
            for group in exact_dup_groups:
                all_dup_indices.extend(group.indices)
            
            if all_dup_indices:
                dup_rows_df = df.loc[all_dup_indices].head(100)
                st.dataframe(dup_rows_df, use_container_width=True)
                st.caption(f"Showing first 100 of {len(all_dup_indices)} duplicate rows")
    else:
        st.success("✅ No exact duplicate rows found!")


def _render_quality_tab(df: pd.DataFrame, profiles: dict, quality_scores: dict, cleaning_report: dict):
    """Render data quality analysis tab - NEW ENHANCEMENT"""
    
    st.markdown("### 📊 Data Quality Analysis")
    
    # Quality Score Overview
    st.markdown("#### Overall Quality Metrics")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    metrics = [
        ("Overall Score", quality_scores.get('overall_score', 0), "⭐"),
        ("Completeness", quality_scores.get('completeness', 0), "✅"),
        ("Uniqueness", quality_scores.get('uniqueness', 0), "🎯"),
        ("Consistency", quality_scores.get('consistency', 0), "🔄"),
        ("Accuracy", quality_scores.get('accuracy', 0), "✓")
    ]
    
    for col, (label, score, icon) in zip([col1, col2, col3, col4, col5], metrics):
        with col:
            # Color based on score
            if score >= 90:
                color = "#00c853"
            elif score >= 80:
                color = "#2196f3"
            elif score >= 70:
                color = "#ff9800"
            else:
                color = "#f44336"
            
            st.markdown(f"""
            <div style="background: white; border: 2px solid {color}; 
                        padding: 15px; border-radius: 10px; text-align: center;">
                <div style="font-size: 24px;">{icon}</div>
                <div style="font-size: 12px; color: #666;">{label}</div>
                <div style="font-size: 24px; font-weight: bold; color: {color};">{score:.1f}%</div>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown(f"**Quality Grade:** {quality_scores.get('grade', 'N/A')}")
    
    st.divider()
    
    # Data Quality Issues
    st.markdown("#### 🔍 Data Quality Issues")
    
    issues = []
    
    # Check for null values
    for col, p in profiles.items():
        if p.null_percentage > 0:
            severity = "Critical" if p.null_percentage > 50 else "High" if p.null_percentage > 20 else "Medium"
            issues.append({
                'Column': col,
                'Issue Type': 'Missing Values',
                'Severity': severity,
                'Count': p.null_count,
                'Percentage': f"{p.null_percentage:.2f}%",
                'Description': f'{p.null_count} missing values ({p.null_percentage:.1f}%)'
            })
    
    # Check for high duplicate rates
    for col, p in profiles.items():
        dup_pct = (p.duplicate_count / p.total_rows * 100) if p.total_rows > 0 else 0
        if dup_pct > 50 and p.unique_count > 5:
            severity = "Medium"
            issues.append({
                'Column': col,
                'Issue Type': 'High Duplicates',
                'Severity': severity,
                'Count': p.duplicate_count,
                'Percentage': f"{dup_pct:.2f}%",
                'Description': f'{p.duplicate_count} duplicate values ({dup_pct:.1f}%)'
            })
    
    # Check for whitespace issues (if not cleaned)
    if not cleaning_report or cleaning_report.get('whitespace_cleaned', 0) == 0:
        nrows = len(df)
        chunk = max(1, QUALITY_WHITESPACE_CHUNK)
        for col in df.select_dtypes(include=['object']).columns:
            has_leading = 0
            has_trailing = 0
            for start in range(0, nrows, chunk):
                chunk_s = df[col].iloc[start : start + chunk].astype(str)
                has_leading += int(chunk_s.str.match(r'^\s+.*').sum())
                has_trailing += int(chunk_s.str.match(r'.*\s+$').sum())
            
            if has_leading > 0 or has_trailing > 0:
                issues.append({
                    'Column': col,
                    'Issue Type': 'Whitespace',
                    'Severity': 'High',
                    'Count': has_leading + has_trailing,
                    'Percentage': f"{((has_leading + has_trailing) / nrows * 100):.2f}%",
                    'Description': f'{has_leading} leading, {has_trailing} trailing spaces'
                })
    
    # Check for inconsistent nulls
    for col in df.select_dtypes(include=['object']).columns:
        null_variants = df[col].isin(['NULL', 'Null', 'null', 'NA', 'N/A', '']).sum()
        if null_variants > 0:
            issues.append({
                'Column': col,
                'Issue Type': 'Inconsistent NULLs',
                'Severity': 'Medium',
                'Count': null_variants,
                'Percentage': f"{(null_variants / len(df) * 100):.2f}%",
                'Description': f'{null_variants} inconsistent NULL representations'
            })
    
    if issues:
        issues_df = pd.DataFrame(issues)
        
        # Sort by severity
        severity_order = {'Critical': 0, 'High': 1, 'Medium': 2, 'Low': 3}
        issues_df['_sort'] = issues_df['Severity'].map(severity_order)
        issues_df = issues_df.sort_values('_sort').drop('_sort', axis=1)
        
        # Color code severity
        def highlight_severity(row):
            if row['Severity'] == 'Critical':
                return ['background-color: #ffebee'] * len(row)
            elif row['Severity'] == 'High':
                return ['background-color: #fff3e0'] * len(row)
            elif row['Severity'] == 'Medium':
                return ['background-color: #fff9c4'] * len(row)
            else:
                return [''] * len(row)
        
        st.dataframe(
            issues_df.style.apply(highlight_severity, axis=1),
            use_container_width=True,
            height=400
        )
        
        # Summary
        st.markdown("#### Issue Summary")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            critical = len(issues_df[issues_df['Severity'] == 'Critical'])
            st.metric("Critical", critical, delta=None if critical == 0 else f"-{critical}")
        with col2:
            high = len(issues_df[issues_df['Severity'] == 'High'])
            st.metric("High", high, delta=None if high == 0 else f"-{high}")
        with col3:
            medium = len(issues_df[issues_df['Severity'] == 'Medium'])
            st.metric("Medium", medium, delta=None if medium == 0 else f"-{medium}")
        with col4:
            low = len(issues_df[issues_df['Severity'] == 'Low'])
            st.metric("Low", low, delta=None if low == 0 else f"-{low}")
    else:
        st.success("✅ No data quality issues found! Your data is in excellent condition.")
    
    st.divider()


def _render_export_tab(df: pd.DataFrame, profiles: dict, source_filename: str):
    """Render export options - EXACT SAME report as DataProfilingTool"""
    
    st.markdown("### 📥 Export Profiling Report")
    
    # Generate default filename (no UI input)
    base_name = os.path.splitext(str(source_filename))[0]
    safe_orig = re.sub(r'[^A-Za-z0-9_.-]', '_', base_name)
    default_filename = f"{safe_orig}_Data_Profile_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    if st.button("📥 Generate Excel Report", type="primary", use_container_width=True):
        with st.spinner("Generating complete report..."):
            try:
                excel_data = generate_complete_profiling_report(df, profiles, source_filename)
                
                st.download_button(
                    label="⬇️ Download Complete Report",
                    data=excel_data,
                    file_name=f"{default_filename}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
                
                st.success("✅ Report generated successfully!")
                
            except Exception as e:
                st.error(f"❌ Error generating report: {str(e)}")
                import traceback
                st.code(traceback.format_exc())
