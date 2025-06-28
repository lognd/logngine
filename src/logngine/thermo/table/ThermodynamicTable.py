from abc import ABC, abstractmethod

import numpy as np
from dataclasses import dataclass, fields
from typing import *
from pydantic import Field
import warnings

try:
    import loguru
    LOGURU_INSTALLED = True
except ImportError:
    warnings.warn("Symbolic Thermosolver is not enabled...")
    LOGURU_INSTALLED = False

class CompressedNotSaturatedMixtureError(Exception): pass
class SuperheatedNotSaturatedMixtureError(Exception): pass
class DegenerateStateError(Exception): pass
class OutOfTableBoundsError(Exception): pass

def info_log(msg: str):
    if LOGURU_INSTALLED: loguru.logger.info(msg)

States = Literal['superheated', 'saturated', 'compressed']
NonUniqueProperty = Literal['pressure', 'temperature']
UniqueProperty = Literal['specific_volume', 'specific_internal_energy', 'specific_enthalpy', 'specific_entropy']
ThermoProperty = Literal[UniqueProperty, NonUniqueProperty]
LerpFloat = Annotated[float, Field(ge=0.0, le=1.0)]

# This serves as an interface for how a table should
# interact, so that I may make a simple implementation
# now and a drop-in optimized implementation later.
# I have an exam coming up that I *really* need this
# library to work, so I'm making the simple implementation
# now, but the simple implementation can also be used
# to check the complex implementation later :)

@dataclass(frozen=True, eq=True, order=True, slots=True)
class ThermoState:
    pressure: float
    temperature: float
    specific_volume: float
    specific_internal_energy: float
    specific_enthalpy: float
    specific_entropy: float

class SaturatedQueryResult(TypedDict):
    quality: float
    vapor_state: ThermoState
    liquid_state: ThermoState

class LerpQuery(TypedDict):
    A: ThermoState
    B: ThermoState
    x: LerpFloat

class Table2DQuery(TypedDict):
    upper_left: Optional[ThermoState]
    upper_right: Optional[ThermoState]
    lower_left: Optional[ThermoState]
    lower_right: Optional[ThermoState]
    vertical_property: ThermoProperty
    horizontal_property: ThermoProperty

class QueryResult(TypedDict):
    type: States
    result: ThermoState
    quality: Optional[float]

MAX_ITER: int = int(1e5)
def _find_root_bisection(f: Callable[[float], float], bracket: tuple[float, float], tol: float = 1e-8) -> float:
    x_l, x_u = bracket
    f_l, f_u = f(x_l), f(x_u)

    assert f_l * f_u < 0, "There is likely not a value bracketed."

    _past_vals = [-float('inf'), float('inf')]
    n_iter: float = 0
    while abs(_past_vals[1] - _past_vals[0]) > tol:
        if n_iter >= MAX_ITER: raise Exception("Too many iterations reached.")
        n_iter += 1
        _past_vals[0] = _past_vals[1]

        x_r = 0.5 * (x_l + x_u)
        f_r = f(x_r)
        _past_vals[1] = f_r

        if f_r * f_l < 0:
            x_u = x_r
            f_u = f_r
        elif f_r * f_u < 0:
            x_l = x_r
            f_l = f_r
        else:
            return x_r
    return 0.5 * (x_l + x_u)



