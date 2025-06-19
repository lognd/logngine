"""
pytest for SVUVParser against water/saturation-table.svuv
------------------------------------------------------------------
Assumes the repo layout:

project_root/
├─ tools/SVUVParser.py
├─ datasets/data/fluids/water/saturation-table.svuv
└─ tests/test_svuv_parser.py   ← (this file)

Run with:  pytest -v
"""

from pathlib import Path
import importlib.util

# --- locate and import parser from tools/ ------------------------------------
ROOT = Path(__file__).resolve().parents[1]          # project root
TOOLS_DIR = ROOT / "tools"
SPEC = importlib.util.spec_from_file_location(
    "svuv_parser", TOOLS_DIR / "SVUVParser.py"
)
svuv_parser = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(svuv_parser)               # type: ignore[attr-defined]
SVUVParser = svuv_parser.SVUVParser                # noqa: N806

DATA_FILE = ROOT / "datasets" / "data" / "fluids" / "water" / "saturation-table.svuv"


# --------------------------------------------------------------------------- #
def _parse() -> SVUVParser:
    p = SVUVParser(dataset_dir=ROOT / "datasets")
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
    assert abs(temps[0] - 0.01) < 1e-6
    # last numeric entry (row with 373.95 °C)
    assert abs(temps[-1] - 373.95) < 1e-6


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