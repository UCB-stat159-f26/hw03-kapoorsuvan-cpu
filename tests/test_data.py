"""Exercise retrieval with mocked HTTP responses; never contact live servers."""

import json
from unittest.mock import Mock

import pytest
import requests

from tennis_career.data import _download, _merge_matches, get_player_matches


@pytest.fixture(autouse=True)
def http_get(monkeypatch):
    """Fail unexpected requests rather than letting a test access the network."""
    mock = Mock(side_effect=AssertionError("Unexpected HTTP request in offline test"))
    monkeypatch.setattr("tennis_career.data.requests.get", mock)
    return mock


def _response(body, status=200):
    response = requests.Response()
    response.status_code = status
    response.url = "https://www.tennisabstract.com/mock"
    response.encoding = "utf-8"
    response._content = (body if isinstance(body, str) else json.dumps(body)).encode()
    return response


def _row(match_date="20000101", opponent_age="25.5", identifier="2000-event-001"):
    return [match_date, "Open", "Hard", "S", "W", "", "", "", "F", "6-4 6-4",
            "3", "Opponent", "", "", "", "R", opponent_age] + [""] * 9 + [identifier]


def _sources(tour="W", rows=None, historical=None):
    name, slug = ("Serena Williams", "SerenaWilliams") if tour == "W" else ("Rafael Nadal", "RafaelNadal")
    player = {"name": name, "tour": tour,
              "url": f"https://www.tennisabstract.com/cgi-bin/player.cgi?p=123/{slug}"}
    rows = [_row()] if rows is None else rows
    historical = rows if historical is None else historical
    profile = "var dob = 19800101; var matchmx = " + json.dumps(rows) + ";"
    archive = "var morematchmx = " + json.dumps(historical) + ";"
    return [_response([player]), _response(profile), _response(archive)]


@pytest.mark.parametrize("tour, name, endpoint", [
    ("W", "serena williams", "/jsmatches/SerenaWilliams.js"),
    ("M", "RafaelNadal", "/cgi-bin/player-classic.cgi"),
])
def test_retrieves_and_cleans_both_tours(http_get, tour, name, endpoint):
    http_get.side_effect = _sources(tour)
    data = get_player_matches(name)
    assert len(data) == 1
    assert data.loc[0, "opponent_age"] == 25.5
    assert data.loc[0, "age_difference"] == pytest.approx(data.loc[0, "player_age"] - 25.5)
    assert data.attrs["player_name"] == ("Serena Williams" if tour == "W" else "Rafael Nadal")
    assert http_get.call_count == 3
    assert http_get.call_args_list[1].args[0].endswith(endpoint)
    assert all(call.kwargs["timeout"] == 30 for call in http_get.call_args_list)
    assert http_get.call_args_list[0].kwargs["params"]["q"].lower() == name.replace("Nadal", " Nadal").lower()


def test_combines_old_and_recent_matches_in_date_order(http_get):
    old = _row("19990101", "19700101", "1999-event-001")
    recent = _row()
    http_get.side_effect = _sources(rows=[recent], historical=[old, recent])
    data = get_player_matches("SerenaWilliams")
    assert len(data) == 2
    assert data["date"].dt.strftime("%Y%m%d").tolist() == ["19990101", "20000101"]


def test_prefers_profile_record_when_opponent_name_changed():
    recent = _row()
    historical = recent.copy()
    historical[11] = "Former opponent spelling"
    assert _merge_matches([recent], [historical]) == [recent]


def test_deduplicates_matching_details_when_ids_changed():
    recent = _row()
    historical = _row(identifier="2000-revised-001")
    assert _merge_matches([recent], [historical]) == [recent]


def test_preserves_distinct_rounds_against_the_same_opponent():
    final = _row()
    round_robin = _row(identifier="2000-event-002")
    round_robin[8] = "RR"
    assert _merge_matches([final], [round_robin]) == [final, round_robin]


def test_handles_rows_without_match_ids():
    row = _row()[:17]
    assert _merge_matches([row], [row.copy()]) == [row]


def test_warns_and_uses_profile_when_archive_is_missing(http_get):
    http_get.side_effect = _sources()[:2] + [_response("Not found", 404)]
    with pytest.warns(UserWarning, match="No career archive is available"):
        data = get_player_matches("SerenaWilliams")
    assert len(data) == 1


def test_rejects_unknown_player_without_fetching_profiles(http_get):
    http_get.side_effect = [_response([])]
    with pytest.raises(ValueError, match="No Tennis Abstract player found for 'GastonSanchez'"):
        get_player_matches("GastonSanchez")
    assert http_get.call_count == 1


@pytest.mark.parametrize("name, error", [(None, TypeError), ("", ValueError), ("123", ValueError)])
def test_rejects_invalid_names_before_http(http_get, name, error):
    with pytest.raises(error):
        get_player_matches(name)
    http_get.assert_not_called()


def test_reports_non_json_search_response(http_get):
    http_get.side_effect = [_response("<html>Service unavailable</html>")]
    with pytest.raises(ValueError, match="search returned invalid JSON"):
        get_player_matches("SerenaWilliams")


@pytest.mark.parametrize("error", [requests.Timeout("timed out"), requests.ConnectionError("offline")])
def test_reports_network_failures_with_source_context(http_get, error):
    http_get.side_effect = error
    with pytest.raises(RuntimeError, match="Could not retrieve.*search.cgi") as caught:
        get_player_matches("SerenaWilliams")
    assert caught.value.__cause__ is error


@pytest.mark.parametrize("status", [403, 404, 429, 500])
def test_reports_required_source_http_errors(http_get, status):
    http_get.side_effect = [_response("Error", status)]
    with pytest.raises(RuntimeError, match=str(status)):
        _download("/required-source")


def test_does_not_hide_archive_server_errors(http_get):
    http_get.side_effect = _sources()[:2] + [_response("Server error", 500)]
    with pytest.raises(RuntimeError, match="SerenaWilliamsCareer.js"):
        get_player_matches("SerenaWilliams")


def test_rejects_empty_career(http_get):
    http_get.side_effect = _sources(rows=[], historical=[])
    with pytest.raises(ValueError, match="No usable singles matches were found"):
        get_player_matches("SerenaWilliams")


def test_rejects_career_with_only_unusable_rows(http_get):
    http_get.side_effect = _sources(rows=[_row(opponent_age="")], historical=[])
    with pytest.warns(UserWarning, match="Omitted 1 matches"):
        with pytest.raises(ValueError, match="No usable singles matches"):
            get_player_matches("SerenaWilliams")


def test_reports_missing_birth_date(http_get):
    sources = _sources()
    sources[1] = _response("var matchmx = " + json.dumps([_row()]) + ";")
    http_get.side_effect = sources
    with pytest.raises(ValueError, match="no player birth date"):
        get_player_matches("SerenaWilliams")


def test_rejects_malformed_archive_instead_of_returning_partial_data(http_get):
    http_get.side_effect = _sources()[:2] + [_response("var morematchmx = [")]
    with pytest.raises(ValueError, match="invalid match array"):
        get_player_matches("SerenaWilliams")
