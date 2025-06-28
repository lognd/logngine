from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, ClassVar, Type

from .exceptions import *

def state(identifier: str, variable: str):
    def decorator(cls: Type[State]):
        cls.id = identifier
        cls.var = variable
        cls.__name__ = identifier.title() + "State"
        return cls
    return decorator

@dataclass
class State:
    # Class-level fields
    id: ClassVar[str]  # the name of the state, i.e. "temperature", belongs to class
    var: ClassVar[str]  # the variable corresponding to the state, i.e. "T", belongs to class

    # Instance-level fields
    value: Optional[float] = None  # the value of a state, None if unknown, belongs to instance
    source: Optional[str] = None  # how we arrived at the known value of the state, i.e. "given", "assumed", or an invariance-id, belongs to instance
    parents: dict[str, State] = field(default_factory=dict)  # the states {id: state-instance} used in the above source to find state, belongs to instance.

    # Class-level internals
    _registry: ClassVar[dict[str, Type[State]]] = {}

    @classmethod
    def get_id(cls): return cls.id

    @classmethod
    def _register_state(cls, state_: Type[State]):
        _sta_id: str = state_.get_id()
        if _sta_id in cls._registry: raise AlreadyRegisteredException
        cls._registry[_sta_id] = state_

    @classmethod
    def is_registered(cls, identifier: str) -> bool:
        return identifier in cls._registry

    @classmethod
    def get_registered(cls, identifier: str):
        if not cls.is_registered(identifier): raise NotRegisteredException
        return cls._registry[identifier]

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        State._register_state(cls)

    def is_known(self) -> bool:
        return self.value is not None

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}; {self.id}: {self.var} = {self.value if self.value is not None else '?'}>"