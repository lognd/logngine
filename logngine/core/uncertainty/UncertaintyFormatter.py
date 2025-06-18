from enum import IntEnum, auto
from dataclasses import dataclass
from typing import Callable

import numpy as np

from .NormalDistribution import NormalDistribution

def _get_machine_epsilon() -> float:
    _eps = 1.0
    while 1.0 + _eps > 1:
        _eps /= 2.0
    return _eps
def _get_most_significant_digit(x_: float):
    return int(np.floor(np.log10(x_)))
def _get_machine_precision() -> int:
    _eps = _get_machine_epsilon()
    return _get_most_significant_digit(_eps)
def _round_from_back(x_: float, digits: int = 2):
    eps_digits = _get_most_significant_digit(x_)
    return round(x_, eps_digits + _get_machine_precision() - digits)
def _get_first_digit(num: float):
    return _round_from_back(num) // 10**_get_most_significant_digit(num)

class UncertaintyFormatter:

    ENGINEERING_PRECISION: int = 3
    SCIENTIFIC_TWO_SF_REPORTING_THRESHOLD: float = 0.02

    class Nomenclature(IntEnum):
        ENGINEERING = auto()
        SCIENTIFIC = auto()

    class OutputFormat(IntEnum):
        ENGINEERING = auto()
        PLAINTEXT = auto()
        LATEX = auto()

    def __init__(self):
        self.__vec_repr: Callable[[list[str]], str] = None
        self.__fp_repr: Callable[[float, int], str] = None
        self.format: Callable[[float, float], str] = None
        self.set_format()

    def set_format(self,
                   nomenclature: Nomenclature = Nomenclature.SCIENTIFIC,
                   output_format: OutputFormat = OutputFormat.PLAINTEXT):
        match output_format:
            case UncertaintyFormatter.OutputFormat.ENGINEERING:
                self.__fp_repr = UncertaintyFormatter._convert_to_engineering_float_format
                self.__vec_repr = UncertaintyFormatter._convert_to_plaintext_vector_string_format
            case UncertaintyFormatter.OutputFormat.PLAINTEXT:
                self.__fp_repr = UncertaintyFormatter._convert_to_plaintext_float_format
                self.__vec_repr = UncertaintyFormatter._convert_to_plaintext_vector_string_format
            case UncertaintyFormatter.OutputFormat.LATEX:
                self.__fp_repr = UncertaintyFormatter._convert_to_latex_float_format
                self.__vec_repr = UncertaintyFormatter._convert_to_latex_vector_string_format

        match nomenclature:
            case UncertaintyFormatter.Nomenclature.SCIENTIFIC:
                self.format = self._format_scientific
            case UncertaintyFormatter.Nomenclature.ENGINEERING:
                self.format = self._format_engineering

    def _format_scientific(self, value: float, uncert: float):
        pass
    def _format_engineering(self, value: float, uncert: float):
        pass

    def _convert_single_to_engineering_precision(self, value: float, uncert: float = 0.0) -> str:
        # bug with value == 0.0
        most_sig_dig: int = UncertaintyFormatter.ENGINEERING_PRECISION - _get_most_significant_digit(value)
        if _get_first_digit(value) == 1.0: most_sig_dig += 1

        min_tolerance = 10**-most_sig_dig
        if uncert <= min_tolerance:  # basically exact value; uncertainty in the value is less than our tolerance anyway
            if 0.001 < value < 10_000:
                return f"{value:.{most_sig_dig}f}"
            mantissa, _, exp, _ = self._get_scientific_format(value, uncert)
            return f"{self.__fp_repr(mantissa, exp)}"
        return self._convert_single_to_scientific_precision(value, uncert)
    def _convert_single_to_scientific_precision(self, value: float, uncert: float = 0.0) -> str:
        # Handle when value == 0.0.
        if 0.001 < abs(value) < 10_000:
            pass
        mantissa, u_mantissa, exp, round_len = self._get_scientific_format(value, uncert)

    @staticmethod
    def _get_scientific_format(value: float, uncert: float) -> tuple[float, float, int, int]:
        n_digits: int = _get_first_digit(uncert)

        exp = -n_digits
        value /= 10**exp
        uncert /= 10**exp

        if uncert / value <= UncertaintyFormatter.SCIENTIFIC_TWO_SF_REPORTING_THRESHOLD:
            n_digits -= 1
        return value, uncert, exp, -n_digits

    # Float formats
    @staticmethod
    def _convert_to_engineering_float_format(value: str, exponent: int = 0) -> str:
        if exponent == 0:
            return value
        return f"{value}E{exponent}"
    @staticmethod
    def _convert_to_plaintext_float_format(value: str, exponent: int = 0) -> str:
        if exponent == 0:
            return value
        return f"{value} * 10^{exponent}"
    @staticmethod
    def _convert_to_latex_float_format(value: str, exponent: int = 0) -> str:
        if exponent == 0:
            return value
        return f"{value} \\times 10^{{{exponent}}}"

    # Vector formats
    @staticmethod
    def _convert_to_latex_vector_string_format(strings: list[str]) -> str:
        return "\\begin{bmatrix}\n    " + " \\ \n    ".join(strings) + "\n\\end{bmatrix}"
    @staticmethod
    def _convert_to_plaintext_vector_string_format(strings: list[str]) -> str:
        if len(strings) == 1: return strings[0]
        entry_length = max(len(string) for string in strings)
        aligned = ['[' if i_ == 0 else ' ' + ' ' + string + ' ' * (entry_length - len(string) + 1) + ',' for i_, string in enumerate(strings)]
        # Formatted like:
        #     [ {} ,
        #       {} ,
        #       {} ,
        #       {} ]
        return '\n'.join(aligned)[:-1] + ']'
