"""
Data Cleaning Module - Production Enhancement
Automatically cleans data before profiling
"""

import pandas as pd
import numpy as np
import re
from typing import Dict, List, Tuple


class DataCleaner:
    """Automatic data cleaning for production-ready profiling"""
    
    def __init__(self):
        self.cleaning_report = {
            'whitespace_cleaned': 0,
            'nulls_standardized': 0,
            'duplicate_spaces_removed': 0,
            'columns_affected': []
        }
    
    def clean(self, df: pd.DataFrame, auto_clean: bool = True) -> Tuple[pd.DataFrame, Dict]:
        """
        Clean dataframe with comprehensive data quality fixes
        
        Args:
            df: Input dataframe
            auto_clean: If True, automatically clean. If False, just report issues
            
        Returns:
            Tuple of (cleaned_df, cleaning_report)
        """
        df_cleaned = df.copy()
        
        if auto_clean:
            # 1. Strip leading/trailing whitespaces
            df_cleaned = self._strip_whitespaces(df_cleaned)
            
            # 2. Standardize NULL values
            df_cleaned = self._standardize_nulls(df_cleaned)
            
            # 3. Remove duplicate spaces
            df_cleaned = self._remove_duplicate_spaces(df_cleaned)
            
            # 4. Clean special cases
            df_cleaned = self._clean_special_cases(df_cleaned)
        
        return df_cleaned, self.cleaning_report
    
    def _strip_whitespaces(self, df: pd.DataFrame) -> pd.DataFrame:
        """Remove leading and trailing whitespaces from text columns"""
        whitespace_count = 0
        affected_cols = []
        
        for col in df.select_dtypes(include=['object']).columns:
            # Check if column has whitespace issues
            has_leading = df[col].astype(str).str.match(r'^\s+.*').sum()
            has_trailing = df[col].astype(str).str.match(r'.*\s+$').sum()
            
            if has_leading > 0 or has_trailing > 0:
                df[col] = df[col].str.strip()
                whitespace_count += has_leading + has_trailing
                affected_cols.append(col)
        
        self.cleaning_report['whitespace_cleaned'] = whitespace_count
        self.cleaning_report['columns_affected'].extend(affected_cols)
        
        return df
    
    def _standardize_nulls(self, df: pd.DataFrame) -> pd.DataFrame:
        """Standardize different NULL representations to pandas NaN"""
        null_variants = ['NULL', 'Null', 'null', 'NONE', 'None', 'none', 
                        'NA', 'N/A', 'n/a', 'NaN', 'nan', '', ' ', '  ']
        
        nulls_standardized = 0
        
        for col in df.select_dtypes(include=['object']).columns:
            # Count nulls before
            before_nulls = df[col].isin(null_variants).sum()
            
            # Replace with NaN
            df[col] = df[col].replace(null_variants, np.nan)
            
            nulls_standardized += before_nulls
        
        self.cleaning_report['nulls_standardized'] = nulls_standardized
        
        return df
    
    def _remove_duplicate_spaces(self, df: pd.DataFrame) -> pd.DataFrame:
        """Remove duplicate spaces within text"""
        dup_spaces_count = 0
        
        for col in df.select_dtypes(include=['object']).columns:
            # Check for duplicate spaces
            has_dup_spaces = df[col].astype(str).str.contains(r'\s{2,}', na=False).sum()
            
            if has_dup_spaces > 0:
                df[col] = df[col].str.replace(r'\s+', ' ', regex=True)
                dup_spaces_count += has_dup_spaces
        
        self.cleaning_report['duplicate_spaces_removed'] = dup_spaces_count
        
        return df
    
    def _clean_special_cases(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean special edge cases"""
        # Remove zero-width characters
        zero_width_chars = dict.fromkeys(map(ord, "\u200b\u200c\u200d\ufeff"), None)
        for col in df.select_dtypes(include=['object']).columns:
            df[col] = df[col].apply(
                lambda value: value.translate(zero_width_chars) if isinstance(value, str) else value
            )
        
        return df
    
    def get_cleaning_summary(self) -> str:
        """Get human-readable cleaning summary"""
        report = self.cleaning_report
        
        summary = f"""
Data Cleaning Summary:
- Whitespace issues fixed: {report['whitespace_cleaned']} occurrences
- NULL values standardized: {report['nulls_standardized']} values
- Duplicate spaces removed: {report['duplicate_spaces_removed']} occurrences
- Columns affected: {len(set(report['columns_affected']))} columns
"""
        return summary


class DataValidator:
    """Validate data against business rules"""
    
    def __init__(self):
        self.validation_rules = {}
        self.violations = []
    
    def add_rule(self, column: str, rule_type: str, **kwargs):
        """Add validation rule for a column"""
        if column not in self.validation_rules:
            self.validation_rules[column] = []
        
        self.validation_rules[column].append({
            'type': rule_type,
            'params': kwargs
        })
    
    def validate(self, df: pd.DataFrame) -> List[Dict]:
        """Validate dataframe against all rules"""
        self.violations = []
        
        for column, rules in self.validation_rules.items():
            if column not in df.columns:
                self.violations.append({
                    'column': column,
                    'rule': 'existence',
                    'severity': 'Critical',
                    'message': f'Column {column} not found in dataset'
                })
                continue
            
            for rule in rules:
                self._check_rule(df, column, rule)
        
        return self.violations
    
    def _check_rule(self, df: pd.DataFrame, column: str, rule: Dict):
        """Check a single validation rule"""
        rule_type = rule['type']
        params = rule['params']
        
        if rule_type == 'required':
            null_count = df[column].isnull().sum()
            if null_count > 0:
                self.violations.append({
                    'column': column,
                    'rule': 'required',
                    'severity': 'High',
                    'message': f'{column} has {null_count} missing values (required field)',
                    'count': null_count
                })
        
        elif rule_type == 'unique':
            dup_count = df[column].duplicated().sum()
            if dup_count > 0:
                self.violations.append({
                    'column': column,
                    'rule': 'unique',
                    'severity': 'High',
                    'message': f'{column} has {dup_count} duplicate values (should be unique)',
                    'count': dup_count
                })
        
        elif rule_type == 'data_type':
            expected_type = params.get('expected')
            if expected_type == 'integer':
                non_int = df[column].dropna().apply(lambda x: not str(x).isdigit()).sum()
                if non_int > 0:
                    self.violations.append({
                        'column': column,
                        'rule': 'data_type',
                        'severity': 'Medium',
                        'message': f'{column} has {non_int} non-integer values',
                        'count': non_int
                    })
        
        elif rule_type == 'pattern':
            pattern = params.get('pattern')
            if pattern:
                non_matching = ~df[column].dropna().astype(str).str.match(pattern)
                count = non_matching.sum()
                if count > 0:
                    self.violations.append({
                        'column': column,
                        'rule': 'pattern',
                        'severity': 'Medium',
                        'message': f'{column} has {count} values not matching pattern {pattern}',
                        'count': count
                    })
        
        elif rule_type == 'min_length':
            min_len = params.get('value', 0)
            short_values = df[column].dropna().astype(str).str.len() < min_len
            count = short_values.sum()
            if count > 0:
                self.violations.append({
                    'column': column,
                    'rule': 'min_length',
                    'severity': 'Low',
                    'message': f'{column} has {count} values shorter than {min_len} characters',
                    'count': count
                })
        
        elif rule_type == 'max_length':
            max_len = params.get('value', 1000)
            long_values = df[column].dropna().astype(str).str.len() > max_len
            count = long_values.sum()
            if count > 0:
                self.violations.append({
                    'column': column,
                    'rule': 'max_length',
                    'severity': 'Low',
                    'message': f'{column} has {count} values longer than {max_len} characters',
                    'count': count
                })


class QualityScorer:
    """Calculate comprehensive data quality scores"""
    
    @staticmethod
    def calculate_quality_score(df: pd.DataFrame, profiles: Dict) -> Dict:
        """Calculate overall data quality score"""
        total_rows = len(df)
        total_cols = len(df.columns)
        total_cells = total_rows * total_cols
        
        if total_cells == 0:
            return {
                'overall_score': 0,
                'completeness': 0,
                'uniqueness': 0,
                'consistency': 0,
                'accuracy': 0
            }
        
        # 1. Completeness Score (0-100)
        missing_cells = sum(p.null_count for p in profiles.values())
        completeness = ((total_cells - missing_cells) / total_cells) * 100
        
        # 2. Uniqueness Score (0-100)
        # Higher uniqueness in key columns is better
        uniqueness_scores = []
        for p in profiles.values():
            # Penalize columns with very low uniqueness (likely not useful)
            if p.unique_percentage < 1:
                uniqueness_scores.append(0)
            elif p.unique_percentage > 95:
                uniqueness_scores.append(100)
            else:
                uniqueness_scores.append(p.unique_percentage)
        
        uniqueness = sum(uniqueness_scores) / len(uniqueness_scores) if uniqueness_scores else 0
        
        # 3. Consistency Score (0-100)
        # Check for data type consistency, whitespace issues, etc.
        consistency_issues = 0
        
        for col in df.select_dtypes(include=['object']).columns:
            # Check for whitespace issues
            has_leading = df[col].astype(str).str.match(r'^\s+.*').sum()
            has_trailing = df[col].astype(str).str.match(r'.*\s+$').sum()
            consistency_issues += has_leading + has_trailing
            
            # Check for inconsistent null representations
            null_variants = df[col].isin(['NULL', 'Null', 'null', 'NA', 'N/A', '']).sum()
            consistency_issues += null_variants
        
        consistency = max(0, 100 - (consistency_issues / total_cells * 100))
        
        # 4. Accuracy Score (0-100)
        # Based on risk scores from profiles
        risk_scores = [getattr(p, 'risk_score', 0) for p in profiles.values()]
        avg_risk = sum(risk_scores) / len(risk_scores) if risk_scores else 0
        accuracy = max(0, 100 - avg_risk)
        
        # Overall Score (weighted average)
        overall_score = (
            completeness * 0.35 +
            uniqueness * 0.20 +
            consistency * 0.25 +
            accuracy * 0.20
        )
        
        return {
            'overall_score': round(overall_score, 1),
            'completeness': round(completeness, 1),
            'uniqueness': round(uniqueness, 1),
            'consistency': round(consistency, 1),
            'accuracy': round(accuracy, 1),
            'grade': QualityScorer._get_grade(overall_score)
        }
    
    @staticmethod
    def _get_grade(score: float) -> str:
        """Convert score to letter grade"""
        if score >= 90:
            return 'A (Excellent)'
        elif score >= 80:
            return 'B (Good)'
        elif score >= 70:
            return 'C (Fair)'
        elif score >= 60:
            return 'D (Poor)'
        else:
            return 'F (Critical)'
