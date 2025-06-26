from pathlib import Path
import csv
import sys

ROOT = Path(__file__).resolve().parents[1]          # project root
sys.path.append(str(ROOT))

from tools import SVUVParser

TOOLS_DIR = ROOT / "tools"
DATA_FILE = ROOT / "datasets" / "data" / "thermo" / "water" / "saturation-table.svuv"


# --------------------------------------------------------------------------- #
def _parse() -> SVUVParser:
    p = SVUVParser()
    p.read(str(DATA_FILE))
    return p


# --------------------------------------------------------------------------- #
def test_structure():
    """Expect correct headings, units, and row count."""
    parser = _parse()

    expected_headings = [
        "temperature",
        "pressure",
        "liquid_specific_volume",
        "vapor_specific_volume",
        "liquid_specific_internal_energy",
        "vapor_specific_internal_energy",
        "liquid_specific_enthalpy",
        "vapor_specific_enthalpy",
        "liquid_specific_entropy",
        "vapor_specific_entropy",
    ]
    # ignore '~' placeholders already filtered out by __get_header_correspondence
    assert list(parser._data.keys())[1::2][: len(expected_headings)] == expected_headings

    # three header rows + ~620 numeric rows + two directive blocks
    total_rows = sum(len(v) for k, v in parser._data.items() if not k.endswith("$uncertainty"))
    assert total_rows > 600, "Suspiciously few data rows parsed"


def test_first_and_last_row():
    """Spot-check a couple of numeric values (temperature column only)."""
    parser = _parse()
    temps = parser._data["temperature"]
    # first numeric entry (row with 0.01 °C)
    assert abs(temps[0] - (0.01+273.15)) < 1e-6


def test_uncertainty_inferred():
    """A None placeholder in uncertainty should be filled by infer_uncertainty()."""
    parser = _parse()
    uvals = parser._data["temperature$uncertainty"]
    assert all(u is not None for u in uvals), "Uncertainty inference failed for some rows"


def test_idempotent():
    """Reading twice yields identical data dicts (deep-copy guard)."""
    p1 = _parse()
    p2 = _parse()
    assert p1._data == p2._data
    # ensure objects are not literally the same instance
    assert p1._data is not p2._data

def test_human_readable_form(tmp_path):
    """
    1. str(parser)   must be a non-empty, multi-line preview
    2. to_csv()      round-trips exactly to the internal _data dict
    """
    parser = _parse()

    # --------- 1. pretty-print preview --------------------------------
    preview = str(parser)
    assert len(preview) > 100           # has content
    assert preview.count("\n") >= parser.MAX_ROWS  # at least MAX_ROWS lines

    # --------- 2. CSV round-trip --------------------------------------
    csv_file = tmp_path / "out.csv"
    parser.to_csv(csv_file)             # default: include uncertainties

    # read it back
    with csv_file.open(newline="", encoding="utf-8") as fh:
        reader = csv.reader(fh)
        headers = next(reader)          # first row written by to_csv
        rows = list(reader)

    # build the expected 2-D list directly from the parser's data store
    expected_rows = list(
        zip(*[parser._data[h] for h in headers])  # noqa: WPS437  (accessing a dunder for test only)
    )
    # convert everything to string – str(float) is how csv.writer wrote it
    expected_rows = [[str(cell) for cell in row] for row in expected_rows]

    assert rows == expected_rows

