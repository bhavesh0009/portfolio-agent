"""
Column Name Management
Consolidated module for column name mapping, search, and validation.

Combines functionality from:
- column_utils.py (basic mapping)
- column_mapper.py (fuzzy search)
- query_validator.py (validation and auto-correction)
"""

import json
import re
from pathlib import Path
from typing import List, Dict, Optional
from difflib import SequenceMatcher


# ============================================================================
# SECTION 1: Core Data Loading and Mapping
# ============================================================================

# Load mapping once at module level
_MAPPING_FILE = Path(__file__).parent.parent / 'data' / 'column_name_mapping.json'
_COLUMN_MAPPING = None


def load_column_mapping() -> Dict:
    """Load column mapping from JSON file (cached)"""
    global _COLUMN_MAPPING

    if _COLUMN_MAPPING is None:
        if _MAPPING_FILE.exists():
            with open(_MAPPING_FILE, 'r', encoding='utf-8') as f:
                _COLUMN_MAPPING = json.load(f)
        else:
            _COLUMN_MAPPING = {}

    return _COLUMN_MAPPING


def get_short_name(config_name: str) -> Optional[str]:
    """
    Get short name (table header base) for a configuration name.

    Args:
        config_name: Configuration name (e.g., "Sales growth 3Years")

    Returns:
        Short name (e.g., "Sales Var 3Yrs") or None if not found
    """
    mapping = load_column_mapping()
    if config_name in mapping:
        return mapping[config_name]['short_name']
    return None


def map_to_short_names(config_names: list) -> list:
    """
    Map list of config names to short names.

    Args:
        config_names: List of configuration names

    Returns:
        List of short names (unmapped names returned as-is)
    """
    result = []
    for name in config_names:
        short = get_short_name(name)
        result.append(short if short else name)
    return result


def get_all_column_names() -> List[str]:
    """Get list of all valid column configuration names"""
    mapping = load_column_mapping()
    return list(mapping.keys())


# ============================================================================
# SECTION 2: Search and Discovery
# ============================================================================

def calculate_similarity(str1: str, str2: str) -> float:
    """Calculate similarity ratio between two strings (case-insensitive)"""
    return SequenceMatcher(None, str1.lower(), str2.lower()).ratio()


def search_column_mapping(
    search_term: str,
    max_results: int = 5,
    min_similarity: float = 0.3
) -> List[Dict]:
    """
    Search for column names using fuzzy matching.

    Args:
        search_term: Natural language term to search for
        max_results: Maximum number of results to return
        min_similarity: Minimum similarity score (0.0 to 1.0)

    Returns:
        List of matching column mappings with context, sorted by relevance
        Each result contains:
        - config_name: Configuration name (use this in queries)
        - short_name: Short name (appears in table)
        - description: Full description
        - similarity: Match score (0.0 to 1.0)

    Example:
        >>> results = search_column_mapping("market cap")
        >>> print(results[0])
        {
            "config_name": "Market Capitalization",
            "short_name": "Mar Cap",
            "description": "Market Capitalization of the company...",
            "similarity": 0.85
        }
    """
    mapping = load_column_mapping()
    matches = []

    search_lower = search_term.lower()

    for config_name, details in mapping.items():
        # Calculate similarity scores for different fields
        name_similarity = calculate_similarity(search_term, config_name)
        short_name_similarity = calculate_similarity(search_term, details.get('short_name', ''))
        desc_similarity = calculate_similarity(search_term, details.get('description', ''))

        # Check for substring matches (exact partial match)
        name_contains = search_lower in config_name.lower()
        short_contains = search_lower in details.get('short_name', '').lower()
        desc_contains = search_lower in details.get('description', '').lower()

        # Calculate overall match score
        # Prioritize: exact substring match > config name > short name > description
        if name_contains:
            match_score = max(0.9, name_similarity)
        elif short_contains:
            match_score = max(0.8, short_name_similarity)
        elif desc_contains:
            match_score = max(0.7, desc_similarity)
        else:
            # Use best similarity score
            match_score = max(name_similarity, short_name_similarity, desc_similarity * 0.5)

        if match_score >= min_similarity:
            matches.append({
                'config_name': config_name,
                'short_name': details.get('short_name', ''),
                'description': details.get('description', ''),
                'group': details.get('group', ''),
                'similarity': round(match_score, 3)
            })

    # Sort by similarity score (descending)
    matches.sort(key=lambda x: x['similarity'], reverse=True)

    return matches[:max_results]


