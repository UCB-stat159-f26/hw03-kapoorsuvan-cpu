"""Offline checks for the career JavaScript parser."""

import json

import pytest

from tennis_career._parsing import _parse_match_rows


# First rows from the assignment's female and male career examples.
FEMALE_ROW = [
    "19951030", "Canadian Open", "Carpet", "W", "L", "", "", "WC", "Q1",
    "6-1 6-1", "3", "Anne Miller", "149", "7", "", "R", "19770119", "",
    "USA", "0", "", "", "", "", "", "", "1995-W-WT-CAN-02A-1995-013",
]
MALE_ROW = [
    "20010910", "Spain F10", "Hard", "S", "L", "", "", "WC", "R32",
    "2-6 7-5 6-2", "3", "Guillermo Platel", "731", "", "", "R",
    "22.264202601", "", "ESP", "0",
    *([""] * 23), "2001-M-FU-ESP-10A-2001-002", "", "1", "1",
]


@pytest.mark.parametrize("row", [FEMALE_ROW, MALE_ROW], ids=["female", "male"])
def test_preserves_all_fields_in_both_formats(row):
    javascript = "var morematchmx = " + json.dumps([row]) + ";"
    assert _parse_match_rows(javascript) == [row]


def test_preserves_multiple_rows_and_their_order():
    rows = [FEMALE_ROW, FEMALE_ROW.copy()]
    rows[1][4] = "W"
    assert _parse_match_rows("var morematchmx = " + json.dumps(rows)) == rows


def test_accepts_empty_match_array():
    assert _parse_match_rows("var morematchmx = [];") == []


def test_accepts_whitespace_and_unrelated_javascript():
    javascript = "var title = 'Career';\nvar\tmorematchmx\n = \n[];\nunused();"
    assert _parse_match_rows(javascript) == []


def test_preserves_escaped_text_and_brackets_inside_strings():
    row = FEMALE_ROW.copy()
    row[1] = 'Open [A] "Final" \\ indoor'
    assert _parse_match_rows("var morematchmx = " + json.dumps([row])) == [row]


@pytest.mark.parametrize("javascript", ["", "var other = [];", "var morematchmx_extra = [];"])
def test_rejects_missing_match_array(javascript):
    with pytest.raises(ValueError, match="no morematchmx match array"):
        _parse_match_rows(javascript)


@pytest.mark.parametrize("value", ["[", "[[1,]", "undefined", "makeMatches()"])
def test_rejects_invalid_json_without_executing_javascript(value):
    with pytest.raises(ValueError, match="invalid match array"):
        _parse_match_rows("var morematchmx = " + value)


@pytest.mark.parametrize("value", [None, {}, 42, "matches"])
def test_rejects_non_array_values(value):
    with pytest.raises(ValueError, match="must be a list of rows"):
        _parse_match_rows("var morematchmx = " + json.dumps(value))


@pytest.mark.parametrize("row", [[], [""] * 16, None, {}, "not a row"])
def test_reports_the_position_of_a_malformed_row(row):
    javascript = "var morematchmx = " + json.dumps([FEMALE_ROW, row])
    with pytest.raises(ValueError, match="row 2 needs at least 17 fields"):
        _parse_match_rows(javascript)


@pytest.mark.parametrize("javascript", [None, 42, [], b"var morematchmx = [];"])
def test_rejects_non_string_input(javascript):
    with pytest.raises(TypeError, match="must be a string"):
        _parse_match_rows(javascript)
