"""
Phone number validation for UAE and India.

Returns hard errors only for truly invalid formats.
Normalization notes (format differences) are returned separately as warnings
so the caller can choose whether to surface them.
"""
import re
import pandas as pd
from typing import Tuple, List


def validate_uae_india_phone(phone: str) -> Tuple[str, List[str]]:
    """Validate a phone number against UAE and India formats.

    Args:
        phone: Original phone number string.

    Returns:
        Tuple of (original_phone, list_of_hard_errors).
        Normalization notes are NOT included in errors — only genuinely
        invalid formats produce error messages.
    """
    errors: List[str] = []

    if not phone or pd.isna(phone):
        errors.append("Phone number is empty")
        return str(phone) if phone else "", errors

    original = str(phone).strip()

    # Remove all non-digit characters except +
    cleaned = re.sub(r'[^\d+]', '', original)

    # Remove + for processing
    if cleaned.startswith('+'):
        cleaned = cleaned[1:]

    # --- UAE ---
    if cleaned.startswith('971'):
        national_number = cleaned[3:]
        if len(national_number) == 9 and national_number[0] == '5':
            return original, errors
        if len(national_number) in (8, 9) and national_number[0] in '234679':
            return original, errors
        errors.append(f"Invalid UAE phone format (original: '{original}')")
        return original, errors

    # --- India ---
    if cleaned.startswith('91'):
        national_number = cleaned[2:]
        if len(national_number) == 10 and national_number[0] in '6789':
            return original, errors
        errors.append(f"Invalid India phone format (original: '{original}')")
        return original, errors

    # --- Missing country code heuristics ---
    if len(cleaned) == 10 and cleaned[0] in '6789':
        errors.append(f"Missing country code — looks like India mobile (original: '{original}')")
        return original, errors

    if len(cleaned) == 9 and cleaned[0] == '5':
        errors.append(f"Missing country code — looks like UAE mobile (original: '{original}')")
        return original, errors

    errors.append(f"Phone must be UAE (+971) or India (+91) format (original: '{original}')")
    return original, errors
