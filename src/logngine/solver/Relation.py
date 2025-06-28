from __future__ import annotations
from abc import ABC, abstractmethod
from typing import get_args, Literal, Type, ClassVar, Iterable, TypedDict
from dataclasses import dataclass

from .SolverOption import RelationSolverOption
from .State import State
from .exceptions import *

SpecialSources = Literal['given', 'assumed']

class RelationSolverOptions(TypedDict):
    valid: list[RelationSolverOption]
    assumable: list[RelationSolverOption]

def relation(identifier: str):
    def decorator(cls: Type[Relation]):
        cls.id = identifier
        cls.__name__ = identifier.title() + "Relation"
        return cls
    return decorator

@dataclass
class Relation:
    # Class-level fields
    id: ClassVar[str]

    # Class-level internals
    _registry: ClassVar[dict[str, Type[Relation]]] = {}
    _solvers: ClassVar[list[RelationSolverOption]] = []
    _reserved_ids: ClassVar[Iterable[str]] = get_args(SpecialSources)

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        Relation._register_relation(cls)

    @classmethod
    def _register_relation(cls, relation_: Type[Relation]):
        _inv_id: str = relation_.get_id()
        if _inv_id in cls._registry or _inv_id in cls._reserved_ids: raise AlreadyRegisteredException
        cls._registry[_inv_id] = relation_

    @classmethod
    def get_applicable_solvers(cls, target_var: str, known_vars: set[str], active_assumptions: set[str]) -> RelationSolverOptions:
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
            'valid': valid,
            'assumable': assumable,
        }

    @classmethod
    def is_registered(cls, identifier: str) -> bool:
        return identifier in cls._registry

    @classmethod
    def get_registered(cls, identifier: str):
        if not cls.is_registered(identifier): raise NotRegisteredException
        return cls._registry[identifier]

    @classmethod
    def get_id(cls) -> str: return cls.id