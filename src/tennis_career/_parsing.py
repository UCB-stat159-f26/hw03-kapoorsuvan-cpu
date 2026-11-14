"""Read match arrays from Tennis Abstract JavaScript without executing it."""

import json
import re


def _decode_match_array(value):
    """Read a JSON-compatible array without evaluating trailing JavaScript."""
    try:
        return json.JSONDecoder().raw_decode(value)[0]
    except json.JSONDecodeError as error:
        raise ValueError("Career JavaScript contains an invalid match array.") from error


def _read_match_array(javascript, array_name="morematchmx"):
    """Read historical ``morematchmx`` or recent ``matchmx`` singles data."""
    if not isinstance(javascript, str):
        raise TypeError("Career JavaScript must be a string.")
    if array_name not in ("morematchmx", "matchmx"):
        raise ValueError("Match array name must be 'morematchmx' or 'matchmx'.")
    assignment = re.search(rf"\bvar\s+{array_name}\s*=\s*", javascript)
    if assignment is None:
        raise ValueError(f"Career JavaScript has no {array_name} match array.")
    return _decode_match_array(javascript[assignment.end():])


def _parse_match_rows(javascript, array_name="morematchmx"):
    """Return historical or recent rows, retaining either tour's original fields."""
    rows = _read_match_array(javascript, array_name)
    if not isinstance(rows, list):
        raise ValueError("The career match array must be a list of rows.")
    for index, row in enumerate(rows):
        if not isinstance(row, list) or len(row) < 17:
            raise ValueError(f"Career match row {index + 1} needs at least 17 fields.")
    return rows
