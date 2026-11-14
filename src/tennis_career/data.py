"""Retrieve singles match data from Tennis Abstract."""

import json
import re
import warnings

import requests

from ._cleaning import _clean_matches
from ._parsing import _parse_match_rows
from ._players import _player_birth_date, _search_query, _select_player


_BASE_URL = "https://www.tennisabstract.com"


def _download(path, params=None, allow_missing=False):
    """Fetch a source with a timeout and descriptive HTTP/network errors."""
    try:
        response = requests.get(_BASE_URL + path, params=params, timeout=30)
        if allow_missing and response.status_code == 404:
            return None
        response.raise_for_status()
        return response
    except requests.RequestException as error:
        raise RuntimeError(f"Could not retrieve Tennis Abstract source {path}: {error}") from error


def _lookup_player(player_name):
    """Resolve a supplied name through the site's player search."""
    query = _search_query(player_name)
    response = _download("/cgi-bin/search.cgi", params={"q": query})
    try:
        results = response.json()
    except ValueError as error:
        raise ValueError("Tennis Abstract search returned invalid JSON.") from error
    return _select_player(results, player_name)


def _profile_page(player):
    """Read metadata and recent singles from the source used by each tour."""
    if player["tour"] == "W":
        return _download(f"/jsmatches/{player['slug']}.js").text
    return _download("/cgi-bin/player-classic.cgi", params={"p": player["slug"]}).text


def _archive_rows(player):
    """Read historical matches when an archive is available for the player."""
    response = _download(f"/jsmatches/{player['slug']}Career.js", allow_missing=True)
    if response is None:
        warnings.warn("No career archive is available; using the profile's matches only.",
                      UserWarning, stacklevel=2)
        return []
    return _parse_match_rows(response.text)


def _match_keys(row):
    """Identify overlapping matches by source ID or shared match details."""
    keys = {("details", *(row[index] for index in (0, 1, 8, 11)))}
    identifiers = [value for value in row[26:] if isinstance(value, str)
                   and re.match(r"^\d{4}-", value)]
    if identifiers:
        keys.add(("id", identifiers[0]))
    return keys


def _merge_matches(recent, historical):
    """Prefer profile records when the same match also occurs in the archive."""
    seen, merged = set(), []
    for row in recent + historical:
        keys = _match_keys(row)
        if not seen.intersection(keys):
            merged.append(row)
        seen.update(keys)
    return merged


def get_player_matches(player_name):
    """Retrieve a player's singles career as a pandas DataFrame.

    Accept spaced or CamelCase names. Ages use 365.25 days per year, and
    age_difference is player_age minus opponent_age. Invalid rows are omitted
    with a warning. Raise ValueError for unknown names or unusable source data,
    and RuntimeError for network failures. This function accesses the network.
    """
    player = _lookup_player(player_name)
    page = _profile_page(player)
    recent = _parse_match_rows(page, "matchmx")
    rows = _merge_matches(recent, _archive_rows(player))
    data = _clean_matches("var morematchmx = " + json.dumps(rows), _player_birth_date(page))
    if data.empty:
        raise ValueError(f"No usable singles matches were found for {player['name']}.")
    data.attrs["player_name"] = player["name"]
    return data
