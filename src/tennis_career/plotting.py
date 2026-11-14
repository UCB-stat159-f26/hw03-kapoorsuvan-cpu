"""Plot singles results against player age and opponent age difference."""

import math

import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
import pandas as pd


_RESULT_STYLES = {"W": ("#4acbed", "Won"), "L": ("#953a8c", "Lost")}
_PLOT_COLUMNS = {"player_age", "age_difference", "result"}


def _validate_plot_frame(matches):
    """Require a nonempty dataframe with the columns used by the plot."""
    if not isinstance(matches, pd.DataFrame):
        raise TypeError("Matches must be a pandas DataFrame from get_player_matches().")
    missing = _PLOT_COLUMNS.difference(matches.columns)
    if missing:
        raise ValueError(f"Missing plot columns: {', '.join(sorted(missing))}.")
    if matches.empty:
        raise ValueError("Cannot plot an empty match dataframe.")
    _validate_plot_values(matches)


def _validate_plot_values(matches):
    """Reject missing, nonnumeric, or infinite coordinates and unknown results."""
    for column in ("player_age", "age_difference"):
        values = matches[column]
        if not pd.api.types.is_numeric_dtype(values) or values.isna().any():
            raise ValueError(f"Plot column {column!r} must contain finite numbers.")
        if not values.map(math.isfinite).all():
            raise ValueError(f"Plot column {column!r} must contain finite numbers.")
    if not matches["result"].isin(_RESULT_STYLES).all():
        raise ValueError("Match results must be 'W' or 'L'.")


def _draw_results(axes, matches):
    """Draw wins first so losses remain visible when points overlap."""
    for result, (color, label) in _RESULT_STYLES.items():
        subset = matches.loc[matches["result"] == result]
        if not subset.empty:
            axes.scatter(subset["player_age"], subset["age_difference"],
                         color=color, label=label, s=22, alpha=0.85, edgecolors="none")


def _style_axes(axes):
    """Use the reference chart's white background, light grid, and zero line."""
    axes.set_facecolor("white")
    axes.set_axisbelow(True)
    axes.grid(color="#e6e6e6", linewidth=0.8)
    axes.axhline(0, color="#888888", linewidth=1, zorder=1)
    for spine in axes.spines.values():
        spine.set_visible(False)
    axes.tick_params(axis="both", length=0, pad=8, colors="#444444")
    axes.xaxis.set_major_locator(MaxNLocator(integer=True))


def _label_axes(axes, matches):
    """Label coordinates in years and identify the player when available."""
    player = matches.attrs.get("player_name")
    axes.set_title(f"{player}: career matches" if player else "Career matches",
                   loc="left", fontsize=17, pad=42)
    axes.set_xlabel("Player age (years)", labelpad=12)
    axes.set_ylabel("Player age − opponent age (years)", labelpad=12)
    axes.legend(loc="lower left", bbox_to_anchor=(0, 1.01), ncol=2,
                frameon=False, borderaxespad=0, handletextpad=0.4)


def plot_age_difference(matches):
    """Return a Matplotlib Axes showing each match, colored by win or loss.

    Use the dataframe returned by get_player_matches(). Positive differences
    mean the player was older than the opponent. Call plt.show() to display
    the figure, or use the returned axes.figure.savefig() to save it.
    This function does not change the input dataframe or access the network.
    """
    _validate_plot_frame(matches)
    figure, axes = plt.subplots(figsize=(11, 6.5), facecolor="white")
    figure.subplots_adjust(left=0.11, right=0.98, bottom=0.16, top=0.82)
    _draw_results(axes, matches)
    _style_axes(axes)
    _label_axes(axes, matches)
    figure.text(0.11, 0.035, "Source: Tennis Abstract", fontsize=9, color="#666666")
    return axes
