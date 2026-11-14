Suvan Kapoor

# Tennis career plots

This is my Python package for [STAT 159 HW3](https://stat159.berkeley.edu/fall-2026/hws/hw03/hw03.html). It gets a player's singles matches from Tennis Abstract and plots their age against the difference between their age and their opponent's age. Wins are cyan and losses are purple, following the NYT chart from HW1 and HW2, without the point annotations.

## Installation

Use Python 3.10 or newer and Git. From a terminal:

```bash
python -m pip install "git+https://github.com/UCB-stat159-f26/hw03-kapoorsuvan-cpu.git"
```

The package installs pandas, Matplotlib, and requests. If the repository is private, Git needs to be signed into a GitHub account that can access it.

## Examples

```python
import matplotlib.pyplot as plt
from tennis_career import get_player_matches, plot_age_difference

serena = get_player_matches("serena williams")
serena_plot = plot_age_difference(serena)
serena_plot.figure.savefig("serena_age_difference.png", dpi=200, bbox_inches="tight")
plt.show()

rafa = get_player_matches("Rafael Nadal")
plot_age_difference(rafa)
plt.show()
```

`"Serena Williams"` and `"SerenaWilliams"` also work. Use a full name so the search can find an exact match. An unknown player gives an error:

```python
try:
    get_player_matches("GastonSanchez")
except ValueError as error:
    print(error)
# No Tennis Abstract player found for 'GastonSanchez'.
```

Downloading matches requires an internet connection. Plotting an existing dataframe does not. To save figures on a machine without a display, set `MPLBACKEND=Agg` before running Python.

## The two functions

`get_player_matches(player_name)` returns a pandas dataframe sorted by date. It searches Tennis Abstract, reads the player's birth date, and combines the profile's singles results with the career archive. Overlapping matches are checked using their source IDs or their date, tournament, round, and opponent. The profile record takes priority when there is a duplicate.

`plot_age_difference(matches)` returns a Matplotlib `Axes`. The horizontal axis is player age. The vertical axis is `player_age - opponent_age`, so a positive value means the player was older. The function leaves the dataframe unchanged. Use `plt.show()` to display the plot or `axes.figure.savefig(...)` to save it.

Unknown names and unusable data raise `ValueError`. Invalid input types can raise `TypeError`. HTTP errors and connection failures raise `RuntimeError`, with a 30-second timeout on each request. If a career archive returns 404, the package warns and uses the profile's matches; that result may be incomplete.

## Data and age calculations

| Column | Meaning |
| --- | --- |
| `date` | Date recorded by Tennis Abstract, parsed as a pandas datetime |
| `tournament` | Event name |
| `surface` | Court surface |
| `result` | `W` for a win or `L` for a loss |
| `round` | Tournament round |
| `score` | Score text from the source |
| `opponent` | Opponent's name |
| `player_age` | Player's age in decimal years |
| `opponent_age` | Opponent's age in decimal years |
| `age_difference` | Player's age minus opponent's age |

The player's display name is stored in `dataframe.attrs["player_name"]` and used for the plot title.

In the assignment's female career format, the opponent field contains a birth date such as `19770119`. In the male career format, it contains a decimal age such as `22.264202601`. The cleaner checks the value itself, since newer profile data can also contain opponents' birth dates for men.

For birth dates, age is the number of days between the recorded match date and birth date, divided by 365.25. Supplied decimal ages are kept as given. This uses the dates in the source; some records use a tournament's starting date, so these ages are approximate.

Rows with invalid dates, missing or nonfinite ages, ages outside 0 to 120, or results other than `W` and `L` are omitted with a warning. The package keeps the source's W/L records without applying an extra score-based filter for retirements or walkovers. It parses the match arrays as JSON-compatible data and does not execute the downloaded JavaScript.

Tennis Abstract can update its records or change its page format. A new download can therefore differ from an earlier one. The plot uses the available career data and is not restricted to the NYT article's August 2022 cutoff.

## Running the tests

From a local clone of this repository:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[test]"
python -m pytest -q
```

On Windows, activate the environment with `.venv\Scripts\activate` instead. The test suite has 174 cases covering parsing, age calculations, name matching, retrieval errors, and plotting. Retrieval tests use mocked HTTP responses. An automatic fixture blocks DNS lookups and socket connections during tests, and Matplotlib uses the noninteractive Agg backend.

Live retrieval checks are separate from the automated tests. The package was also checked by building a wheel and installing from GitHub. These checks matter because passing tests inside the source directory alone would not show whether someone else could install the package.

## Repository layout

```text
pyproject.toml                 Package metadata and dependencies
src/tennis_career/
    __init__.py                The two public imports
    _parsing.py                JavaScript match-array parsing
    _players.py                Name matching and profile metadata
    _cleaning.py               Dataframe preparation and age calculations
    data.py                    Downloads and duplicate removal
    plotting.py                Scatter plot
tests/
    conftest.py                Offline test guard and plotting backend
    test_*.py                  Tests for each part of the package
instructions.md               Assignment instructions supplied in the repository
README.md                     Setup, usage, and reflections
```

Dependencies are in `pyproject.toml`. HW3 does not require a Makefile or an `environment.yml`.

## Reflections

My main takeaway is to check what a column actually contains before doing calculations with it. The opponent field is a good example. A birth date and a decimal age can sit in the same position in two files, but they need different handling. Just treating both as numbers would give a very wrong plot.

The offline tests also make sense to me here. A broken internet connection should not stop a check of the age calculation. Small sample rows make the expected answer easier to check, and the separate live checks cover whether the website still works with the download code.

I asked for small commits and a pause after each push. That made each change a manageable thing to approve. There are quite a few commits, but it is possible to follow the package from the first configuration file through the tests and the public functions. I used Codex to help with implementation and testing, and the Humanizer skill to edit this README.
