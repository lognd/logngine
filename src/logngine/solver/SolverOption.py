from dataclasses import dataclass, field
from typing import Callable, Literal, Optional, Generic, TypeVar

T = TypeVar("T", str, tuple[str, str])

@dataclass
class SolverOptionBase(Generic[T]):
    implementation: Callable
    inputs: set[T]
    outputs: set[T]
    method: Literal["direct", "symbolic", "tabular"] = "direct"
    assumptions: set[str] = field(default_factory=set)
    symbolic_expr: Optional[str] = None

    def missing_assumptions(self, active: set[str]) -> set[str]:
        return self.assumptions - active

    def is_applicable(self, known_vars: set[T], active_assumptions: set) -> bool:
        return self.inputs.issubset(known_vars) and self.assumptions.issubset(active_assumptions)

class RelationSolverOption(SolverOptionBase[str]): ...
class CouplingSolverOption(SolverOptionBase[tuple[str, str]]): ...
