from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Generator, List, Optional
import warnings

from decimal import Decimal
from pint import UnitRegistry, UndefinedUnitError

import re
import shlex

import csv
from itertools import zip_longest
from textwrap import shorten

from .exceptions import *

class SVUVParser:
    # Parsing class-constants
    IGNORE_LITERAL = "~"
    COMMAND_LITERAL = "!"
    DEFAULT_SEPARATORS = {" ", "\t", "\r", "\v", "\f", "\u00A0", ","}

    # Printing class-constants
    MAX_COL = 14  # max visual width
    MAX_ROWS = 10  # truncate for huge tables

    _NUMERIC_RE = re.compile(
        r"""
        ^[+-]?(
            (?:\d{1,3}(?:,\d{3})+) |   # e.g. 12,345  or 1,234,567
            (?:\d+)                    # or no commas at all
        )
        (?:\.\d*)?                    # optional fractional part
        (?:[eE][+-]?\d+)?             # optional exponent
        $""",
        re.VERBOSE,
    )
    _ureg = UnitRegistry(autoconvert_offset_to_baseunit=True)

    # ------------------------------------------------------------------ #
    # CONSTRUCTION
    # ------------------------------------------------------------------ #
    def __init__(self, dataset_dir: str | Path):
        root = Path(dataset_dir).resolve()
        if not root.is_dir():
            raise NotADirectoryError(f"Dataset root '{root}' is not a directory")

        self._dirs: Dict[str, Path] = {
            "root": root,
            "data": root / "data",
            "validation": root / "validation",
        }
        if not self._dirs["data"].is_dir():
            raise FileNotFoundError("missing ‘data/’ folder")
        if not self._dirs["validation"].is_dir():
            raise FileNotFoundError("missing ‘validation/’ folder")

        self.reset()  # allocate mutable members

    # ------------------------------------------------------------------ #
    # PUBLIC HELPERS
    # ------------------------------------------------------------------ #
    @staticmethod
    def infer_uncertainty(
        value: float,
        prev: Optional[float] = None,
        next_: Optional[float] = None,
    ) -> float:
        """Hybrid rule-of-thumb uncertainty (least-significant digit OR neighbour gap)."""
        dval = Decimal(str(value)).normalize()

        # LSD-based part
        exp = -dval.as_tuple().exponent
        lsd_unc = 0.5 * 10 ** (-exp)

        # Neighbour-based part
        gaps = []
        if prev is not None:
            gaps.append(abs(value - prev))
        if next_ is not None:
            gaps.append(abs(next_ - value))
        neigh_unc = 0.5 * (sum(gaps) / len(gaps)) if gaps else 0.0

        return max(lsd_unc, neigh_unc)

    def read(self, file: str | Path) -> Dict[str, List[Any]]:
        """Parse a single .svuv file and return the full data dict."""
        self.reset()
        self._file = Path(file).resolve()

        with self._file.open(encoding="utf-8") as fp:
            self._fp = fp

            # core header rows ------------------------------------------------
            self._set_headers(self._split(self._next_line()))
            self._vars = self._header_map(self._split(self._next_line()))
            self._units = self._header_map(self._split(self._next_line()))

            # main parse loop -------------------------------------------------
            for row in self._row_iter():
                mapped = self._header_map(row)
                self._push_row(mapped)

        # post-process inferred uncertainties
        self._finalise_uncertainties()
        return self._data

    # ------------------------------------------------------------------ #
    # USER INTERFACE
    # ------------------------------------------------------------------ #
    def to_csv(self, path: str | Path, *, include_uncert=True) -> None:
        """
        Write the parsed table to ``path`` using the built-in csv module.

        Parameters
        ----------
        path : str | Path
            Output file name.
        include_uncert : bool, default True
            If *False* drop the ``$uncertainty`` columns.
        """
        # Pick the order used during parsing
        heads = [h for h in self._headers if h != self.IGNORE_LITERAL]

        # Optionally prune uncertainty columns
        if include_uncert:
            heads += [f"{h}$uncertainty" for h in heads]
        rows = zip_longest(*(self._data[h] for h in heads), fillvalue="")

        with open(str(path), "w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(heads)
            writer.writerows(rows)

    def __str__(self) -> str:
        """
        Human-readable preview —  first 10 data rows + column widths capped
        so `print(parser)` doesn’t flood the console.
        """

        heads = [h for h in self._headers if h != self.IGNORE_LITERAL]
        preview = heads.copy()  # header row

        # Build a 2-D list: header + up to MAX_ROWS of data
        for idx in range(min(len(self._data[heads[0]]), SVUVParser.MAX_ROWS)):
            preview.extend(self._data[h][idx] for h in heads)

        # column-wise max width (honouring cap)
        col_w = {
            h: min(SVUVParser.MAX_COL, max(len(str(h)), *(len(str(v)) for v in self._data[h][:SVUVParser.MAX_ROWS])))
            for h in heads
        }

        def _fmt(col, val):
            return shorten(str(val), width=col_w[col], placeholder="…").ljust(col_w[col])

        # Header line
        lines = [" | ".join(_fmt(h, h) for h in heads),
                 "-+-".join("-" * col_w[h] for h in heads)]

        # Data lines
        for i in range(min(len(self._data[heads[0]]), SVUVParser.MAX_ROWS)):
            lines.append(" | ".join(_fmt(h, self._data[h][i]) for h in heads))

        if len(self._data[heads[0]]) > SVUVParser.MAX_ROWS:
            lines.append(f"... ({len(self._data[heads[0]]) - SVUVParser.MAX_ROWS} more rows)")

        return "\n".join(lines)

    # ------------------------------------------------------------------ #
    # INTERNAL STATE MANAGEMENT
    # ------------------------------------------------------------------ #
    def reset(self) -> None:
        self._separators = set(self.DEFAULT_SEPARATORS)
        self._headers: List[str] = []
        self._vars: Dict[str, str] = {}
        self._units: Dict[str, str] = {}
        self._si_unit: dict[str, str] = {}
        self._uncertainty: Dict[str, Optional[float]] = {}

        self._data: Dict[str, List[Any]] = {"$citation": []}
        self._citation = "UNKNOWN"

        self._file: Optional[Path] = None
        self._fp = None  # type: ignore[assignment]

    # ------------------------------------------------------------------ #
    # PARSING HELPERS
    # ------------------------------------------------------------------ #

    #  Header handling ---------------------------------------------------
    def _set_headers(self, headers: List[str]) -> None:
        if any(not self._valid_header(h) for h in headers):
            raise ParseError(f"Invalid header names in {self._file}")

        # Re-definition checks (after !set-heading)
        if self._headers:
            old = {h for h in self._headers if h != self.IGNORE_LITERAL}
            new = {h for h in headers if h != self.IGNORE_LITERAL}
            if old != new:
                missing = sorted(old - new)
                raise ParseError(f"!set-header is missing a header: {missing} in {self._file}")

        # reset column storage
        for h in headers:
            if h != self.IGNORE_LITERAL:
                self._data.setdefault(h, [])
                self._data.setdefault(f"{h}$uncertainty", [])

        self._headers = headers

    #  Line splitting ----------------------------------------------------
    def _split(self, line: str) -> List[str]:
        """Split a line using current separator set (regex for speed)."""
        if not line:
            return []

        # Build / cache compiled regex per separator set size
        sep_pattern = "[" + re.escape("".join(sorted(self._separators))) + "]+"
        return [tok for tok in re.split(sep_pattern, self._strip(line))]

    #  Command / data iterator ------------------------------------------
    def _row_iter(self) -> Generator[List[str], None, None]:
        while True:
            raw = self._next_line()
            if raw is None:
                break

            if raw.startswith(self.COMMAND_LITERAL):
                self._handle_command(raw)
            else:
                tokens = self._split(raw)
                if tokens and any(tokens):  # ignore accidental blank lines
                    yield tokens

    #  Command dispatcher -----------------------------------------------
    def _handle_command(self, raw: str) -> None:
        cmd, *args = shlex.split(raw)
        match cmd:
            case "!set-heading":
                self._set_headers(self._split(self._next_line()))

            case "!set-units":
                self._units.update(self._header_map(self._split(self._next_line())))

            case "!set-uncertainty":
                unc_list = self._split(self._next_line())
                cleaned = [
                    None if t == self.IGNORE_LITERAL else float(t)
                    for t in unc_list
                ]
                self._uncertainty = self._header_map(cleaned)

            case "!ignore-separator":
                if len(args) != 1:
                    raise CommandError(f"!ignore-separator takes exactly one argument, received {len(args)} in {self._file}.")
                if args[0] not in self._separators: warnings.warn(f"Tried to ignore separator '{args[0]}' in {self._file}, even though it is not actually in the separators list.", SeparatorWarning)
                self._separators.discard(args[0])

            case "!add-separator":
                if len(args) != 1:
                    raise CommandError("!add-separator takes exactly one argument, received {len(args)} in {self._file}.")
                if args[0] in self._separators: warnings.warn(f"Tried to add separator '{args[0]}' in {self._file}, even though it is already in the separators list.", SeparatorWarning)
                self._separators.add(args[0])

            case "!cite":
                if len(args) != 1:
                    raise CommandError("!cite needs a single argument")
                self._citation = args[0]

            case _:
                raise CommandError(f"Unknown command '{cmd}' in {self._file}")

    # core row handler ---------------------------------------------
    def _push_row(self, mapped: dict[str, str]) -> None:  # noqa: N802
        """Add a parsed data row to self._data, converting to SI base units."""

        # citation bookkeeping
        if self._citation == "UNKNOWN":
            warnings.warn(
                f"No '!cite' before data row in {self._file}; using 'UNKNOWN'.",
                MissingCitationWarning,
            )
        self._data["$citation"].append(self._citation)

        # iterate over every numeric cell in the row
        for head, text in mapped.items():
            raw_val = self._numeric(text)  # float as typed
            raw_unit = self._units[head]

            si_val, si_unit = self._to_si(raw_val, raw_unit)
            self._data[head].append(si_val)

            # remember unit once
            self._si_unit.setdefault(head, si_unit)

            # --- uncertainty -------------------------------------------------
            u_key = f"{head}$uncertainty"
            u_raw = self._uncertainty.get(head)  # may be None

            if u_raw is None:
                self._data[u_key].append(None)  # inferred later
            else:
                si_unc = self._to_si_unc(u_raw, raw_unit)
                self._data[u_key].append(si_unc)

    def _finalise_uncertainties(self) -> None:
        """Fill in any None entries with inferred values."""
        for head in self._headers:
            if head == self.IGNORE_LITERAL:
                continue
            u_key = f"{head}$uncertainty"
            col = self._data[head]
            ucol = self._data[u_key]

            for idx, val in enumerate(ucol):
                if val is None:
                    prev_v = col[idx - 1] if idx else None
                    next_v = col[idx + 1] if idx + 1 < len(col) else None
                    ucol[idx] = self.infer_uncertainty(col[idx], prev_v, next_v)

    # ------------------------------------------------------------------ #
    # LOW-LEVEL UTILITIES
    # ------------------------------------------------------------------ #

    def _numeric(self, token: str) -> float:
        """Validate & convert numeric token."""
        if not self._NUMERIC_RE.match(token):
            raise ParseError(f"Invalid numeric token '{token}' in {self._file}")
        return float(token.replace(',', ''))

    def _to_si(self, value: float, unit: str) -> tuple[float, str]:
        """
        Return (magnitude, canonical_unit_string) of `value * unit`
        converted to SI base units.  Raises UnknownUnitError if `unit`
        is not known to pint.
        """
        try:
            q_si = (value * self._ureg(unit)).to_base_units()
        except UndefinedUnitError as exc:
            raise UnknownUnitError(f"Unknown unit “{unit}” in {self._file}") from exc
        return q_si.magnitude, str(q_si.units)

    def _to_si_unc(self, unc: float, unit: str) -> float:
        """
        Convert an *absolute* uncertainty to SI base units **ignoring offsets**.
        If the original unit is affine (degC, degF, …) we use the matching
        delta-unit (`delta_degC`), otherwise we just forward to `_to_si`.
        """
        delta_unit = f"delta_{unit}" if f"delta_{unit}" in self._ureg else unit
        return (unc * self._ureg(delta_unit)).to_base_units().magnitude

    def _header_map(self, row: List[Any]) -> Dict[str, Any]:
        if len(row) != len(self._headers):
            raise ParseError(f"Header/data length mismatch with row content, {row}, in file, {self._file}")
        return {
            h: v for h, v in zip(self._headers, row) if h != self.IGNORE_LITERAL
        }

    def _next_line(self) -> Optional[str]:
        """Return next non-blank, non-comment line (raw)."""
        for raw in self._fp:  # type: ignore[attr-defined]
            stripped = self._strip(raw)
            if stripped:
                return stripped
        return None

    @staticmethod
    def _strip(line: str) -> str:
        """Remove inline # comments and surrounding whitespace."""
        return line.split("#", 1)[0].strip()

    @staticmethod
    def _valid_header(hdr: str) -> bool:
        return hdr == SVUVParser.IGNORE_LITERAL or bool(
            re.fullmatch(r"[a-z_]+", hdr)
        )