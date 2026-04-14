"""
Simplified Data Profiler Engine for Template Mapping Tool
Adapted from DataProfilingTool
"""

from typing import Dict, List, Any
import pandas as pd
from dataclasses import dataclass, field

from config.settings import PROFILER_STRING_STATS_CHUNK


def _string_length_stats_chunked(series: pd.Series) -> tuple:
    """Min/max/mean string length without one giant astype(str) allocation."""
    s = series.dropna()
    n = len(s)
    if n == 0:
        return 0, 0, 0.0
    chunk = max(1, PROFILER_STRING_STATS_CHUNK)
    min_l = None
    max_l = None
    sum_l = 0
    for start in range(0, n, chunk):
        part = s.iloc[start : start + chunk].astype(str).str.len()
        min_l = int(part.min()) if min_l is None else min(min_l, int(part.min()))
        max_l = int(part.max()) if max_l is None else max(max_l, int(part.max()))
        sum_l += float(part.sum())
    return min_l, max_l, sum_l / n


@dataclass
class ColumnProfile:
    """Column profiling data structure"""
    column_name: str
    dtype: str
    total_rows: int
    null_count: int
    null_percentage: float
    unique_count: int
    unique_percentage: float
    duplicate_count: int
    non_null_count: int = 0
    non_null_percentage: float = 0.0
    duplicate_percentage: float = 0.0
    min_length: int = 0
    max_length: int = 0
    avg_length: float = 0.0
    sample_values: List[Any] = field(default_factory=list)
    special_chars: List[str] = field(default_factory=list)
    risk_score: int = 0
    risk_level: str = "Low"


class SimpleProfiler:
    """Simplified profiler for source data"""
    
    def __init__(self, df: pd.DataFrame):
        # Reference only — analyze_column does not mutate the frame
        self.df = df
        self.column_profiles: Dict[str, ColumnProfile] = {}
    
    def analyze_column(self, column: str) -> ColumnProfile:
        """Analyze a single column"""
        series = self.df[column]
        total_rows = len(series)
        
        # Basic stats
        null_count = series.isnull().sum()
        null_percentage = (null_count / total_rows) * 100 if total_rows > 0 else 0
        non_null_count = total_rows - null_count
        non_null_percentage = 100 - null_percentage
        
        unique_count = series.nunique()
        unique_percentage = (unique_count / total_rows) * 100 if total_rows > 0 else 0
        duplicate_count = total_rows - unique_count
        duplicate_percentage = (duplicate_count / total_rows) * 100 if total_rows > 0 else 0
        
        # Length analysis for text columns (chunked for large series)
        min_length, max_length, avg_length = 0, 0, 0.0
        if pd.api.types.is_string_dtype(series) or series.dtype == 'object':
            min_length, max_length, avg_length = _string_length_stats_chunked(series)
        
        # Sample values
        sample_values = series.dropna().head(3).tolist()
        
        # Special characters detection (simplified)
        special_chars = []
        if pd.api.types.is_string_dtype(series) or series.dtype == 'object':
            chunk = max(1, PROFILER_STRING_STATS_CHUNK)
            for char in ['@', '#', '$', '%', '&', '*', '!', '?']:
                found = False
                for start in range(0, total_rows, chunk):
                    sl = series.iloc[start : start + chunk].dropna().astype(str)
                    if len(sl) and sl.str.contains(char, regex=False).any():
                        found = True
                        break
                if found:
                    special_chars.append(char)
        
        # Risk assessment
        risk_score = 0
        if null_percentage > 50:
            risk_score += 40
        elif null_percentage > 20:
            risk_score += 20
        
        if duplicate_percentage > 50 and unique_count > 5:
            risk_score += 30
        
        if len(special_chars) > 3:
            risk_score += 15
        
        risk_level = "High" if risk_score >= 60 else "Medium" if risk_score >= 30 else "Low"
        
        return ColumnProfile(
            column_name=column,
            dtype=str(series.dtype),
            total_rows=total_rows,
            null_count=null_count,
            null_percentage=null_percentage,
            unique_count=unique_count,
            unique_percentage=unique_percentage,
            duplicate_count=duplicate_count,
            non_null_count=non_null_count,
            non_null_percentage=non_null_percentage,
            duplicate_percentage=duplicate_percentage,
            min_length=min_length,
            max_length=max_length,
            avg_length=avg_length,
            sample_values=sample_values,
            special_chars=special_chars,
            risk_score=risk_score,
            risk_level=risk_level
        )
    
    def profile_all(self) -> Dict[str, ColumnProfile]:
        """Profile all columns"""
        for col in self.df.columns:
            self.column_profiles[col] = self.analyze_column(col)
        return self.column_profiles
