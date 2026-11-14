"""Retrieve tennis career matches and visualize player age differences."""

from .data import get_player_matches
from .plotting import plot_age_difference

__all__ = ["get_player_matches", "plot_age_difference"]
