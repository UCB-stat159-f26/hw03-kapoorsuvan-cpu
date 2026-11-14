"""Read match arrays from Tennis Abstract JavaScript without executing it."""

import json
import re


def _read_match_array(javascript):
    """Decode the JSON-compatible value assigned to ``morematchmx``."""
    if not isinstance(javascript, str):
        raise TypeError("Career JavaScript must be a string.")
    assignment = re.search(r"\bvar\s+morematchmx\s*=\s*", javascript)
    if assignment is None:
        raise ValueError("Career JavaScript has no morematchmx match array.")
    try:
        return json.JSONDecoder().raw_decode(javascript[assignment.end():])[0]
    except json.JSONDecodeError as error:
        raise ValueError("Career JavaScript contains an invalid match array.") from error


def _parse_match_rows(javascript):
    """Return rows from either career format, retaining their original fields."""
    rows = _read_match_array(javascript)
    if not isinstance(rows, list):
        raise ValueError("The career match array must be a list of rows.")
    for index, row in enumerate(rows):
        if not isinstance(row, list) or len(row) < 17:
            raise ValueError(f"Career match row {index + 1} needs at least 17 fields.")
    return rows