def find_exact_match(column_name: str) -> Optional[Dict]:
    """
    Find exact match for a column name (case-insensitive).

    Args:
        column_name: Column name to look up

    Returns:
        Mapping details if found, None otherwise
    """
    mapping = load_column_mapping()

    # Try exact match (case-insensitive)
    for config_name, details in mapping.items():
        if config_name.lower() == column_name.lower():
            return {
                'config_name': config_name,
                'short_name': details.get('short_name', ''),
                'description': details.get('description', ''),
                'group': details.get('group', '')
            }

    return None


def print_search_results(search_term: str, max_results: int = 5):
    """
    Print formatted search results for debugging.

    Args:
        search_term: Term to search for
        max_results: Maximum results to show
    """
    results = search_column_mapping(search_term, max_results)

    if not results:
        print(f"\nNo matches found for: '{search_term}'")
        return

    print(f"\n{'='*70}")
    print(f"Search results for: '{search_term}'")
    print(f"{'='*70}")

    for i, result in enumerate(results, 1):
        print(f"\n{i}. Config Name: {result['config_name']}")
        print(f"   Short Name:  {result['short_name']}")
        print(f"   Description: {result['description'][:80]}...")
        print(f"   Match Score: {result['similarity']}")
        print(f"   Group:       {result['group']}")

    print(f"\n{'='*70}\n")


# ============================================================================
# SECTION 3: Validation and Auto-Correction
# ============================================================================

def normalize_column_name(column_name: str) -> str:
    """
    Normalize column name for comparison.
    Handles common variations in spacing and punctuation.

    Args:
        column_name: Column name to normalize

    Returns:
        Normalized column name
    """
    # Strip whitespace
    normalized = column_name.strip()

    # Common corrections
    corrections = {
        'market capitalization': 'Market Capitalization',
        'p/e': 'Price to Earning',
        'pe': 'Price to Earning',
        'roe': 'Return on equity',
        'roe %': 'Return on equity',
        'roce': 'Return on capital employed',
        'roce %': 'Return on capital employed',
        'debt to equity': 'Debt to equity',
        'debt / eq': 'Debt to equity',
        'sales growth 3years': 'Sales growth 3Years',
        'profit growth 3years': 'Profit growth 3Years',
        'sales growth 5years': 'Sales growth 5Years',
        'profit growth 5years': 'Profit growth 5Years',
    }

    lower_name = normalized.lower()
    if lower_name in corrections:
        return corrections[lower_name]

    return normalized


def validate_column(column_name: str, auto_correct: bool = True) -> Dict[str, any]:
    """
    Validate a single column name and optionally suggest corrections.

    Args:
        column_name: Column name to validate
        auto_correct: If True, attempt to find best match

    Returns:
        Dictionary with validation results:
        - is_valid: Boolean indicating if column is valid
        - corrected_name: Suggested correct name (if different)
        - original_name: Original input name
        - match_score: Confidence of correction (0.0 to 1.0)
        - alternatives: List of alternative matches
    """
    # Normalize first
    normalized = normalize_column_name(column_name)

    # Try exact match
    exact_match = find_exact_match(normalized)
    if exact_match:
        return {
            'is_valid': True,
            'corrected_name': exact_match['config_name'],
            'original_name': column_name,
            'match_score': 1.0,
            'alternatives': []
        }

    # If auto-correct enabled, search for best match
    if auto_correct:
        matches = search_column_mapping(normalized, max_results=5, min_similarity=0.5)

        if matches:
            best_match = matches[0]
            alternatives = [m['config_name'] for m in matches[1:]]

            return {
                'is_valid': False,
                'corrected_name': best_match['config_name'],
                'original_name': column_name,
                'match_score': best_match['similarity'],
                'alternatives': alternatives,
                'description': best_match['description']
            }

    # No match found
    return {
        'is_valid': False,
        'corrected_name': None,
        'original_name': column_name,
        'match_score': 0.0,
        'alternatives': []
    }


def validate_columns(
    columns: List[str],
    auto_correct: bool = True,
    min_confidence: float = 0.7
) -> Dict[str, any]:
    """
    Validate a list of column names and suggest corrections.

    Args:
        columns: List of column names to validate
        auto_correct: If True, attempt to find best matches
        min_confidence: Minimum confidence score for auto-correction

    Returns:
        Dictionary with validation results:
        - all_valid: Boolean indicating if all columns are valid
        - corrections: Dict mapping original names to corrected names
        - warnings: List of low-confidence corrections
        - invalid: List of columns that couldn't be matched
    """
    corrections = {}
    warnings = []
    invalid = []

    for col in columns:
        result = validate_column(col, auto_correct=auto_correct)

        if result['is_valid']:
            # Column is valid, but might need case correction
            if result['original_name'] != result['corrected_name']:
                corrections[result['original_name']] = result['corrected_name']
        elif result['corrected_name']:
            # Found a correction
            if result['match_score'] >= min_confidence:
                corrections[result['original_name']] = result['corrected_name']
            else:
                # Low confidence - add warning
                warnings.append({
                    'original': result['original_name'],
                    'suggested': result['corrected_name'],
                    'confidence': result['match_score'],
                    'alternatives': result['alternatives']
                })
        else:
            # No match found
            invalid.append(result['original_name'])

    return {
        'all_valid': len(invalid) == 0 and len(warnings) == 0,
        'corrections': corrections,
        'warnings': warnings,
        'invalid': invalid
    }


