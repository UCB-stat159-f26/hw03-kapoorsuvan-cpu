"""Convert career rows to match data with ages measured in decimal years."""

import warnings

import pandas as pd

from ._parsing import _parse_match_rows


_FIELDS = {
    "date": 0, "tournament": 1, "surface": 2, "result": 4,
    "round": 8, "score": 9, "opponent": 11, "opponent_age_raw": 16,
}
_DAYS_PER_YEAR = 365.25


def _parse_dates(values):
    """Parse eight-digit YYYYMMDD strings; invalid values become NaT."""
    text = values.astype("string")
    text = text.where(text.str.fullmatch(r"\d{8}", na=False))
    return pd.to_datetime(text, format="%Y%m%d", errors="coerce")


def _parse_birth_date(birth_date):
    """Require a valid player birth date in YYYYMMDD format."""
    date = _parse_dates(pd.Series([birth_date])).iloc[0]
    if pd.isna(date):
        raise ValueError("Player birth date must be a valid YYYYMMDD date.")
    return date


def _match_frame(rows):
    """Select the fields shared by the female and male career formats."""
    values = {name: [row[index] for row in rows] for name, index in _FIELDS.items()}
    frame = pd.DataFrame(values)
    frame["date"] = _parse_dates(frame["date"])
    return frame


def _opponent_ages(raw_ages, match_dates):
    """Convert birth dates to ages and retain supplied decimal ages."""
    text = raw_ages.astype("string").str.strip()
    is_birth_date = text.str.fullmatch(r"\d{8}", na=False)
    birthdays = _parse_dates(text.where(is_birth_date))
    calculated = (match_dates - birthdays).dt.days / _DAYS_PER_YEAR
    supplied = pd.to_numeric(text.where(~is_birth_date), errors="coerce")
    return supplied.where(~is_birth_date, calculated).astype(float)


def _valid_matches(frame):
    """Keep W/L rows with valid dates and ages between zero and 120 years."""
    valid = frame["date"].notna() & frame["result"].isin(["W", "L"])
    valid &= frame["player_age"].between(0, 120)
    valid &= frame["opponent_age"].between(0, 120)
    omitted = int((~valid).sum())
    if omitted:
        warnings.warn(f"Omitted {omitted} matches with invalid dates, ages, or results.",
                      UserWarning, stacklevel=2)
    return frame.loc[valid].sort_values("date", kind="stable").reset_index(drop=True)


def _clean_matches(javascript, birth_date):
    """Return plot-ready matches; age difference is player minus opponent age."""
    birthday = _parse_birth_date(birth_date)
    frame = _match_frame(_parse_match_rows(javascript))
    frame["player_age"] = (frame["date"] - birthday).dt.days / _DAYS_PER_YEAR
    frame["opponent_age"] = _opponent_ages(frame.pop("opponent_age_raw"), frame["date"])
    frame["age_difference"] = frame["player_age"] - frame["opponent_age"]
    return _valid_matches(frame)
