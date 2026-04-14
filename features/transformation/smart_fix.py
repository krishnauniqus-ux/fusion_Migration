"""
Smart auto-fix functionality - EXACT from vnew.py
"""
import re
import streamlit as st
from typing import Any



# =============================================================================
# SMART AUTO-FIX ENGINE
# =============================================================================

def smart_auto_fix(value: str, pattern: str, operation: str) -> str:
    """
    Intelligent auto-fix for common data issues using Python logic + AI fallback.
    
    Args:
        value: The original value that failed validation
        pattern: The regex pattern it should match
        operation: The type of operation (validate, extract, search)
    
    Returns:
        Fixed value that hopefully matches the pattern
    """
    if not value or not pattern:
        return value
    
    original_value = str(value).strip()
    fixed_value = original_value
    
    # =============================================================================
    # PYTHON-BASED SMART FIXES (Fast, No API calls)
    # =============================================================================
    
    # 1. Email fixes
    if '@' in pattern or 'email' in pattern.lower():
        # Fix double @@ -> single @
        fixed_value = re.sub(r'@{2,}', '@', fixed_value)
        
        # Fix missing domain extension
        if '@' in fixed_value and '.' not in fixed_value.split('@')[-1]:
            fixed_value = fixed_value + '.com'
        
        # Fix spaces in email
        fixed_value = fixed_value.replace(' ', '')
        
        # Fix common typos
        fixed_value = fixed_value.replace('@@', '@')
        fixed_value = fixed_value.replace('.@', '@')
        fixed_value = fixed_value.replace('@.', '@')
        
        # Fix missing @ before domain
        if '@' not in fixed_value and '.' in fixed_value:
            parts = fixed_value.split('.')
            if len(parts) >= 2:
                fixed_value = f"{parts[0]}@{'.'.join(parts[1:])}"
    
    # 2. Phone number fixes
    elif r'\d' in pattern and (len(original_value) >= 10 or '-' in original_value or '(' in original_value):
        # Extract only digits
        digits = re.sub(r'\D', '', fixed_value)
        
        # Format based on pattern structure
        if '(' in pattern:  # (XXX) XXX-XXXX format
            if len(digits) >= 10:
                fixed_value = f"({digits[:3]}) {digits[3:6]}-{digits[6:10]}"
        elif '-' in pattern:  # XXX-XXX-XXXX format
            if len(digits) >= 10:
                fixed_value = f"{digits[:3]}-{digits[3:6]}-{digits[6:10]}"
        else:  # Plain digits
            fixed_value = digits[:10] if len(digits) >= 10 else digits
    
    # 3. Date fixes
    elif any(date_indicator in pattern for date_indicator in ['\\d{4}', '\\d{2}', 'YYYY', 'MM', 'DD']):
        # Try to parse and reformat dates
        try:
            # Remove extra spaces
            fixed_value = ' '.join(fixed_value.split())
            
            # Fix common date separators
            fixed_value = re.sub(r'[/\-\s]+', '-', fixed_value)
            
            # Try parsing
            parsed = pd.to_datetime(fixed_value, errors='coerce')
            if not pd.isna(parsed):
                # Format based on pattern
                if 'YYYY' in pattern or r'\d{4}' in pattern:
                    if 'MM' in pattern or 'DD' in pattern:
                        fixed_value = parsed.strftime('%Y-%m-%d')
                    else:
                        fixed_value = parsed.strftime('%Y%m%d')
        except:
            pass
    
    # 4. URL fixes
    elif 'http' in pattern.lower() or 'www' in pattern.lower():
        # Add missing protocol
        if not fixed_value.startswith(('http://', 'https://')):
            if fixed_value.startswith('www.'):
                fixed_value = 'https://' + fixed_value
            elif '.' in fixed_value:
                fixed_value = 'https://' + fixed_value
        
        # Remove spaces
        fixed_value = fixed_value.replace(' ', '')
    
    # 5. Whitespace fixes (general)
    # Remove leading/trailing spaces
    fixed_value = fixed_value.strip()
    
    # Fix multiple spaces
    fixed_value = ' '.join(fixed_value.split())
    
    # 6. Special character fixes
    # Remove duplicate special characters
    fixed_value = re.sub(r'([!@#$%^&*()_+=\-\[\]{};:\'",.<>?/\\|`~])\1+', r'\1', fixed_value)
    
    # 7. Case fixes (if pattern suggests specific case)
    if pattern.isupper():
        fixed_value = fixed_value.upper()
    elif pattern.islower():
        fixed_value = fixed_value.lower()
    
    # =============================================================================
    # AI-BASED SMART FIXES (Fallback for complex cases)
    # =============================================================================
    
    # If Python fixes didn't work, try AI (only if Azure OpenAI is configured)
    if fixed_value == original_value or not re.search(pattern, fixed_value):
        try:
            # Check if Azure OpenAI is configured
            if hasattr(st.secrets, 'endpoint') and st.secrets.endpoint:
                fixed_value = ai_auto_fix(original_value, pattern, operation)
        except:
            # AI not available or failed, return Python-fixed value
            pass
    
    return fixed_value


def ai_auto_fix(value: str, pattern: str, operation: str) -> str:
    """
    Use Azure OpenAI to intelligently fix data that doesn't match the pattern.
    
    Args:
        value: The original value that failed validation
        pattern: The regex pattern it should match
        operation: The type of operation (validate, extract, search)
    
    Returns:
        AI-fixed value
    """
    try:
        from openai import AzureOpenAI
        
        client = AzureOpenAI(
            azure_endpoint=st.secrets.endpoint,
            api_key=st.secrets.api_key,
            api_version=st.secrets.api_version
        )
        
        # Create a focused prompt for the AI
        prompt = f"""You are a data cleaning expert. Fix this value to match the required pattern.

Original Value: {value}
Required Pattern (Regex): {pattern}
Operation Type: {operation}

Common issues to fix:
- Double characters (@@, --, etc.)
- Missing characters
- Wrong format
- Extra spaces
- Typos

Return ONLY the fixed value, nothing else. If you cannot fix it, return the original value.

Fixed Value:"""
        
        response = client.chat.completions.create(
            model=st.secrets.deployment_name,
            messages=[
                {
                    "role": "system",
                    "content": "You are a data cleaning expert. Fix data to match patterns. Return only the fixed value, no explanations."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            max_tokens=100,
            temperature=0.1  # Low temperature for consistent fixes
        )
        
        fixed_value = response.choices[0].message.content.strip()
        
        # Remove any quotes or extra formatting
        fixed_value = fixed_value.strip('"\'`')
        
        return fixed_value
        
    except Exception as e:
        # If AI fails, return original value
        return value
