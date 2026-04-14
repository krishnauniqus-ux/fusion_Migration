import streamlit as st
import pandas as pd
import numpy as np
import re
import json
import hashlib
import io
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, asdict, field
from enum import Enum
import warnings
import time
warnings.filterwarnings('ignore')

# Page configuration - MUST be first
st.set_page_config(
    page_title="Mapper Enterprise | Data Migration Platform",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =============================================================================
# ENTERPRISE CSS THEME
# =============================================================================
st.markdown("""
<style>
/* -------- GLOBAL -------- */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');
html, body, [class*="css"]  {
    font-family: 'Inter', sans-serif;
}
.stApp{
    background:#ffffff;
    color:#111827;
}
/* -------- TEXT -------- */
h1,h2,h3,h4{
    color:#111827;
    font-weight:600;
}
p,span,label{
    color:#374151;
    font-size:0.95rem;
}
/* -------- SIMPLE BUTTONS -------- */
.stButton>button{
    background:#2563eb;
    color:white;
    border:none;
    border-radius:6px;
    padding:8px 18px;
    font-weight:600;
    font-size:14px;
}
.stButton>button:hover{
    background:#1d4ed8;
}
/* -------- BUBBLE TABS -------- */
.stTabs [data-baseweb="tab-list"]{
    gap:10px;
    padding:6px;
}
.stTabs [data-baseweb="tab"]{
    background:#f3f4f6;
    border-radius:999px;
    padding:8px 18px;
    color:#374151;
    font-weight:600;
    transition:0.2s;
}
/* active tab bubble */
.stTabs [aria-selected="true"]{
    background:#2563eb !important;
    color:white !important;
}
/* hover */
.stTabs [data-baseweb="tab"]:hover{
    background:#e5e7eb;
}
/* -------- INPUTS -------- */
input, textarea{
    border:1px solid #d1d5db !important;
    border-radius:6px !important;
    color:#111827 !important;
}
/* -------- SELECT BOX -------- */
.stSelectbox div[data-baseweb="select"]{
    border:1px solid #d1d5db;
    border-radius:6px;
}
/* -------- DATAFRAME -------- */
.stDataFrame{
    border:1px solid #e5e7eb;
    border-radius:8px;
}
.stDataFrame thead tr th{
    background:#f9fafb;
    color:#111827;
}
</style>
""", unsafe_allow_html=True)

# =============================================================================
# DATA CLASSES
# =============================================================================
class ValidationType(Enum):
    MANDATORY = "mandatory"
    NOT_NULL = "not_null"
    NO_SPECIAL_CHARS = "no_special_chars"
    MAX_LENGTH = "max_length"
    MIN_LENGTH = "min_length"
    ONLY_CHARACTERS = "only_characters"
    ONLY_NUMBERS = "only_numbers"
    EMAIL_FORMAT = "email_format"
    DATE_FORMAT = "date_format"
    PHONE_FORMAT = "phone_format"
    URL_FORMAT = "url_format"
    POSTAL_CODE = "postal_code"
    SSN_FORMAT = "ssn_format"
    CREDIT_CARD = "credit_card"
    IP_ADDRESS = "ip_address"
    CURRENCY_FORMAT = "currency_format"
    PERCENTAGE = "percentage"
    BOOLEAN_FORMAT = "boolean_format"
    NUMERIC_RANGE = "numeric_range"
    UPPERCASE_ONLY = "uppercase_only"
    LOWERCASE_ONLY = "lowercase_only"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    CONTAINS = "contains"
    UNIQUE_VALUE = "unique_value"
    CHECKSUM_VALIDATION = "checksum_validation"
    AGE_VALIDATION = "age_validation"
    REGEX_PATTERN = "regex_pattern"

@dataclass
class ColumnRule:
    """Validation rule configuration for a column"""
    column_name: str
    is_mandatory: bool = False
    not_null: bool = False
    no_special_chars: bool = False
    max_length: Optional[int] = None
    min_length: Optional[int] = None
    only_characters: bool = False
    only_numbers: bool = False
    email_format: bool = False
    date_format: Optional[str] = None
    phone_format: bool = False
    url_format: bool = False
    postal_code: bool = False
    ssn_format: bool = False
    credit_card: bool = False
    ip_address: bool = False
    currency_format: bool = False
    percentage: bool = False
    boolean_format: bool = False
    numeric_range_min: Optional[float] = None
    numeric_range_max: Optional[float] = None
    uppercase_only: bool = False
    lowercase_only: bool = False
    starts_with: Optional[str] = None
    ends_with: Optional[str] = None
    contains: Optional[str] = None
    unique_value: bool = False
    checksum_validation: bool = False
    age_validation_min: Optional[int] = None
    age_validation_max: Optional[int] = None
    regex_pattern: Optional[str] = None
    transform_regex: Optional[str] = None
    default_value: Optional[str] = None
    description: str = ""
    
    def get_active_rules(self) -> List[str]:
        """Get list of active validation rules"""
        rules = []
        if self.is_mandatory:
            rules.append("Mandatory")
        if self.not_null:
            rules.append("Not Null")
        if self.no_special_chars:
            rules.append("No Special Chars")
        if self.max_length:
            rules.append(f"Max Len: {self.max_length}")
        if self.min_length:
            rules.append(f"Min Len: {self.min_length}")
        if self.only_characters:
            rules.append("Chars Only")
        if self.only_numbers:
            rules.append("Numbers Only")
        if self.email_format:
            rules.append("Email")
        if self.date_format:
            rules.append(f"Date: {self.date_format}")
        if self.phone_format:
            rules.append("Phone")
        if self.url_format:
            rules.append("URL")
        if self.postal_code:
            rules.append("Postal Code")
        if self.ssn_format:
            rules.append("SSN")
        if self.credit_card:
            rules.append("Credit Card")
        if self.ip_address:
            rules.append("IP Address")
        if self.currency_format:
            rules.append("Currency")
        if self.percentage:
            rules.append("Percentage")
        if self.boolean_format:
            rules.append("Boolean")
        if self.numeric_range_min is not None or self.numeric_range_max is not None:
            min_val = self.numeric_range_min if self.numeric_range_min is not None else ""
            max_val = self.numeric_range_max if self.numeric_range_max is not None else ""
            rules.append(f"Range: {min_val}-{max_val}")
        if self.uppercase_only:
            rules.append("Uppercase")
        if self.lowercase_only:
            rules.append("Lowercase")
        if self.starts_with:
            rules.append(f"Starts: '{self.starts_with}'")
        if self.ends_with:
            rules.append(f"Ends: '{self.ends_with}'")
        if self.contains:
            rules.append(f"Contains: '{self.contains}'")
        if self.unique_value:
            rules.append("Unique")
        if self.checksum_validation:
            rules.append("Checksum")
        if self.age_validation_min is not None or self.age_validation_max is not None:
            min_age = self.age_validation_min if self.age_validation_min is not None else ""
            max_age = self.age_validation_max if self.age_validation_max is not None else ""
            rules.append(f"Age: {min_age}-{max_age}")
        if self.regex_pattern:
            rules.append("Regex")
        return rules

@dataclass
class ColumnMapping:
    """Mapping between source and target columns"""
    id: str = field(default_factory=lambda: hashlib.md5(str(datetime.now().timestamp()).encode()).hexdigest()[:8])
    source_column: str = ""
    target_column: str = ""
    source_sheet: str = ""
    target_sheet: str = ""
    transform_rules: List[str] = field(default_factory=list)
    validation_errors: List[Dict] = field(default_factory=list)
    is_active: bool = True
    confidence_score: float = 0.0

@dataclass
class FileData:
    """Container for uploaded file data"""
    name: str = ""
    data: Dict[str, pd.DataFrame] = field(default_factory=dict)
    sheets: List[str] = field(default_factory=list)
    columns: Dict[str, List[str]] = field(default_factory=dict)
    selected_sheet: Optional[str] = None
    header_row: int = 0
    raw_data: Optional[bytes] = None

# =============================================================================
# REGEX MANAGER CLASS
# =============================================================================
class RegexManager:
    """Comprehensive regex management and testing interface"""
    
    @staticmethod
    def render_regex_manager(rule, selected_col: str):
        """Render the complete regex management interface"""
        st.markdown("**🔍 Custom Regex Management**")
        
        # Main Regex Testing Interface
        with st.expander("🧪 Custom Regex Testing & Validation", expanded=False):
            st.markdown("""
            <div style="background: linear-gradient(135deg, rgba(59, 130, 246, 0.15) 0%, rgba(16, 185, 129, 0.15) 100%); 
                        padding: 1.5rem; border-radius: 12px; border: 2px solid rgba(59, 130, 246, 0.3); margin-bottom: 1rem;">
                <h4 style="margin: 0 0 0.5rem 0; color: #3b82f6;">🎯 Universal Regex Tester</h4>
                <p style="margin: 0; color: #1f2937; font-size: 0.9rem;">
                    Test and validate your custom regex patterns with real-time feedback.
                    <br><small style="color: #6b7280;">✓ Live pattern testing  ✓ Match highlighting  ✓ Group extraction  ✓ Sample data validation</small>
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            # Regex Mode Selection
            regex_mode = st.radio(
                "Select Regex Mode:",
                ["Validation Pattern", "Extraction/Transform Pattern", "Both (Validate then Extract)"],
                key=f"regex_mode_{selected_col}",
                horizontal=True,
                help="Choose how you want to use regex"
            )
            
            st.markdown("---")
            
            # Validation Pattern Section
            if regex_mode in ["Validation Pattern", "Both (Validate then Extract)"]:
                RegexManager._render_validation_pattern(rule, selected_col)
            
            # Extraction/Transform Pattern Section
            if regex_mode in ["Extraction/Transform Pattern", "Both (Validate then Extract)"]:
                RegexManager._render_extraction_pattern(rule, selected_col)
            
            st.markdown("---")
            
            # Common Patterns Library
            RegexManager._render_pattern_library(rule, selected_col)
            
            st.markdown("---")
            
            # AI-Powered Generator
            RegexManager._render_ai_generator(rule, selected_col)
            
            st.markdown("---")
            
            # Batch Testing
            RegexManager._render_batch_tester(rule, selected_col)
        
        # Final Pattern Display and Editing
        RegexManager._render_final_patterns(rule, selected_col)
        
        return rule
    
    @staticmethod
    def _render_validation_pattern(rule, selected_col: str):
        """Render validation pattern testing interface"""
        st.markdown("### 📋 Validation Pattern")
        st.caption("Pattern to check if the entire value matches the required format")
        
        validation_pattern = st.text_input(
            "Enter validation regex pattern:",
            value=rule.regex_pattern or "",
            placeholder="e.g., ^[A-Z]{2}\\d{6}$ for 2 letters + 6 digits",
            key=f"validation_pattern_{selected_col}",
            help="Pattern must match the complete value"
        )
        
        if validation_pattern:
            # Live testing
            st.markdown("**🧪 Test Validation:**")
            test_validation = st.text_input(
                "Enter test value:",
                placeholder="Enter a value to test against your pattern",
                key=f"test_val_{selected_col}"
            )
            
            if test_validation:
                try:
                    match = re.match(validation_pattern, test_validation)
                    
                    if match:
                        st.success(f"✅ **Valid!** Pattern matches")
                        st.code(f"Matched: '{match.group(0)}'", language="text")
                        
                        if match.groups():
                            st.info(f"📦 **Captured Groups:** {len(match.groups())}")
                            for i, g in enumerate(match.groups(), 1):
                                st.code(f"Group {i}: '{g}'")
                    else:
                        st.error(f"❌ **Invalid!** Value does not match pattern")
                        
                except re.error as e:
                    st.error(f"⚠️ **Invalid Regex Syntax:** {str(e)}")
    
    @staticmethod
    def _render_extraction_pattern(rule, selected_col: str):
        """Render extraction/transform pattern testing interface"""
        st.markdown("### 🔧 Extraction/Transform Pattern")
        st.caption("Extract or transform specific parts from the value")
        
        extraction_pattern = st.text_input(
            "Enter extraction regex pattern:",
            value=rule.transform_regex or "",
            placeholder="e.g., @([a-zA-Z0-9.-]+) to extract email domain",
            key=f"extraction_pattern_{selected_col}",
            help="Pattern to find and extract specific parts"
        )
        
        if extraction_pattern:
            # Extraction method selection
            extract_method = st.radio(
                "Extraction method:",
                ["First Match", "All Matches", "First Group", "All Groups"],
                key=f"extract_method_{selected_col}",
                horizontal=True
            )
            
            # Live testing
            st.markdown("**🧪 Test Extraction:**")
            test_extraction = st.text_input(
                "Enter test value:",
                placeholder="Enter text to extract from",
                key=f"test_ext_{selected_col}"
            )
            
            if test_extraction:
                try:
                    if extract_method == "First Match":
                        match = re.search(extraction_pattern, test_extraction)
                        if match:
                            st.success(f"✅ **Extracted:** `{match.group(0)}`")
                        else:
                            st.warning("❌ No match found")
                    
                    elif extract_method == "All Matches":
                        matches = re.findall(extraction_pattern, test_extraction)
                        if matches:
                            st.success(f"✅ **Found {len(matches)} matches:**")
                            for i, m in enumerate(matches[:20], 1):
                                st.code(f"{i}. {m}")
                        else:
                            st.warning("❌ No matches found")
                    
                    elif extract_method == "First Group":
                        match = re.search(extraction_pattern, test_extraction)
                        if match and match.groups():
                            st.success(f"✅ **Extracted group:** `{match.group(1)}`")
                        else:
                            st.warning("❌ No groups found - use parentheses ()")
                    
                    elif extract_method == "All Groups":
                        match = re.search(extraction_pattern, test_extraction)
                        if match and match.groups():
                            st.success(f"✅ **Extracted {len(match.groups())} groups:**")
                            for i, g in enumerate(match.groups(), 1):
                                st.code(f"Group {i}: {g}")
                        else:
                            st.warning("❌ No groups found")
                
                except re.error as e:
                    st.error(f"⚠️ **Invalid Regex Syntax:** {str(e)}")
    
    @staticmethod
    def _render_pattern_library(rule, selected_col: str):
        """Render common regex patterns library"""
        with st.expander("📚 Common Regex Patterns Library", expanded=False):
            st.markdown("**Quick Insert Common Patterns:**")
            
            common_patterns = {
                # Validation Patterns
                "Email": (r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', "validation"),
                "Phone (US)": (r'^\+?1?\s*\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})$', "validation"),
                "Phone (Indian)": (r'^[6-9]\d{9}$', "validation"),
                "SSN": (r'^\d{3}-\d{2}-\d{4}$', "validation"),
                "Credit Card": (r'^\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}$', "validation"),
                "ZIP Code (US)": (r'^\d{5}(-\d{4})?$', "validation"),
                "IP Address": (r'^(\d{1,3}\.){3}\d{1,3}$', "validation"),
                "URL": (r'^(https?://)?(www\.)?([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}(/.*)?$', "validation"),
                "Date (YYYY-MM-DD)": (r'^\d{4}-\d{2}-\d{2}$', "validation"),
                "Username": (r'^[a-zA-Z0-9_]{3,16}$', "validation"),
                "Only Letters": (r'^[a-zA-Z]+$', "validation"),
                "Only Numbers": (r'^\d+$', "validation"),
                
                # Extraction Patterns
                "Extract Domain": (r'@([a-zA-Z0-9.-]+)', "extraction"),
                "Extract Numbers": (r'\d+', "extraction"),
                "Extract Words": (r'\b[a-zA-Z]+\b', "extraction"),
                "Extract Hashtags": (r'#\w+', "extraction"),
            }
            
            # Group by type
            validation_patterns = {k: v[0] for k, v in common_patterns.items() if v[1] == "validation"}
            extraction_patterns = {k: v[0] for k, v in common_patterns.items() if v[1] == "extraction"}
            
            tab1, tab2 = st.tabs(["📋 Validation", "🔧 Extraction"])
            
            with tab1:
                cols = st.columns(2)
                for i, (name, pattern) in enumerate(validation_patterns.items()):
                    with cols[i % 2]:
                        if st.button(f"📌 {name}", key=f"preset_val_{name}_{selected_col}", use_container_width=True):
                            rule.regex_pattern = pattern
                            st.success(f"✅ Applied: {name}")
                            st.rerun()
            
            with tab2:
                cols = st.columns(2)
                for i, (name, pattern) in enumerate(extraction_patterns.items()):
                    with cols[i % 2]:
                        if st.button(f"🔧 {name}", key=f"preset_ext_{name}_{selected_col}", use_container_width=True):
                            rule.transform_regex = pattern
                            st.success(f"✅ Applied: {name}")
                            st.rerun()
    
    @staticmethod
    def _render_ai_generator(rule, selected_col: str):
        """Render AI-powered regex generator"""
        with st.expander("🤖 AI Regex Generator (Azure OpenAI)", expanded=False):
            st.markdown("""
            <div style="background: rgba(139, 92, 246, 0.15); padding: 1rem; border-radius: 8px;">
                <p style="margin: 0; font-size: 0.9rem;">
                    <strong>✨ Describe what you need and AI will generate the regex pattern.</strong>
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            user_prompt = st.text_area(
                "Describe your regex requirement:",
                placeholder="e.g., Validate Indian mobile numbers starting with 6-9 with 10 digits",
                key=f"ai_prompt_{selected_col}",
                height=100
            )
            
            ai_mode = st.radio(
                "Pattern type:",
                ["Validation", "Extraction/Transform"],
                key=f"ai_mode_{selected_col}",
                horizontal=True
            )
            
            if st.button("🎯 Generate Pattern", key=f"ai_gen_{selected_col}", type="primary"):
                if user_prompt.strip():
                    try:
                        from openai import AzureOpenAI
                        
                        if not hasattr(st.secrets, 'endpoint'):
                            st.error("❌ Azure OpenAI not configured")
                            st.info("Add credentials to .streamlit/secrets.toml")
                        else:
                            with st.spinner("🤖 Generating pattern..."):
                                client = AzureOpenAI(
                                    azure_endpoint=st.secrets.endpoint,
                                    api_key=st.secrets.api_key,
                                    api_version=st.secrets.api_version
                                )
                                
                                response = client.chat.completions.create(
                                    model=st.secrets.deployment_name,
                                    messages=[
                                        {"role": "system", "content": f"Generate a {ai_mode.lower()} regex pattern. Return ONLY the pattern."},
                                        {"role": "user", "content": user_prompt}
                                    ],
                                    max_tokens=500,
                                    temperature=0.1
                                )
                                
                                generated = response.choices[0].message.content.strip()
                                generated = generated.strip('`').strip()
                                
                                st.success("✅ Pattern generated!")
                                st.code(generated, language="regex")
                                
                                col1, col2 = st.columns(2)
                                if ai_mode == "Validation":
                                    with col1:
                                        if st.button("✅ Use Pattern", key=f"use_{selected_col}"):
                                            rule.regex_pattern = generated
                                            st.rerun()
                                else:
                                    with col2:
                                        if st.button("✅ Use Pattern", key=f"use_{selected_col}"):
                                            rule.transform_regex = generated
                                            st.rerun()
                    
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
    
    @staticmethod
    def _render_batch_tester(rule, selected_col: str):
        """Render batch testing interface"""
        with st.expander("🔬 Batch Testing", expanded=False):
            st.markdown("**Test pattern against multiple values:**")
            
            sample_data = st.text_area(
                "Sample values (one per line):",
                placeholder="test@example.com\ninvalid-email\nuser@domain.co.uk",
                key=f"sample_data_{selected_col}",
                height=150
            )
            
            test_pattern = st.text_input(
                "Pattern to test:",
                value=rule.regex_pattern or rule.transform_regex or "",
                key=f"batch_pattern_{selected_col}"
            )
            
            if st.button("🧪 Run Test", key=f"batch_test_{selected_col}"):
                if sample_data and test_pattern:
                    lines = [l.strip() for l in sample_data.split('\n') if l.strip()]
                    results = []
                    
                    for line in lines:
                        try:
                            match = re.match(test_pattern, line)
                            results.append({
                                "Value": line,
                                "Status": "✅ Valid" if match else "❌ Invalid",
                                "Result": match.group(0) if match else "—"
                            })
                        except:
                            results.append({
                                "Value": line,
                                "Status": "⚠️ Error",
                                "Result": "—"
                            })
                    
                    df_results = pd.DataFrame(results)
                    st.dataframe(df_results, use_container_width=True, hide_index=True)
                    
                    valid = sum(1 for r in results if "✅" in r["Status"])
                    st.metric("Pass Rate", f"{valid}/{len(results)} ({valid/len(results)*100:.1f}%)")
    
    @staticmethod
    def _render_final_patterns(rule, selected_col: str):
        """Render final pattern editing"""
        st.markdown("**📝 Active Patterns:**")
        
        col1, col2 = st.columns(2)
        
        with col1:
            current_validation = st.text_input(
                "✅ Validation Pattern:",
                value=rule.regex_pattern or "",
                key=f"final_validation_{selected_col}",
                placeholder="^pattern$"
            )
            rule.regex_pattern = current_validation if current_validation else None
        
        with col2:
            current_extraction = st.text_input(
                "🔧 Extraction Pattern:",
                value=rule.transform_regex or "",
                key=f"final_extraction_{selected_col}",
                placeholder="(group)"
            )
            rule.transform_regex = current_extraction if current_extraction else None

# =============================================================================
# SESSION STATE MANAGEMENT
# =============================================================================
def init_session_state():
    """Initialize session state with all required keys"""
    defaults = {
        'active_tab': 0,
        'completed_steps': set(),
        'template_file': FileData(),
        'source_file': FileData(),
        'column_rules': {},
        'mappings': [],
        'validation_results': {},
        'transformed_data': None,
        'processing_log': [],
        'show_mapping_panel': False,
        'auto_map_triggered': False,
        'selected_mapping_id': None,
        'session_id': hashlib.md5(str(datetime.now()).encode()).hexdigest()[:8]
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def save_session_state():
    """Export session state to JSON"""
    state_dict = {
        'column_rules': {k: asdict(v) for k, v in st.session_state.column_rules.items()},
        'mappings': [asdict(m) for m in st.session_state.mappings],
        'session_id': st.session_state.session_id
    }
    return json.dumps(state_dict, indent=2, default=str)

# =============================================================================
# FILE HANDLING
# =============================================================================
def detect_file_type(file_name: str) -> str:
    """Detect file type from extension"""
    if file_name.lower().endswith('.csv'):
        return 'csv'
    elif file_name.lower().endswith(('.xlsx', '.xls', '.xlsm')):
        return 'excel'
    return 'unknown'

def clean_column_names(columns, header_row=None):
    """Clean column names"""
    cleaned = []
    for i, col in enumerate(columns):
        col_str = str(col).strip()
        is_empty = (
            col_str.lower() in ['nan', 'none', ''] or 
            pd.isna(col) or
            col_str.startswith('Unnamed:')
        )
        if is_empty:
            cleaned.append(f"Column_{i+1}")
        else:
            cleaned.append(col_str)
    return cleaned

def read_uploaded_file(uploaded_file, header_row: int = 0, selected_sheet: str = None):
    """Read uploaded file"""
    if uploaded_file is None:
        return {}, [], {}
    
    try:
        if hasattr(uploaded_file, 'name'):
            file_type = detect_file_type(uploaded_file.name)
            file_bytes = uploaded_file.getvalue() if hasattr(uploaded_file, 'getvalue') else uploaded_file.read()
        else:
            file_bytes = uploaded_file.getvalue() if hasattr(uploaded_file, 'getvalue') else uploaded_file.read()
            file_type = 'excel'
        
        data = {}
        
        if file_type == 'csv':
            df = pd.read_csv(io.BytesIO(file_bytes), header=header_row)
            df.columns = clean_column_names(df.columns, header_row)
            df = df.dropna(how='all')
            data['Sheet1'] = df
            sheets = ['Sheet1']
        else:
            excel_file = pd.ExcelFile(io.BytesIO(file_bytes))
            sheets_to_process = [selected_sheet] if selected_sheet else excel_file.sheet_names
            
            for sheet in sheets_to_process:
                df = pd.read_excel(io.BytesIO(file_bytes), sheet_name=sheet, header=header_row)
                df.columns = clean_column_names(df.columns, header_row)
                df = df.dropna(how='all')
                data[sheet] = df
            
            sheets = list(data.keys())
        
        columns = {sheet: list(df.columns) for sheet, df in data.items()}
        return data, sheets, columns
        
    except Exception as e:
        st.error(f"Error reading file: {str(e)}")
        return {}, [], {}

def auto_detect_header(df: pd.DataFrame, max_rows: int = 10) -> int:
    """Auto-detect header row"""
    if len(df) == 0:
        return 0
    
    best_row = 0
    best_score = 0
    
    for i in range(min(max_rows, len(df))):
        row = df.iloc[i]
        if row.isna().all():
            continue
        
        string_count = sum(1 for x in row if isinstance(x, str))
        score = string_count / len(row) if len(row) > 0 else 0
        
        if score > best_score:
            best_score = score
            best_row = i
    
    return best_row

def _refresh_template_data():
    """Refresh template data"""
    if st.session_state.template_file.raw_data:
        file_obj = io.BytesIO(st.session_state.template_file.raw_data)
        data, sheets, columns = read_uploaded_file(
            file_obj,
            st.session_state.template_file.header_row,
            st.session_state.template_file.selected_sheet
        )
        st.session_state.template_file.data = data
        st.session_state.template_file.sheets = sheets
        st.session_state.template_file.columns = columns

def _refresh_source_data():
    """Refresh source data"""
    if st.session_state.source_file.raw_data:
        file_obj = io.BytesIO(st.session_state.source_file.raw_data)
        data, sheets, columns = read_uploaded_file(
            file_obj,
            st.session_state.source_file.header_row,
            st.session_state.source_file.selected_sheet
        )
        st.session_state.source_file.data = data
        st.session_state.source_file.sheets = sheets
        st.session_state.source_file.columns = columns

# =============================================================================
# VALIDATION ENGINE
# =============================================================================
class ValidationEngine:
    """Enterprise-grade validation engine"""
    
    @staticmethod
    def validate_value(value: Any, rule: ColumnRule) -> Tuple[bool, List[str], Any]:
        """Validate and transform a single value"""
        errors = []
        is_empty = pd.isna(value) or str(value).strip() == ''
        
        if is_empty:
            if rule.not_null:
                errors.append("Value cannot be null/empty")
            if rule.is_mandatory:
                errors.append("Mandatory field is empty")
            if rule.default_value:
                value = rule.default_value
            return len(errors) == 0, errors, value
        
        str_value = str(value).strip()
        transformed_value = str_value
        
        if rule.max_length and len(str_value) > rule.max_length:
            errors.append(f"Length exceeds maximum {rule.max_length}")
            transformed_value = str_value[:rule.max_length]
        
        if rule.min_length and len(str_value) < rule.min_length:
            errors.append(f"Length below minimum {rule.min_length}")
        
        if rule.only_characters and any(char.isdigit() for char in str_value):
            errors.append("Contains numeric characters")
        
        if rule.only_numbers:
            try:
                float(str_value.replace(',', ''))
            except:
                errors.append("Not a valid number")
        
        if rule.no_special_chars:
            if re.findall(r'[^\w\s\-]', str_value):
                errors.append("Contains special characters")
        
        if rule.email_format:
            if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', str_value):
                errors.append("Invalid email format")
        
        if rule.regex_pattern:
            try:
                if not re.match(rule.regex_pattern, str_value):
                    errors.append("Does not match required pattern")
            except:
                pass
        
        return len(errors) == 0, errors, transformed_value

# =============================================================================
# MAPPING ENGINE
# =============================================================================
class MappingEngine:
    """AI-powered column mapping engine"""
    
    @staticmethod
    def calculate_similarity(source: str, target: str) -> float:
        """Calculate similarity score"""
        source_clean = source.lower().replace('_', ' ').strip()
        target_clean = target.lower().replace('_', ' ').strip()
        
        if source_clean == target_clean:
            return 100.0
        if source_clean in target_clean or target_clean in source_clean:
            return 90.0
        
        source_words = set(source_clean.split())
        target_words = set(target_clean.split())
        
        if source_words and target_words:
            intersection = source_words.intersection(target_words)
            union = source_words.union(target_words)
            return (len(intersection) / len(union) * 100) if union else 0
        
        return 0.0
    
    @staticmethod
    def auto_map_columns(source_cols: List[str], target_cols: List[str], threshold: float = 60.0):
        """Generate automatic mappings"""
        mappings = []
        used_targets = set()
        
        for source in source_cols:
            best_match = None
            best_score = 0
            
            for target in target_cols:
                if target in used_targets:
                    continue
                score = MappingEngine.calculate_similarity(source, target)
                if score > best_score and score >= threshold:
                    best_score = score
                    best_match = target
            
            if best_match:
                mapping = ColumnMapping(
                    source_column=source,
                    target_column=best_match,
                    confidence_score=best_score / 100
                )
                mappings.append(mapping)
                used_targets.add(best_match)
        
        return mappings

# =============================================================================
# UI COMPONENTS
# =============================================================================
def render_progress_steps():
    """Render progress steps"""
    steps = [
        ("1", "Upload Template"),
        ("2", "Upload Source"),
        ("3", "Configure Rules"),
        ("4", "Map Columns"),
        ("5", "Validate & Export")
    ]
    
    current_step = st.session_state.active_tab
    cols = st.columns(len(steps))
    
    for i, (num, label) in enumerate(steps):
        with cols[i]:
            if i < current_step:
                st.markdown(f"""
                <div style="text-align: center;">
                    <div style="width: 48px; height: 48px; border-radius: 50%; background: #10b981; 
                                color: white; display: flex; align-items: center; justify-content: center; margin: 0 auto;">
                        ✓
                    </div>
                    <div style="font-size: 0.85rem; color: #10b981; margin-top: 0.5rem;">{label}</div>
                </div>
                """, unsafe_allow_html=True)
            elif i == current_step:
                st.markdown(f"""
                <div style="text-align: center;">
                    <div style="width: 48px; height: 48px; border-radius: 50%; background: #3b82f6; 
                                color: white; display: flex; align-items: center; justify-content: center; margin: 0 auto;">
                        {num}
                    </div>
                    <div style="font-size: 0.85rem; color: #3b82f6; margin-top: 0.5rem;">{label}</div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div style="text-align: center;">
                    <div style="width: 48px; height: 48px; border-radius: 50%; background: #e5e7eb; 
                                color: #6b7280; display: flex; align-items: center; justify-content: center; margin: 0 auto;">
                        {num}
                    </div>
                    <div style="font-size: 0.85rem; color: #6b7280; margin-top: 0.5rem;">{label}</div>
                </div>
                """, unsafe_allow_html=True)
    
    st.markdown("<hr style='margin: 2rem 0;'>", unsafe_allow_html=True)

def render_sidebar():
    """Render sidebar"""
    with st.sidebar:
        st.markdown("## 🎛️ Control Panel")
        
        with st.expander("💾 Session Management", expanded=True):
            if st.button("💾 Save Session", use_container_width=True):
                state_json = save_session_state()
                st.download_button(
                    "Download JSON",
                    state_json,
                    file_name=f"session_{st.session_state.session_id}.json",
                    mime="application/json"
                )
        
        st.markdown("---")
        st.markdown("### 📊 Quick Stats")
        
        col1, col2 = st.columns(2)
        col1.metric("Template", len(st.session_state.template_file.sheets))
        col2.metric("Source", len(st.session_state.source_file.sheets))
        st.metric("Mappings", len(st.session_state.mappings))
        st.metric("Rules", len(st.session_state.column_rules))
        
        st.markdown("---")
        if st.button("🔄 Reset", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            init_session_state()
            st.rerun()

# =============================================================================
# TAB RENDERERS
# =============================================================================
def render_template_tab():
    """Render template upload tab"""
    st.markdown("### 📤 Step 1: Upload Template File")
    
    uploaded = st.file_uploader(
        "Upload Template",
        type=['csv', 'xlsx', 'xls'],
        key='template_upload'
    )
    
    if uploaded:
        file_bytes = uploaded.getvalue()
        
        if st.session_state.template_file.name != uploaded.name:
            st.session_state.template_file = FileData(
                name=uploaded.name,
                raw_data=file_bytes
            )
            _refresh_template_data()
        
        if st.session_state.template_file.sheets:
            selected_sheet = st.selectbox(
                "Select Sheet",
                st.session_state.template_file.sheets,
                key='template_sheet'
            )
            st.session_state.template_file.selected_sheet = selected_sheet
            
            if st.button("✅ Confirm Template", type="primary"):
                _refresh_template_data()
                st.success("✅ Template configured!")
                
                # Initialize rules
                if selected_sheet in st.session_state.template_file.data:
                    for col in st.session_state.template_file.data[selected_sheet].columns:
                        if col not in st.session_state.column_rules:
                            st.session_state.column_rules[col] = ColumnRule(column_name=col)
                
                if st.button("➡️ Next: Upload Source"):
                    st.session_state.active_tab = 1
                    st.rerun()

def render_source_tab():
    """Render source upload tab"""
    st.markdown("### 📤 Step 2: Upload Source File")
    
    uploaded = st.file_uploader(
        "Upload Source",
        type=['csv', 'xlsx', 'xls'],
        key='source_upload'
    )
    
    if uploaded:
        file_bytes = uploaded.getvalue()
        
        if st.session_state.source_file.name != uploaded.name:
            st.session_state.source_file = FileData(
                name=uploaded.name,
                raw_data=file_bytes
            )
        
        if st.button("✅ Load Source", type="primary"):
            _refresh_source_data()
            st.success("✅ Source loaded!")
            
            if st.button("➡️ Next: Configure Rules"):
                st.session_state.active_tab = 2
                st.rerun()

def render_rules_tab():
    """Render validation rules tab"""
    st.markdown("### ⚙️ Step 3: Configure Validation Rules")
    
    if not st.session_state.template_file.selected_sheet:
        st.warning("⚠️ Please upload template first")
        return
    
    template_cols = st.session_state.template_file.columns.get(
        st.session_state.template_file.selected_sheet, []
    )
    
    selected_col = st.selectbox(
        "Select Column",
        template_cols,
        key='rule_column'
    )
    
    if selected_col:
        rule = st.session_state.column_rules.get(
            selected_col,
            ColumnRule(column_name=selected_col)
        )
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("**Basic Validation**")
            rule.is_mandatory = st.toggle("Mandatory", value=rule.is_mandatory, key=f"m_{selected_col}")
            rule.not_null = st.toggle("Not Null", value=rule.not_null, key=f"n_{selected_col}")
            rule.only_numbers = st.toggle("Numbers Only", value=rule.only_numbers, key=f"num_{selected_col}")
            rule.email_format = st.toggle("Email", value=rule.email_format, key=f"em_{selected_col}")
        
        with col2:
            st.markdown("**Length & Range**")
            rule.max_length = st.number_input("Max Length", value=rule.max_length or 0, key=f"max_{selected_col}")
            if rule.max_length == 0:
                rule.max_length = None
        
        with col3:
            st.markdown("**Transform**")
            rule.uppercase_only = st.toggle("Uppercase", value=rule.uppercase_only, key=f"up_{selected_col}")
            rule.lowercase_only = st.toggle("Lowercase", value=rule.lowercase_only, key=f"low_{selected_col}")
        
        # Enhanced Regex Manager Integration
        rule = RegexManager.render_regex_manager(rule, selected_col)
        
        st.session_state.column_rules[selected_col] = rule
        
        if st.button("➡️ Next: Map Columns", type="primary"):
            st.session_state.active_tab = 3
            st.rerun()

def render_mapping_tab():
    """Render mapping tab"""
    st.markdown("### 🔗 Step 4: Column Mapping")
    
    template_cols = st.session_state.template_file.columns.get(
        st.session_state.template_file.selected_sheet, []
    )
    source_cols = st.session_state.source_file.columns.get(
        st.session_state.source_file.selected_sheet, []
    )
    
    if not template_cols or not source_cols:
        st.error("⚠️ Please upload both files")
        return
    
    if st.button("🤖 Auto-Map", use_container_width=True):
        mappings = MappingEngine.auto_map_columns(source_cols, template_cols)
        st.session_state.mappings = mappings
        st.success(f"✅ Mapped {len(mappings)} columns")
        st.rerun()
    
    st.markdown("---")
    
    for target in template_cols:
        col1, col2 = st.columns([2, 2])
        
        with col1:
            current = next((m.source_column for m in st.session_state.mappings if m.target_column == target), "")
            selected = st.selectbox(
                f"Source → {target}",
                [""] + source_cols,
                index=source_cols.index(current) + 1 if current in source_cols else 0,
                key=f"map_{target}"
            )
            
            if selected:
                # Remove old mapping
                st.session_state.mappings = [m for m in st.session_state.mappings if m.target_column != target]
                # Add new
                st.session_state.mappings.append(ColumnMapping(
                    source_column=selected,
                    target_column=target
                ))
    
    if st.button("➡️ Next: Validate", type="primary"):
        st.session_state.active_tab = 4
        st.rerun()

def render_validation_tab():
    """Render validation and export tab"""
    st.markdown("### ✅ Step 5: Validate & Export")
    
    if st.button("🚀 Execute Validation", type="primary"):
        with st.spinner("Processing..."):
            execute_validation_pipeline()
    
    if st.session_state.validation_results:
        results = st.session_state.validation_results
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Rows", results.get('total_rows', 0))
        col2.metric("Valid", results.get('valid_rows', 0))
        col3.metric("Errors", results.get('error_rows', 0))
        
        if st.session_state.transformed_data is not None:
            st.dataframe(st.session_state.transformed_data.head(100))
            
            csv = st.session_state.transformed_data.to_csv(index=False)
            st.download_button(
                "📥 Download CSV",
                csv,
                file_name="mapped_data.csv",
                mime="text/csv"
            )

def execute_validation_pipeline():
    """Execute validation pipeline"""
    try:
        source_df = st.session_state.source_file.data.get(
            st.session_state.source_file.selected_sheet,
            pd.DataFrame()
        )
        
        template_cols = st.session_state.template_file.columns.get(
            st.session_state.template_file.selected_sheet, []
        )
        
        transformed_data = pd.DataFrame(columns=template_cols)
        errors = []
        valid_rows = 0
        error_rows = 0
        
        for idx, row in source_df.iterrows():
            new_row = {}
            row_has_error = False
            
            for mapping in st.session_state.mappings:
                source_val = row.get(mapping.source_column)
                rule = st.session_state.column_rules.get(
                    mapping.target_column,
                    ColumnRule(column_name=mapping.target_column)
                )
                
                is_valid, val_errors, transformed = ValidationEngine.validate_value(source_val, rule)
                
                if not is_valid:
                    row_has_error = True
                    for err in val_errors:
                        errors.append({
                            'row': idx + 1,
                            'column': mapping.target_column,
                            'error': err
                        })
                
                new_row[mapping.target_column] = transformed
            
            transformed_data = pd.concat([transformed_data, pd.DataFrame([new_row])], ignore_index=True)
            
            if row_has_error:
                error_rows += 1
            else:
                valid_rows += 1
        
        st.session_state.transformed_data = transformed_data
        st.session_state.validation_results = {
            'total_rows': len(source_df),
            'valid_rows': valid_rows,
            'error_rows': error_rows,
            'errors': errors[:100]
        }
        
        st.success("✅ Validation complete!")
        
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")

# =============================================================================
# MAIN APPLICATION
# =============================================================================
def main():
    """Main application"""
    init_session_state()
    
    st.title("🎯 Mapper Enterprise | Data Migration Platform")
    
    render_sidebar()
    render_progress_steps()
    
    tabs = st.tabs([
        "📤 Template",
        "📤 Source",
        "⚙️ Rules",
        "🔗 Mapping",
        "✅ Validate"
    ])
    
    with tabs[0]:
        render_template_tab()
    
    with tabs[1]:
        render_source_tab()
    
    with tabs[2]:
        render_rules_tab()
    
    with tabs[3]:
        render_mapping_tab()
    
    with tabs[4]:
        render_validation_tab()

if __name__ == "__main__":
    main()