"""Test plot behavior using in-memory data and a noninteractive backend."""

from io import BytesIO

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.colors import to_rgba
import pandas as pd
import pytest

from tennis_career.plotting import plot_age_difference


@pytest.fixture(autouse=True)
def close_figures():
    yield
    plt.close("all")


@pytest.fixture
def matches():
    frame = pd.DataFrame({"player_age": [18.5, 22.0, 30.25],
                          "age_difference": [-5.0, 0.0, 7.5],
                          "result": ["W", "L", "W"]})
    frame.attrs["player_name"] = "Example Player"
    return frame


def test_returns_axes_with_correct_points_and_colors(matches):
    axes = plot_age_difference(matches)
    assert isinstance(axes, Axes)
    wins, losses = axes.collections
    assert wins.get_offsets().tolist() == [[18.5, -5.0], [30.25, 7.5]]
    assert losses.get_offsets().tolist() == [[22.0, 0.0]]
    assert wins.get_facecolors()[0] == pytest.approx(to_rgba("#4acbed", alpha=0.85))
    assert losses.get_facecolors()[0] == pytest.approx(to_rgba("#953a8c", alpha=0.85))
    assert sum(len(collection.get_offsets()) for collection in axes.collections) == len(matches)


def test_labels_axes_player_and_results(matches):
    axes = plot_age_difference(matches)
    assert axes.get_xlabel() == "Player age (years)"
    assert axes.get_ylabel() == "Player age − opponent age (years)"
    assert axes.get_title(loc="left") == "Example Player: career matches"
    assert [text.get_text() for text in axes.get_legend().get_texts()] == ["Won", "Lost"]
    assert any(text.get_text() == "Source: Tennis Abstract" for text in axes.figure.texts)


def test_draws_zero_line_and_uses_white_background(matches):
    axes = plot_age_difference(matches)
    assert any(list(line.get_ydata()) == [0, 0] for line in axes.lines)
    assert axes.get_facecolor() == to_rgba("white")
    assert axes.figure.get_facecolor() == to_rgba("white")
    assert not any(spine.get_visible() for spine in axes.spines.values())


def test_uses_generic_title_without_player_metadata(matches):
    matches.attrs.clear()
    assert plot_age_difference(matches).get_title(loc="left") == "Career matches"


def test_does_not_modify_input_data_or_metadata(matches):
    original = matches.copy(deep=True)
    plot_age_difference(matches)
    pd.testing.assert_frame_equal(matches, original)
    assert matches.attrs == original.attrs


def test_saves_a_nonempty_png_without_showing_a_window(matches, monkeypatch):
    def unexpected_show(*args, **kwargs):
        pytest.fail("Plotting should return axes without calling show().")
    monkeypatch.setattr(plt, "show", unexpected_show)
    axes = plot_age_difference(matches)
    buffer = BytesIO()
    axes.figure.savefig(buffer, format="png")
    assert buffer.getvalue().startswith(b"\x89PNG\r\n\x1a\n")
    assert len(buffer.getvalue()) > 1000


@pytest.mark.parametrize("result, label", [("W", "Won"), ("L", "Lost")])
def test_handles_a_single_match_and_result_category(matches, result, label):
    single = matches.loc[matches["result"] == result].iloc[:1]
    axes = plot_age_difference(single)
    assert len(axes.collections) == 1
    assert len(axes.collections[0].get_offsets()) == 1
    assert [text.get_text() for text in axes.get_legend().get_texts()] == [label]


@pytest.mark.parametrize("value", [None, [], {"player_age": [20]}, "matches"])
def test_rejects_non_dataframe_inputs(value):
    with pytest.raises(TypeError, match="must be a pandas DataFrame"):
        plot_age_difference(value)


@pytest.mark.parametrize("column", ["player_age", "age_difference", "result"])
def test_reports_missing_columns(matches, column):
    with pytest.raises(ValueError, match=f"Missing plot columns: {column}"):
        plot_age_difference(matches.drop(columns=column))


def test_rejects_empty_data_without_creating_a_figure(matches):
    before = plt.get_fignums()
    with pytest.raises(ValueError, match="empty match dataframe"):
        plot_age_difference(matches.iloc[:0])
    assert plt.get_fignums() == before


@pytest.mark.parametrize("column", ["player_age", "age_difference"])
@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf"), "twenty", None])
def test_rejects_invalid_coordinates(matches, column, value):
    matches[column] = [value] * len(matches)
    with pytest.raises(ValueError, match=f"{column!r} must contain finite numbers"):
        plot_age_difference(matches)


@pytest.mark.parametrize("result", ["", "win", "D", None])
def test_rejects_unknown_results(matches, result):
    matches["result"] = result
    with pytest.raises(ValueError, match="Match results must be 'W' or 'L'"):
        plot_age_difference(matches)
