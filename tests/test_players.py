"""Offline tests for player searches and profile metadata extraction."""

import pytest

from tennis_career._players import (
    _name_key,
    _player_birth_date,
    _search_query,
    _select_player,
)


SERENA = {
    "name": "Serena Williams",
    "tour": "W",
    "url": "https://www.tennisabstract.com/cgi-bin/wplayer.cgi?p=200033/SerenaWilliams",
}
NADAL = {
    "name": "Rafael Nadal",
    "tour": "M",
    "url": "https://www.tennisabstract.com/cgi-bin/player.cgi?p=104745/RafaelNadal",
}


@pytest.mark.parametrize("name", ["serena williams", "Serena Williams", "SerenaWilliams",
                                 "  Serena   Williams  ", "SERENA WILLIAMS"])
def test_accepts_name_variations(name):
    assert _search_query(name).casefold() == "serena williams"
    assert _select_player([SERENA], name) == {
        "name": "Serena Williams", "slug": "SerenaWilliams", "tour": "W",
    }


def test_resolves_male_player_from_multiple_results():
    assert _search_query("RafaelNadal") == "Rafael Nadal"
    assert _select_player([SERENA, NADAL], "RafaelNadal") == {
        "name": "Rafael Nadal", "slug": "RafaelNadal", "tour": "M",
    }


@pytest.mark.parametrize("name, equivalent", [
    ("Iga Świątek", "Iga Swiatek"),
    ("Juan Martín del Potro", "JuanMartinDelPotro"),
    ("Jean-Julien Rojer", "Jean Julien Rojer"),
    ("Đorđe", "Djordje"),
])
def test_normalizes_accents_and_separators(name, equivalent):
    assert _name_key(name) == _name_key(equivalent)


@pytest.mark.parametrize("name", [None, 123, [], b"SerenaWilliams"])
def test_rejects_non_string_names(name):
    with pytest.raises(TypeError, match="Player name must be a string"):
        _search_query(name)


@pytest.mark.parametrize("name", ["", "   ", "123", "---"])
def test_rejects_names_without_letters(name):
    with pytest.raises(ValueError, match="Provide a player's name"):
        _search_query(name)


@pytest.mark.parametrize("name", ["GastonSanchez", "Serena", "Williams"])
def test_rejects_unknown_and_partial_names(name):
    with pytest.raises(ValueError, match="No Tennis Abstract player found") as caught:
        _select_player([SERENA, NADAL], name)
    assert name in str(caught.value)


def test_rejects_ambiguous_exact_names():
    with pytest.raises(ValueError, match="Multiple players match"):
        _select_player([SERENA, SERENA.copy()], "SerenaWilliams")


@pytest.mark.parametrize("results", [None, {}, "not a list"])
def test_rejects_invalid_search_response(results):
    with pytest.raises(ValueError, match="invalid results list"):
        _select_player(results, "SerenaWilliams")


def test_ignores_malformed_entries_without_losing_valid_matches():
    results = [None, "unexpected", {}, {"name": 123}, SERENA]
    assert _select_player(results, "SerenaWilliams")["slug"] == "SerenaWilliams"


def test_supports_legacy_profile_urls_without_numeric_ids():
    player = dict(NADAL, url="https://www.tennisabstract.com/cgi-bin/player.cgi?p=RafaelNadal")
    assert _select_player([player], "Rafael Nadal")["slug"] == "RafaelNadal"


@pytest.mark.parametrize("url", [
    "https://example.org/?p=SerenaWilliams",
    "https://www.tennisabstract.com.example.org/?p=SerenaWilliams",
    "https://www.tennisabstract.com/",
    "https://www.tennisabstract.com/?p=..",
    "https://www.tennisabstract.com/?p=Serena%20Williams",
])
def test_rejects_unexpected_profile_urls(url):
    with pytest.raises(ValueError, match="profile URL|player identifier"):
        _select_player([dict(SERENA, url=url)], "SerenaWilliams")


@pytest.mark.parametrize("tour", [None, "", "unknown"])
def test_rejects_unknown_tours(tour):
    with pytest.raises(ValueError, match="unrecognized tour"):
        _select_player([dict(SERENA, tour=tour)], "SerenaWilliams")


@pytest.mark.parametrize("assignment", ["var dob = 19810926;", "var dob = '19810926';",
                                       'var dob = "19810926";', "var\tdob\n=19810926;"])
def test_extracts_player_birth_date(assignment):
    assert _player_birth_date("<script>" + assignment + "</script>") == "19810926"


@pytest.mark.parametrize("page", ["", "var other = 19810926;", "var dob = unknown;",
                                 "var dob = 1981092;", "var dob = 198109260;"])
def test_reports_missing_or_malformed_birth_date(page):
    with pytest.raises(ValueError, match="no player birth date"):
        _player_birth_date(page)
