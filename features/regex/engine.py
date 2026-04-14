"""
Regex Engine - EXACT from vnew.py
"""
import re
from typing import Dict, Any

class RegexEngine:
    """Enterprise-grade unified regex engine for validation, extraction, transformation, and more."""
    
    def __init__(self, pattern: str):
        self.pattern = pattern
        try:
            self.compiled = re.compile(pattern)
            self.is_valid = True
        except re.error as e:
            self.compiled = None
            self.is_valid = False
            self.error = str(e)
    
    def detect_operation(self) -> str:
        """Automatically detect the intended regex operation based on pattern structure."""
        if not self.pattern:
            return "search"
        
        pattern = self.pattern.strip()
        
        # Validation: starts with ^ and ends with $
        if pattern.startswith("^") and pattern.endswith("$"):
            return "validate"
        
        # Remove characters: starts with [^
        if pattern.startswith("[^"):
            return "remove"
        
        # Split: contains | or , as delimiter
        if "|" in pattern or ("," in pattern and not pattern.startswith("[")):
            return "split"
        
        # Extraction: contains capture groups or common extraction patterns
        if "(" in pattern or "\\d" in pattern or "\\w" in pattern:
            return "extract"
        
        # Default fallback: search
        return "search"
    
    def process(self, value: Any) -> Dict[str, Any]:
        """
        Process a value using the appropriate regex operation.
        Returns a dict with operation type and result.
        """
        if not self.is_valid:
            return {
                "operation": "error",
                "error": self.error,
                "result": str(value) if value else ""
            }
        
        if value is None:
            value = ""
        
        value_str = str(value)
        operation = self.detect_operation()
        
        try:
            if operation == "validate":
                # Full match validation
                match = self.compiled.fullmatch(value_str)
                return {
                    "operation": "validate",
                    "result": bool(match),
                    "matched": bool(match)
                }
            
            elif operation == "remove":
                # Remove matching characters
                cleaned = self.compiled.sub("", value_str)
                return {
                    "operation": "transform",
                    "result": cleaned,
                    "original": value_str
                }
            
            elif operation == "extract":
                # Extract matching patterns
                matches = self.compiled.findall(value_str)
                # If single capture group, flatten the list
                if matches and isinstance(matches[0], tuple) and len(matches[0]) == 1:
                    matches = [m[0] for m in matches]
                return {
                    "operation": "extract",
                    "result": matches,
                    "count": len(matches)
                }
            
            elif operation == "split":
                # Split by pattern
                parts = self.compiled.split(value_str)
                return {
                    "operation": "split",
                    "result": parts,
                    "parts_count": len(parts)
                }
            
            elif operation == "search":
                # Search for first match
                match = self.compiled.search(value_str)
                return {
                    "operation": "search",
                    "result": match.group(0) if match else None,
                    "found": bool(match)
                }
            
            else:
                return {
                    "operation": "unknown",
                    "result": value_str,
                    "error": f"Unknown operation: {operation}"
                }
                
        except Exception as e:
            return {
                "operation": operation,
                "error": str(e),
                "result": value_str
            }