def validate_query_syntax(query: str) -> Dict[str, any]:
    """
    Validate query syntax and column names used in query.

    Args:
        query: Screening query string

    Returns:
        Dictionary with validation results:
        - is_valid: Boolean indicating if query is valid
        - issues: List of identified issues
        - suggestions: List of suggested fixes
    """
    issues = []
    suggestions = []

    # Extract potential column names from query
    # Look for patterns like "Column Name > value" or "Column Name < value"
    # This is a simple heuristic - matches word sequences before comparison operators
    potential_columns = re.findall(r'([A-Za-z][A-Za-z0-9\s]+?)\s*(?:>|<|=|>=|<=)', query)

    for col in potential_columns:
        col = col.strip()
        result = validate_column(col, auto_correct=True)

        if not result['is_valid']:
            if result['corrected_name']:
                issues.append(f"Column '{col}' might be incorrect")
                suggestions.append(f"Did you mean '{result['corrected_name']}'? (confidence: {result['match_score']:.2f})")
            else:
                issues.append(f"Column '{col}' not found in mapping")
                suggestions.append(f"Search for similar column names or check spelling")

    return {
        'is_valid': len(issues) == 0,
        'issues': issues,
        'suggestions': suggestions
    }


def auto_correct_columns(columns: List[str], min_confidence: float = 0.8) -> List[str]:
    """
    Auto-correct a list of column names with high confidence.

    Args:
        columns: List of column names
        min_confidence: Minimum confidence for auto-correction

    Returns:
        List of corrected column names
    """
    validation = validate_columns(columns, auto_correct=True, min_confidence=min_confidence)

    corrected = []
    for col in columns:
        if col in validation['corrections']:
            corrected.append(validation['corrections'][col])
        else:
            corrected.append(col)

    return corrected


def print_validation_report(columns: List[str], auto_correct: bool = True):
    """
    Print detailed validation report for debugging.

    Args:
        columns: List of column names to validate
        auto_correct: Whether to attempt auto-correction
    """
    print(f"\n{'='*70}")
    print(f"Column Validation Report")
    print(f"{'='*70}")

    validation = validate_columns(columns, auto_correct=auto_correct)

    if validation['all_valid']:
        print("\nAll columns are valid!")
    else:
        if validation['corrections']:
            print("\nAuto-corrections applied:")
            for orig, corrected in validation['corrections'].items():
                print(f"  '{orig}' -> '{corrected}'")

        if validation['warnings']:
            print("\nWarnings (low confidence):")
            for warning in validation['warnings']:
                print(f"  '{warning['original']}' -> '{warning['suggested']}' (confidence: {warning['confidence']:.2f})")
                if warning['alternatives']:
                    print(f"    Alternatives: {', '.join(warning['alternatives'][:3])}")

        if validation['invalid']:
            print("\nInvalid columns (no match found):")
            for col in validation['invalid']:
                print(f"  '{col}'")

    print(f"\n{'='*70}\n")


# ============================================================================
# Module Testing
# ============================================================================

if __name__ == "__main__":
    print("=== Column Manager Test Suite ===\n")

    # Test 1: Search functionality
    print("TEST 1: Fuzzy Search")
    test_search_terms = ["market cap", "ROE", "sales growth", "P/E", "debt equity"]
    for term in test_search_terms:
        print_search_results(term, max_results=3)

    # Test 2: Validation
    print("\nTEST 2: Column Validation")
    test_columns = [
        "Market Capitalization",  # Exact match
        "market capitalization",  # Case variation
        "P/E",  # Common abbreviation
        "ROE %",  # Output name instead of config name
        "Sales growth 3Years",  # Exact match
        "sales growth 3years",  # Case variation
        "Invalid Column Name",  # Invalid
    ]
    print_validation_report(test_columns)

    # Test 3: Auto-correction
    print("\nTEST 3: Auto-Correction")
    print("Auto-corrected columns:")
    corrected = auto_correct_columns(test_columns)
    for orig, corr in zip(test_columns, corrected):
        if orig != corr:
            print(f"  '{orig}' -> '{corr}'")
