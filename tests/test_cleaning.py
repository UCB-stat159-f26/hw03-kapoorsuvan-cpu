"""Check cleaning and age calculations using only in-memory career data."""

import json
from datetime import date

import pandas as pd
import pytest

from tennis_career._cleaning import _clean_matches


def _row(match_date="20000301", opponent_age="25.5", result="W", opponent="Opponent"):
    """Build the shared fields needed to exercise either career format."""
    return [match_date, "Example Open", "Hard", "S", result, "", "", "", "R32",
            "6-4 6-4", "3", opponent, "", "", "", "R", opponent_age]


def _javascript(rows):
    return "var morematchmx = " + json.dumps(rows) + ";"


def test_calculates_female_ages_across_leap_day():
    frame = _clean_matches(_javascript([_row(opponent_age="19760229")]), "19800229")
    expected_player = (date(2000, 3, 1) - date(1980, 2, 29)).days / 365.25
    expected_opponent = (date(2000, 3, 1) - date(1976, 2, 29)).days / 365.25
    assert frame.loc[0, "player_age"] == pytest.approx(expected_player)
    assert frame.loc[0, "opponent_age"] == pytest.approx(expected_opponent)
    assert frame.loc[0, "age_difference"] == pytest.approx(expected_player - expected_opponent)


def test_retains_supplied_male_age_precision():
    frame = _clean_matches(_javascript([_row(opponent_age="22.264202601")]), "19860603")
    assert frame.loc[0, "opponent_age"] == pytest.approx(22.264202601, abs=1e-12)
    expected = (date(2000, 3, 1) - date(1986, 6, 3)).days / 365.25 - 22.264202601
    assert frame.loc[0, "age_difference"] == pytest.approx(expected)


def test_age_difference_is_positive_for_an_older_player():
    frame = _clean_matches(_javascript([_row(opponent_age="15")]), "19800101")
    assert frame.loc[0, "age_difference"] > 0


def test_retains_match_metadata_and_both_results():
    frame = _clean_matches(_javascript([_row(result="W"), _row(result="L")]), "19800101")
    assert frame["result"].tolist() == ["W", "L"]
    assert frame.loc[0, ["tournament", "surface", "round", "score", "opponent"]].tolist() == [
        "Example Open", "Hard", "R32", "6-4 6-4", "Opponent",
    ]
    assert frame.loc[0, "date"] == pd.Timestamp("2000-03-01")
    assert "opponent_age_raw" not in frame.columns


def test_sorts_dates_stably_and_resets_the_index():
    rows = [_row("20010101", opponent="Later"), _row(opponent="First"),
            _row(opponent="Second")]
    frame = _clean_matches(_javascript(rows), "19800101")
    assert frame["opponent"].tolist() == ["First", "Second", "Later"]
    assert frame.index.tolist() == [0, 1, 2]


@pytest.mark.parametrize("opponent_age", ["", None, "unknown", "nan", "inf", "-inf",
                                         "-1", "121", "20000230", "20010101"])
def test_omits_invalid_opponent_ages_with_a_warning(opponent_age):
    rows = [_row(), _row(opponent_age=opponent_age)]
    with pytest.warns(UserWarning, match="Omitted 1 matches"):
        frame = _clean_matches(_javascript(rows), "19800101")
    assert len(frame) == 1
    assert frame.loc[0, "opponent_age"] == 25.5


@pytest.mark.parametrize("match_date", ["", None, "20000230", "2000031", "not a date"])
def test_omits_invalid_match_dates(match_date):
    with pytest.warns(UserWarning, match="Omitted 1 matches"):
        frame = _clean_matches(_javascript([_row(match_date)]), "19800101")
    assert frame.empty


@pytest.mark.parametrize("result", ["", None, "D", "win"])
def test_omits_unknown_results(result):
    with pytest.warns(UserWarning, match="Omitted 1 matches"):
        frame = _clean_matches(_javascript([_row(result=result)]), "19800101")
    assert frame.empty


@pytest.mark.parametrize("birth_date", ["", None, "19800230", "1980011", "1980-01-01"])
def test_rejects_invalid_player_birth_dates(birth_date):
    with pytest.raises(ValueError, match="Player birth date must be a valid YYYYMMDD date"):
        _clean_matches(_javascript([_row()]), birth_date)


@pytest.mark.parametrize("birth_date", ["20010101", "18000101"])
def test_omits_negative_or_implausible_player_ages(birth_date):
    with pytest.warns(UserWarning, match="Omitted 1 matches"):
        frame = _clean_matches(_javascript([_row()]), birth_date)
    assert frame.empty


def test_empty_input_retains_plot_columns_and_numeric_age_types():
    frame = _clean_matches(_javascript([]), "19800101")
    assert frame.empty
    assert frame.columns.tolist() == ["date", "tournament", "surface", "result", "round",
                                      "score", "opponent", "player_age", "opponent_age",
                                      "age_difference"]
    assert pd.api.types.is_datetime64_any_dtype(frame["date"])
    for column in ("player_age", "opponent_age", "age_difference"):
        assert pd.api.types.is_numeric_dtype(frame[column])


def test_counts_all_omitted_rows_in_one_warning():
    rows = [_row(), _row(opponent_age=""), _row(result="unknown"), _row("bad-date")]
    with pytest.warns(UserWarning, match="Omitted 3 matches") as caught:
        frame = _clean_matches(_javascript(rows), "19800101")
    assert len(caught) == 1
    assert len(frame) == 1
