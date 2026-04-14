"""
Validation Engine.

Two categories of rules:
  TRANSFORM rules  – applied to the output AND generate validation errors.
                     These are: case rules, no_special_chars.
  VALIDATE rules   – generate validation errors only; never touch the output.
                     All other rules (max_length, mandatory, phone, etc.).

Guarantees:
  - Every input row produces exactly one output value (no data loss).
  - All validation errors are reported without any limit.
"""
import re
import pandas as pd
from typing import Tuple, List, Any
from core.models import ColumnRule
from unidecode import unidecode
from features.validation.phone_validator import validate_uae_india_phone
from features.regex.engine import RegexEngine

_NULL_STRINGS = frozenset({
    'NULL', 'NONE', 'NAN', 'N/A', 'NA', '#N/A', '<NA>', '-', '--'
})


class ValidationEngine:
    """Enterprise-grade validation engine."""

    @staticmethod
    def validate_value(value: Any, rule: ColumnRule) -> Tuple[bool, List[str], Any]:
        """Validate a single value against all configured rules.

        Behaviour:
        - ``original`` is always used for validation / error messages so that
          the user sees what was wrong with the *source* data.
        - ``output`` starts as a copy of ``original`` and is mutated **only**
          by *transform* rules (case conversions, special-char stripping).
          Everything else leaves ``output`` unchanged.

        Returns:
            (is_valid, error_messages, output_value)
        """
        errors: List[str] = []

        # --- Null / empty check (scalar-safe for pd.NA, np.nan, None) ---
        try:
            is_empty = bool(pd.isna(value))
        except (TypeError, ValueError):
            is_empty = value is None

        if not is_empty:
            str_upper = str(value).strip().upper()
            is_empty = (
                str(value).strip() == ''
                or str_upper in _NULL_STRINGS
            )

        if is_empty:
            if rule.is_mandatory:
                errors.append("Mandatory field is empty")
            if rule.not_null:
                errors.append("Contains Null Values")
            output = rule.default_value if rule.default_value else value
            return len(errors) == 0, errors, output

        original = str(value).strip()
        # `output` accumulates only transform-rule mutations
        output = original

        # --- Not Null Check (non-empty null-like strings) ---
        if rule.not_null:
            if original.upper() in _NULL_STRINGS:
                errors.append("Contains Null Values")

        # =================================================================
        # TRANSFORM RULES — applied to `output` AND generate errors
        #
        # Order matters:
        #   1. fix_accented_chars  — convert Unicode → ASCII FIRST
        #   2. no_special_chars    — strip remaining non-alphanumeric
        #   3. case transformations
        # This ensures accented chars become ASCII letters (É→E) before
        # the special-char filter runs, so they are kept instead of
        # being deleted.
        # =================================================================

        # --- Fix Accented Characters (transform + validate) ---
        if rule.fix_accented_chars:
            has_non_ascii = any(ord(c) > 127 for c in original)
            if has_non_ascii:
                ascii_version = unidecode(original)
                errors.append(
                    f"Contains accented/non-ASCII characters "
                    f"(e.g. '{original}' → '{ascii_version}')"
                )
            output = unidecode(output)

        # --- No Special Characters (transform + validate) ---
        if rule.no_special_chars:
            found = re.findall(r'[^a-zA-Z0-9\s&]', original)
            if found:
                errors.append(f"Contains special characters: {set(found)}")
            output = re.sub(r'[^a-zA-Z0-9\s&]', '', output)

        # --- Case transformations (transform + validate) ---
        if rule.uppercase_only:
            if original != original.upper():
                errors.append("Must be uppercase only")
            output = output.upper()

        if rule.lowercase_only:
            if original != original.lower():
                errors.append("Must be lowercase only")
            output = output.lower()

        if rule.title_case:
            expected = ValidationEngine._apply_title_case(original)
            if original != expected:
                errors.append("Does not match title case format")
            output = ValidationEngine._apply_title_case(output)

        if rule.sentence_case:
            expected = ValidationEngine._apply_sentence_case(original)
            if original != expected:
                errors.append("Does not match sentence case format")
            output = ValidationEngine._apply_sentence_case(output)

        if rule.camel_case:
            expected = ValidationEngine._apply_camel_case(original)
            if original != expected:
                errors.append("Does not match CamelCase format")
            output = ValidationEngine._apply_camel_case(output)

        if rule.lower_camel_case:
            expected = ValidationEngine._apply_lower_camel_case(original)
            if original != expected:
                errors.append("Does not match lowerCamelCase format")
            output = ValidationEngine._apply_lower_camel_case(output)

        if rule.snake_case:
            expected = ValidationEngine._apply_snake_case(original)
            if original != expected:
                errors.append("Does not match snake_case format")
            output = ValidationEngine._apply_snake_case(output)

        if rule.title_case_strict:
            expected = ValidationEngine._apply_title_case_strict(original)
            if original != expected:
                errors.append("Does not match strict title case format")
            output = ValidationEngine._apply_title_case_strict(output)

        # =================================================================
        # VALIDATE-ONLY RULES — never touch `output`
        # =================================================================

        # --- Only Characters ---
        if rule.only_characters:
            if any(c.isdigit() for c in original):
                errors.append("Contains numeric characters")

        # --- Only Numbers ---
        if rule.only_numbers:
            cleaned_num = original.replace(',', '').replace(' ', '')
            try:
                float(cleaned_num)
            except ValueError:
                errors.append("Not a valid numeric value")

        # --- Email Format ---
        if rule.email_format:
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, original):
                errors.append("Invalid email format")

        # --- Phone Format ---
        if rule.phone_format:
            _, phone_errors = validate_uae_india_phone(original)
            errors.extend(phone_errors)

        # --- Date Format ---
        if rule.date_format:
            try:
                parsed_date = pd.to_datetime(original, errors='coerce')
                if pd.isna(parsed_date):
                    for fmt in ['%Y-%m-%d', '%Y/%m/%d', '%d-%m-%Y', '%d/%m/%Y',
                                '%m/%d/%Y', '%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S',
                                '%Y-%m-%dT%H:%M:%SZ', '%d-%b-%Y', '%Y%m%d',
                                '%d %b %Y', '%d %B %Y']:
                        try:
                            parsed_date = pd.to_datetime(original, format=fmt)
                            break
                        except Exception:
                            continue
                if pd.isna(parsed_date):
                    errors.append("Invalid date format (expected parseable date)")
            except Exception as e:
                errors.append(f"Date parsing error: {str(e)}")

        # --- URL Format ---
        if rule.url_format:
            url_pattern = r'^(https?://)?(www\.)?([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}(/.*)?$'
            if not re.match(url_pattern, original):
                errors.append("Invalid URL format")

        # --- Postal Code ---
        if rule.postal_code:
            if not re.match(r'^\d{5}(-\d{4})?$', original):
                errors.append("Invalid postal code format (expected: 12345 or 12345-6789)")

        # --- SSN Format ---
        if rule.ssn_format:
            if not re.match(r'^\d{3}-\d{2}-\d{4}$', original):
                errors.append("Invalid SSN format (expected: 123-45-6789)")

        # --- Credit Card ---
        if rule.credit_card:
            clean_card = re.sub(r'[-\s]', '', original)
            if not clean_card.isdigit():
                errors.append("Credit card must contain only numbers")
            elif not (13 <= len(clean_card) <= 19):
                errors.append("Credit card number length invalid")
            else:
                def luhn_checksum(card_num: int) -> int:
                    def digits_of(n: int) -> List[int]:
                        return [int(d) for d in str(n)]
                    digits = digits_of(card_num)
                    odd_digits = digits[-1::-2]
                    even_digits = digits[-2::-2]
                    total = sum(odd_digits)
                    for d in even_digits:
                        total += sum(digits_of(d * 2))
                    return total % 10
                if luhn_checksum(int(clean_card)) != 0:
                    errors.append("Invalid credit card number")

        # --- IP Address ---
        if rule.ip_address:
            if not re.match(r'^(\d{1,3}\.){3}\d{1,3}$', original):
                errors.append("Invalid IP address format")
            else:
                for octet in original.split('.'):
                    if not octet.isdigit() or not (0 <= int(octet) <= 255):
                        errors.append("Invalid IP address range")
                        break

        # --- Currency Format ---
        if rule.currency_format:
            if not re.match(r'^\$?\d{1,3}(,\d{3})*(\.\d{2})?$', original):
                errors.append("Invalid currency format (expected: $1,234.56 or 1234.56)")

        # --- Percentage ---
        if rule.percentage:
            if not re.match(r'^\d+(\.\d+)?%?$', original):
                errors.append("Invalid percentage format (expected: 25 or 25.5 or 25%)")

        # --- Boolean Format ---
        if rule.boolean_format:
            if original.lower() not in ['true', 'false', 'yes', 'no', '1', '0', 'y', 'n', 't', 'f']:
                errors.append("Invalid boolean value (expected: true/false, yes/no, 1/0, y/n, t/f)")

        # --- Numeric Range ---
        if rule.numeric_range_min is not None or rule.numeric_range_max is not None:
            try:
                num_value = float(original)
                if rule.numeric_range_min is not None and num_value < rule.numeric_range_min:
                    errors.append(f"Value {num_value} below minimum {rule.numeric_range_min}")
                if rule.numeric_range_max is not None and num_value > rule.numeric_range_max:
                    errors.append(f"Value {num_value} above maximum {rule.numeric_range_max}")
            except ValueError:
                errors.append("Value must be numeric for range validation")

        # --- Max / Min Length (validate only – no truncation) ---
        if rule.max_length and len(original) > rule.max_length:
            errors.append(f"Length {len(original)} exceeds maximum {rule.max_length}")

        if rule.min_length and len(original) < rule.min_length:
            errors.append(f"Length {len(original)} below minimum {rule.min_length}")

        # --- Regex Pattern (validate only – no transformation) ---
        if rule.regex_pattern:
            try:
                engine = RegexEngine(rule.regex_pattern)
                result = engine.process(original)
                op = result.get("operation")

                if op == "validate":
                    if not result.get("matched", False):
                        errors.append(f"Does not match required pattern: {rule.regex_pattern}")
                elif op in ("extract", "search"):
                    if not result.get("result"):
                        errors.append(f"Pattern not found in value: {rule.regex_pattern}")
                elif op == "transform":
                    cleaned = result.get("result", "")
                    if cleaned != result.get("original", original):
                        errors.append(
                            f"Contains characters not allowed by pattern: {rule.regex_pattern}"
                        )
                elif op == "split":
                    parts_count = result.get("parts_count", 1)
                    if parts_count > 1:
                        errors.append(
                            f"Value contains delimiter matched by pattern: {rule.regex_pattern}"
                        )
                elif op == "error":
                    errors.append(f"Invalid regex pattern: {result.get('error', 'Unknown error')}")
            except Exception as e:
                errors.append(f"Regex processing error: {str(e)}")

        # --- String matching ---
        if rule.starts_with and not original.startswith(rule.starts_with):
            errors.append(f"Must start with '{rule.starts_with}'")

        if rule.ends_with and not original.endswith(rule.ends_with):
            errors.append(f"Must end with '{rule.ends_with}'")

        if rule.contains and rule.contains not in original:
            errors.append(f"Must contain '{rule.contains}'")

        # --- Unique value (pipeline-level check placeholder) ---
        if rule.unique_value:
            errors.append("UNIQUE_CHECK")

        # --- Duplicate check (pipeline-level check placeholder) ---
        if rule.check_duplicates:
            errors.append("DUPLICATE_CHECK")

        # --- Checksum ---
        if rule.checksum_validation:
            if not original.isdigit():
                errors.append("Checksum validation requires numeric value")
            else:
                if sum(int(d) for d in original) % 10 != 0:
                    errors.append("Checksum validation failed")

        # --- Age validation ---
        if rule.age_validation_min is not None or rule.age_validation_max is not None:
            if rule.date_format:
                try:
                    birth_date = pd.to_datetime(original, format=rule.date_format)
                    age = (pd.Timestamp.now() - birth_date).days // 365
                    if rule.age_validation_min is not None and age < rule.age_validation_min:
                        errors.append(f"Age {age} below minimum {rule.age_validation_min}")
                    if rule.age_validation_max is not None and age > rule.age_validation_max:
                        errors.append(f"Age {age} above maximum {rule.age_validation_max}")
                except Exception:
                    errors.append("Invalid date for age validation")
            else:
                errors.append("Age validation requires date format to be set")

        return len(errors) == 0, errors, output

    # -------------------------------------------------------------------------
    # Case helper methods — used for both validation AND transformation
    # -------------------------------------------------------------------------

    @staticmethod
    def _apply_title_case(text: str) -> str:
        """Return text converted to title case for comparison."""
        small_words = {'a', 'an', 'and', 'as', 'at', 'but', 'by', 'for',
                       'in', 'of', 'on', 'or', 'the', 'to', 'with'}
        words = text.split()
        if not words:
            return text
        result = []
        for i, word in enumerate(words):
            if i == 0 or i == len(words) - 1:
                result.append(word.capitalize())
            elif word.lower() in small_words:
                result.append(word.lower())
            else:
                result.append(word.capitalize())
        return ' '.join(result)

    @staticmethod
    def _apply_sentence_case(text: str) -> str:
        """Return text converted to sentence case for comparison."""
        if not text:
            return text
        return text[0].upper() + text[1:].lower() if len(text) > 1 else text.upper()

    @staticmethod
    def _apply_camel_case(text: str) -> str:
        """Return text converted to CamelCase for comparison."""
        words = re.split(r'[\s_-]+', text)
        return ''.join(w.capitalize() for w in words if w)

    @staticmethod
    def _apply_lower_camel_case(text: str) -> str:
        """Return text converted to lowerCamelCase for comparison."""
        words = [w for w in re.split(r'[\s_-]+', text) if w]
        if not words:
            return text
        return words[0].lower() + ''.join(w.capitalize() for w in words[1:])

    @staticmethod
    def _apply_snake_case(text: str) -> str:
        """Return text converted to snake_case for comparison."""
        text = re.sub(r'[\s-]+', '_', text)
        text = re.sub(r'([a-z])([A-Z])', r'\1_\2', text)
        return text.lower()

    @staticmethod
    def _apply_title_case_strict(text: str) -> str:
        """Return text converted to strict title case for comparison."""
        small_words = {
            'a', 'an', 'and', 'as', 'at', 'but', 'by', 'for', 'from', 'in',
            'into', 'of', 'on', 'or', 'the', 'to', 'with', 'via', 'per',
            'nor', 'yet', 'so'
        }
        words = text.split()
        if not words:
            return text
        result = []
        for i, word in enumerate(words):
            if i == 0 or i == len(words) - 1:
                result.append(word.capitalize())
            elif word.lower() in small_words:
                result.append(word.lower())
            else:
                result.append(word.capitalize())
        return ' '.join(result)
