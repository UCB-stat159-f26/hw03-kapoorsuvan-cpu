"""Normalize player names and read Tennis Abstract player metadata."""

import re
import unicodedata
from urllib.parse import parse_qs, urlsplit


def _name_key(name):
    """Compare names without differences in case, accents, or separators."""
    replacements = str.maketrans({"đ": "dj", "ł": "l", "ø": "o", "æ": "ae",
                                 "œ": "oe", "ı": "i"})
    folded = unicodedata.normalize("NFKD", name.casefold().translate(replacements))
    return "".join(letter for letter in folded if letter.isalnum())


def _search_query(player_name):
    """Convert spaced or CamelCase names into a player-search query."""
    if not isinstance(player_name, str):
        raise TypeError("Player name must be a string.")
    if not player_name.strip() or not any(letter.isalpha() for letter in player_name):
        raise ValueError("Provide a player's name, such as 'Serena Williams'.")
    spaced = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", player_name.strip())
    return " ".join(spaced.split())


def _player_slug(player):
    """Read a safe player identifier from either supported profile URL format."""
    url = urlsplit(player.get("url", ""))
    identifiers = parse_qs(url.query).get("p", [])
    slug = identifiers[0].rsplit("/", 1)[-1] if identifiers else ""
    if url.hostname not in {"tennisabstract.com", "www.tennisabstract.com"}:
        raise ValueError("Player search returned an unexpected profile URL.")
    if not re.fullmatch(r"[A-Za-z0-9_-]+", slug):
        raise ValueError("Player search returned an invalid player identifier.")
    return slug


def _player_metadata(player):
    """Keep the display name, canonical identifier, and tour from a result."""
    tour = player.get("tour")
    if tour not in {"W", "M"}:
        raise ValueError("Player search returned an unrecognized tour.")
    return {"name": player["name"], "slug": _player_slug(player), "tour": tour}


def _select_player(results, player_name):
    """Require one exact normalized name instead of choosing a partial match."""
    if not isinstance(results, list):
        raise ValueError("Player search returned an invalid results list.")
    matches = [item for item in results if isinstance(item, dict)
               and isinstance(item.get("name"), str)
               and _name_key(item["name"]) == _name_key(player_name)]
    if not matches:
        raise ValueError(f"No Tennis Abstract player found for {player_name!r}.")
    if len(matches) > 1:
        raise ValueError(f"Multiple players match {player_name!r}; provide a more specific name.")
    return _player_metadata(matches[0])


def _player_birth_date(page):
    """Extract the YYYYMMDD birth date embedded in a player profile."""
    match = re.search(r"\bvar\s+dob\s*=\s*[\"']?(\d{8})[\"']?\s*;", page)
    if match is None:
        raise ValueError("The Tennis Abstract profile has no player birth date.")
    return match.group(1)
