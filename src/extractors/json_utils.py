"""Utilities for handling and sanitizing JSON responses."""
import json
import re
from typing import Optional, Dict, Any


def sanitize_json_string(text: str) -> str:
    """
    Clean up common JSON formatting issues.
    
    Args:
        text: Raw JSON string
        
    Returns:
        Cleaned JSON string
    """
    # Remove markdown code blocks
    text = re.sub(r'```json\s*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'```\s*', '', text)
    
    # Remove any text before first { and after last }
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        text = match.group(0)
    
    # Fix common issues
    # 1. Replace single quotes with double quotes (only around keys/values)
    text = re.sub(r"'([^']*)':", r'"\1":', text)  # Keys
    
    # 2. Remove trailing commas before closing braces/brackets
    text = re.sub(r',(\s*[}\]])', r'\1', text)
    
    # 3. Fix None to null
    text = re.sub(r'\bNone\b', 'null', text)
    
    # 4. Fix True/False to true/false
    text = re.sub(r'\bTrue\b', 'true', text)
    text = re.sub(r'\bFalse\b', 'false', text)
    
    # 5. Remove control characters (except \n, \r, \t which are valid in JSON strings)
    # This fixes "Invalid control character" errors
    text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\r\t')
    
    # 6. Escape unescaped quotes inside string values
    # This is tricky - we'll use a more conservative approach
    
    return text.strip()


def extract_json_safely(text: str) -> Optional[Dict[str, Any]]:
    """
    Try multiple strategies to extract valid JSON from text.
    
    Args:
        text: Raw response text
        
    Returns:
        Parsed JSON dict or None
    """
    if not text or not text.strip():
        return None
    
    # Strategy 1: Try direct parsing
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    # Strategy 2: Sanitize and try again
    try:
        cleaned = sanitize_json_string(text)
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    
    # Strategy 3: Find JSON object and try parsing
    try:
        match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
    except json.JSONDecodeError:
        pass
    
    # Strategy 4: Try fixing common newline issues in strings
    try:
        # Replace newlines within strings with spaces
        fixed = re.sub(r':\s*"([^"]*\n[^"]*)"', lambda m: f': "{m.group(1).replace(chr(10), " ")}"', text)
        return json.loads(fixed)
    except json.JSONDecodeError:
        pass
    
    return None


def validate_paper_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate and fix paper data structure.
    
    Args:
        data: Raw parsed JSON
        
    Returns:
        Validated and fixed data dict
    """
    # Ensure required fields exist with correct types
    validated = {
        'title': str(data.get('title', 'Untitled')),
        'authors': data.get('authors') if isinstance(data.get('authors'), list) else [],
        'overview': data.get('overview') if isinstance(data.get('overview'), str) else None,
    }
    
    # Clean up empty strings to None
    if validated['overview'] == '':
        validated['overview'] = None
    
    # Ensure authors array doesn't contain None or empty strings
    validated['authors'] = [a for a in validated['authors'] if a]
    
    return validated