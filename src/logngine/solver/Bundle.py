from dataclasses import dataclass
from typing import ClassVar, Type, Optional
from .State import State
from .exceptions import *

def bundle(state_ids: list[str]):
    def decorator(cls: Type[Bundle]):
        for _sta_id in state_ids:
            cls._registered_states[_sta_id] = State.get_registered(_sta_id)
        return cls
    return decorator

@dataclass
class Bundle:
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls._registered_states = {}

    def __init__(self, name: str, values: dict[str, float]):
        self.name = name
        self.states = {}
        for var, val in values.items():
            if var not in self._registered_states: raise UnregisteredStatesException(var)
            state_cls = self._registered_states[var]
            self.states[var] = state_cls(value=val, source="given")

    def is_known(self, var: str) -> bool:
        return self.states[var].is_known()

    def __getitem__(self, item):
        return self.states[item]

    def get_known(self) -> dict[str, State]:
        return {k: s for k, s in self.states.items() if s.is_known()}