class NaiveThermodynamicTable(ABC):

    def __init__(self, material: str):
        self._material: str = material
        self.get_tables()
        self._lerp_queries: list[LerpQuery] = []

    def get_tables(self, citation_filter: Optional[str] = None):
        self._compressed_table = self.get_compressed_table(citation_filter=citation_filter)
        self._saturated_table = self.get_saturated_table(citation_filter=citation_filter)
        self._superheated_table = self.get_superheated_table(citation_filter=citation_filter)

        self._compressed_headers = self.get_compressed_headers()
        self._saturated_headers = self.get_saturated_headers()
        self._superheated_headers = self.get_superheated_headers()

    @abstractmethod
    def get_saturated_table(self, citation_filter: Optional[str] = None) -> np.ndarray: pass
    @abstractmethod
    def get_saturated_headers(self) -> list[str]: pass
    @abstractmethod
    def get_compressed_table(self, citation_filter: Optional[str] = None) -> np.ndarray: pass
    @abstractmethod
    def get_compressed_headers(self) -> list[str]: pass
    @abstractmethod
    def get_superheated_table(self, citation_filter: Optional[str] = None) -> np.ndarray: pass
    @abstractmethod
    def get_superheated_headers(self) -> list[str]: pass

    @staticmethod
    def _get_row(table: np.ndarray, headers: list[str], row_num: int, formatter: Callable[[str], str] = lambda _str: _str) -> ThermoState:
        entries = {}
        for _f in fields(ThermoState):
            prop_name = _f.name
            table_idx = headers.index(formatter(prop_name))
            entries[prop_name] = table[row_num][table_idx]
        return ThermoState(**entries)

    _saturated_vapor_formatter: Callable[[str], str] = lambda _str: "vapor_{}".format(_str) if _str not in ('pressure', 'temperature') else _str
    _saturated_liquid_formatter: Callable[[str], str] = lambda _str: "liquid_{}".format(_str) if _str not in ('pressure', 'temperature') else _str
    def _get_saturated_row(self, row_num: int) -> tuple[ThermoState, ThermoState]:
        return (
            self._get_row(table=self._saturated_table, headers=self._saturated_headers, row_num=row_num, formatter=self._saturated_vapor_formatter),
            self._get_row(table=self._saturated_table, headers=self._saturated_headers, row_num=row_num, formatter=self._saturated_liquid_formatter)
        )
    def _get_compressed_row(self, row_num) -> ThermoState:
        return self._get_row(table=self._compressed_table, headers=self._compressed_headers, row_num=row_num)
    def _get_superheated_row(self, row_num) -> ThermoState:
        return self._get_row(table=self._superheated_table, headers=self._superheated_headers, row_num=row_num)

    def _lerp(self, x: LerpFloat, A: ThermoState, B: ThermoState) -> ThermoState:
        self._lerp_queries.append(LerpQuery(A=A, B=B, x=x))
        if len(self._lerp_queries) > 4: self._lerp_queries.pop(0)

        entries = {}
        for _f in fields(ThermoState):
            prop_name = _f.name
            entries[prop_name] = x * getattr(A, prop_name) + (1.0 - x) * getattr(B, prop_name)
        return ThermoState(**entries)

    @staticmethod
    def _get_bounds(table: np.ndarray, headers: list[str], property: str) -> tuple[float, float]:
        col_idx = headers.index(property)
        col = table[:, col_idx]
        return float(np.min(col)), float(np.max(col))

    def _log_recent_lerps(self, count: int = 3):
        count = min(count, len(self._lerp_queries))

        info_log("Lerp History: ")
        for query in self._lerp_queries[-count:]:
            info_log(f"x: {query['x']}; A: {query['A']}; B: {query['B']}")

    def _get_saturated_row_from_nonunique_property(self, Tsat: Optional[float] = None, Psat: Optional[float] = None) -> tuple[ThermoState, ThermoState]:
        assert (Tsat is not None) != (Psat is not None), "Must specify either Tsat or Psat for TableBase._get_saturated_row_from_nonunique_property(...)"
        saturated_value = Tsat if Tsat is not None else Psat
        saturated_property = 'temperature' if Tsat is not None else Psat

        tightest_lower_bound: Optional[tuple[ThermoState, ThermoState]] = None
        tightest_upper_bound: Optional[tuple[ThermoState, ThermoState]] = None
        for row_num in range(self._saturated_table.shape[0]):
            vapor, liquid = self._get_saturated_row(row_num=row_num)
            if getattr(vapor, saturated_property) < saturated_value:
                if tightest_lower_bound is None or getattr(tightest_lower_bound[0], saturated_property) < getattr(vapor, saturated_property):
                    tightest_lower_bound = vapor, liquid
            if getattr(vapor, saturated_property) > saturated_value:
                if tightest_upper_bound is None or getattr(tightest_upper_bound[0], saturated_property) > getattr(vapor, saturated_property):
                    tightest_upper_bound = vapor, liquid
        if tightest_upper_bound is None or tightest_lower_bound is None: raise OutOfTableBoundsError
        lerpfloat: LerpFloat = (saturated_value - getattr(tightest_lower_bound[0], saturated_property)) / (
                    getattr(tightest_upper_bound[0], saturated_property) - getattr(tightest_lower_bound[0], saturated_property))
        return self._lerp(lerpfloat, tightest_lower_bound[0], tightest_upper_bound[0]), self._lerp(lerpfloat, tightest_lower_bound[1], tightest_upper_bound[1])

    _nonunique_property_args = get_args(NonUniqueProperty)
    def _get_saturated_state(self, properties: dict[ThermoProperty, float], quiet: bool = False) -> SaturatedQueryResult:
        assert len(set(properties)) == 2, "Must provide exactly two different properties"
        nonunique_number: int = sum(prop in self._nonunique_property_args for prop in properties)

        if nonunique_number == 2:
            vapor, liquid = self._get_saturated_row_from_nonunique_property(Psat=properties['pressure'])
            if properties['temperature'] < liquid.temperature: raise CompressedNotSaturatedMixtureError
            elif properties['temperature'] > liquid.temperature: raise SuperheatedNotSaturatedMixtureError
            raise DegenerateStateError

        elif nonunique_number == 1:
            if 'pressure' in properties:
                vapor, liquid = self._get_saturated_row_from_nonunique_property(Psat=properties['pressure'])
                other_property = (set(properties) - {'pressure'}).pop()
                nonunique_property: NonUniqueProperty = 'pressure'
            else:
                vapor, liquid = self._get_saturated_row_from_nonunique_property(Tsat=properties['temperature'])
                other_property = (set(properties) - {'temperature'}).pop()
                nonunique_property: NonUniqueProperty = 'temperature'
            delta = getattr(vapor, other_property) - getattr(liquid, other_property)
            if abs(delta) < 1e-9:
                raise DegenerateStateError(f"No difference in property {other_property} between saturated states.")

            quality = (properties[other_property] - getattr(liquid, other_property)) / delta
            if not quiet:
                info_log(f"Found quality (x={quality}) via a single property lerp search ({nonunique_property}={properties[nonunique_property]}, {other_property}={properties[other_property]}).")
                self._log_recent_lerps(2)
                if quality > 1.0: raise SuperheatedNotSaturatedMixtureError
                elif quality < 0.0: raise CompressedNotSaturatedMixtureError
            return {
                'quality': quality,
                'vapor_state': vapor,
                'liquid_state': liquid
            }

        else:
            # This is not a great way of doing this, but it's fine.
            props = set(properties)
            prop_1 = props.pop()
            prop_2 = props.pop()

            bracket = self._get_bounds(self._saturated_table, self._saturated_headers, 'temperature')
            quality_from_prop_1 = lambda T: self._get_quality({
                'temperature': T,
                prop_1: properties[prop_1]
            }, quiet=True)['quality']
            quality_from_prop_2 = lambda T: self._get_quality({
                'temperature': T,
                prop_2: properties[prop_2]
            }, quiet=True)['quality']
            f = lambda T: quality_from_prop_1(T) - quality_from_prop_2(T)
            Tsat = _find_root_bisection(f, bracket)

            info_log(f"Found saturation temperature (T={Tsat}) via a double property lerp search ({prop_1}={properties[prop_1]}, {prop_2}={properties[prop_2]}).")
            self._log_recent_lerps(4)

            x_1 = quality_from_prop_1(Tsat)
            x_2 = quality_from_prop_2(Tsat)
            assert abs(x_1 - x_2) < 1e-3, f"There was an appreciable difference in the two estimated qualities ({x_1}, {x_2})."

            quality = 0.5 * (x_1 + x_2)
            vapor, liquid = self._get_saturated_row_from_nonunique_property(Tsat=Tsat)

            if not quiet:
                if quality > 1.0: raise SuperheatedNotSaturatedMixtureError
                elif quality < 0.0: raise CompressedNotSaturatedMixtureError
            return {
                'quality': quality,
                'vapor_state': vapor,
                'liquid_state': liquid
            }

    _thermo_property_args = get_args(ThermoProperty)
    @classmethod
    def _get_2d_table_bounds(cls, table: np.ndarray, headers: list[str], properties: dict[ThermoProperty, float], row_getter: Callable[[int], ThermoState]) -> Table2DQuery:
        assert all(prop in headers for prop in properties), f"One of the properties, `{properties}`, cannot be found in `{headers}`."
        assert len(properties) == 2, "Must specify two properties in TableBase._get_2d_table_bounds(...)."
        assert all(prop in cls._thermo_property_args for prop in properties), "Must specify two properties in ThermoProperties in TableBase._get_2d_table_bounds(...)"

        props = set(properties)
        v_prop = props.pop()
        h_prop = props.pop()

        bounds: Table2DQuery = {
            'upper_left': None,
            'upper_right': None,
            'lower_left': None,
            'lower_right': None,
            'vertical_property': v_prop,
            'horizontal_property': h_prop
        }
        for row_num in range(table.shape[0]):
            state = row_getter(row_num)

            vq_val = getattr(state, v_prop)
            hq_val = getattr(state, h_prop)
            if vq_val <= properties[v_prop] and hq_val <= properties[h_prop]:  # possible upper_left
                if bounds['upper_left'] is None or (vq_val >= getattr(bounds['upper_left'], v_prop) and hq_val >= getattr(bounds['upper_left'], h_prop)):
                    bounds['upper_left'] = state
            if vq_val >= properties[v_prop] and hq_val <= properties[h_prop]:  # possible lower_left
                if bounds['lower_left'] is None or (vq_val <= getattr(bounds['lower_left'], v_prop) and hq_val >= getattr(bounds['lower_left'], h_prop)):
                    bounds['lower_left'] = state
            if vq_val >= properties[v_prop] and hq_val >= properties[h_prop]:  # possible lower_right
                if bounds['lower_right'] is None or (vq_val <= getattr(bounds['lower_right'], v_prop) and hq_val <= getattr(bounds['lower_right'], h_prop)):
                    bounds['lower_right'] = state
            if vq_val <= properties[v_prop] and hq_val >= properties[h_prop]:  # possible upper_right
                if bounds['upper_right'] is None or (vq_val >= getattr(bounds['upper_right'], v_prop) and hq_val <= getattr(bounds['upper_right'], h_prop)):
                    bounds['upper_right'] = state
        if any(val is None for val in bounds.values()): raise OutOfTableBoundsError
        return bounds

    def _get_2d_lerped_values(self, table: np.ndarray, headers: list[str], properties: dict[ThermoProperty, float], row_getter: Callable[[int], ThermoState]) -> ThermoState:
        bounds = self._get_2d_table_bounds(table, headers, properties, row_getter)

        lerp_count = 0
        if bounds['upper_left'] != bounds['lower_left']:
            x_l = (properties[bounds['vertical_property']] - getattr(bounds['upper_left'],
                                                                     bounds['vertical_property'])) / (
                              getattr(bounds['lower_left'], bounds['vertical_property']) - getattr(bounds['upper_left'],
                                                                                                   bounds[
                                                                                                       'vertical_property']))
            left = self._lerp(x_l, bounds['lower_left'], bounds['upper_left'])
            lerp_count += 1
        else:
            x_l = 'unused'
            left = bounds['lower_left']

        if bounds['upper_right'] != bounds['lower_right']:
            x_r = (properties[bounds['vertical_property']] - getattr(bounds['upper_right'],
                                                                     bounds['vertical_property'])) / (
                              getattr(bounds['lower_right'], bounds['vertical_property']) - getattr(
                          bounds['upper_right'], bounds['vertical_property']))
            right = self._lerp(x_r, bounds['lower_right'], bounds['upper_right'])
            lerp_count += 1
        else:
            x_r = 'unused'
            right = bounds['upper_right']

        if left != right:
            x_f = (properties[bounds['horizontal_property']] - getattr(left, bounds['horizontal_property'])) / (
                        getattr(right, bounds['horizontal_property']) - getattr(left, bounds['horizontal_property']))
            out = self._lerp(x_f, left, right)
            lerp_count += 1
        else:
            x_f = 'unused'
            out = left

        info_log(
            f'2D-lerping to find value; used x={x_l} for left-bounds, x={x_r} for right-bounds, and x={x_f} to lerp between those.')
        self._log_recent_lerps(lerp_count)

        return out

    def _get_compressed_state(self, properties: dict[ThermoProperty, float]) -> ThermoState:
        return self._get_2d_lerped_values(self._compressed_table, self._compressed_headers, properties, self._get_compressed_row)

    def _get_superheated_state(self, properties: dict[ThermoProperty, float]) -> ThermoState:
        return self._get_2d_lerped_values(self._compressed_table, self._compressed_headers, properties, self._get_compressed_row)

    def get_state(self, properties: dict[ThermoProperty, float]) -> QueryResult:
        try:
            result: ThermoState = self._get_superheated_state(properties)
            quality = None
            state: States = 'superheated'
        except OutOfTableBoundsError:
            try:
                result: ThermoState = self._get_compressed_state(properties)
                quality = None
                state: States = 'compressed'
            except OutOfTableBoundsError:
                result: SaturatedQueryResult = self._get_saturated_state(properties)
                quality = result['quality']
                result: ThermoState = self._lerp(quality, result['vapor_state'], result['liquid_state'])
                state: States = 'saturated'
        return {
            'result': result,
            'quality': quality,
            'type': state,
        }

