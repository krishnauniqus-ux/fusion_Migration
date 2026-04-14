"""
Data models and classes
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
import pandas as pd
import hashlib
from datetime import datetime

class ValidationType(Enum):
    """Validation types enumeration"""
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
    FIX_ACCENTED_CHARS = "fix_accented_chars"

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
    title_case: bool = False
    sentence_case: bool = False
    camel_case: bool = False
    lower_camel_case: bool = False
    snake_case: bool = False
    title_case_strict: bool = False
    fix_accented_chars: bool = False
    starts_with: Optional[str] = None
    ends_with: Optional[str] = None
    contains: Optional[str] = None
    unique_value: bool = False
    check_duplicates: bool = False
    similar_match: bool = False
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
        if self.title_case:
            rules.append("Title Case")
        if self.sentence_case:
            rules.append("Sentence Case")
        if self.camel_case:
            rules.append("CamelCase")
        if self.lower_camel_case:
            rules.append("lowerCamelCase")
        if self.snake_case:
            rules.append("snake_case")
        if self.title_case_strict:
            rules.append("Title Case (Strict)")
        if self.fix_accented_chars:
            rules.append("Fix Accented Chars")
        if self.starts_with:
            rules.append(f"Starts: '{self.starts_with}'")
        if self.ends_with:
            rules.append(f"Ends: '{self.ends_with}'")
        if self.contains:
            rules.append(f"Contains: '{self.contains}'")
        if self.unique_value:
            rules.append("Unique")
        if self.check_duplicates:
            rules.append("Check Duplicates")
        if self.similar_match:
            rules.append("Similar Match (>=85%)")
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
    all_sheets: List[str] = field(default_factory=list)
