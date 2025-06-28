from __future__ import annotations
from abc import ABC
from typing import get_args, Literal, Type, ClassVar, Iterable, TypedDict
from dataclasses import dataclass

from .SolverOption import CouplingSolverOption
from .exceptions import *

SpecialSources = Literal['given', 'assumed']


class CouplingSolverOptions(TypedDict):
    valid: list[CouplingSolverOption]
    assumable: list[tuple[CouplingSolverOption, set[str]]]


def coupling(identifier: str):
    def decorator(cls: Type[Coupling]):
        cls.id = identifier
        cls.__name__ = identifier.title() + "Coupling"
        return cls

    return decorator


@dataclass
class Coupling:
    # Class-level fields
    id: ClassVar[str]

    # Class-level internals
    _registry: ClassVar[dict[str, Type[Coupling]]] = {}
    _solvers: ClassVar[list[CouplingSolverOption]] = []
    _reserved_ids: ClassVar[Iterable[str]] = get_args(SpecialSources)

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        Coupling._register_coupling(cls)

    @classmethod
    def _register_coupling(cls, coupling_: Type[Coupling]):
        _id = coupling_.get_id()
        if _id in cls._registry or _id in cls._reserved_ids:
            raise AlreadyRegisteredException
        cls._registry[_id] = coupling_

    @classmethod
    def get_applicable_solvers(
            cls,
            target_var: tuple[str, str],  # (bundle_id, var)
            known_vars: set[tuple[str, str]],
            active_assumptions: set[str]
    ) -> CouplingSolverOptions:
        valid = []
        assumable = []

        for solver in cls._solvers:
            if target_var not in solver.outputs:
                continue
            if solver.inputs.issubset(known_vars):
                missing = solver.missing_assumptions(active_assumptions)
                if not missing:
                    valid.append(solver)
                else:
                    assumable.append((solver, missing))

        return {
            "valid": valid,
            "assumable": assumable,
        }

    @classmethod
    def is_registered(cls, identifier: str) -> bool:
        return identifier in cls._registry

    @classmethod
    def get_registered(cls, identifier: str):
        if not cls.is_registered(identifier):
            raise NotRegisteredException
        return cls._registry[identifier]

    @classmethod
    def get_id(cls) -> str:
        return cls.id
