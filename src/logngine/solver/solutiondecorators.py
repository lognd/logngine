from functools import wraps
from typing import Callable, Optional, Literal, Union
from .SolverOption import RelationSolverOption, CouplingSolverOption
import sympy as sp

def solve(*, inputs, outputs, assumes: Optional[set[str]] = None):
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        if all(isinstance(i, str) for i in inputs):
            option = RelationSolverOption(
                implementation=wrapper,
                inputs=inputs,  # PyCharm now knows this is set[str]
                outputs=outputs,
                method="direct",
                assumptions=assumes or set(),
                symbolic_expr=None
            )
        else:
            option = CouplingSolverOption(
                implementation=wrapper,
                inputs=inputs,  # PyCharm knows this is set[tuple[str, str]]
                outputs=outputs,
                method="direct",
                assumptions=assumes or set(),
                symbolic_expr=None
            )

        def attach_to_class(cls):
            cls._solvers.append(option)
            return cls

        return attach_to_class
    return decorator

def symbol(expr: Union[str, list[str]], assumes: Optional[set[str]] = None):
    def decorator(cls):
        equations = expr if isinstance(expr, list) else [expr]
        generated_solvers = []

        for eq_str in equations:
            lhs, rhs = eq_str.split("=") if "=" in eq_str else (eq_str, "0")
            equation = sp.Eq(sp.sympify(lhs.strip()), sp.sympify(rhs.strip()))

            all_symbols = list(equation.free_symbols)
            for target in all_symbols:
                try:
                    solved = sp.solve(equation, target, dict=False)
                    if not solved:
                        continue
                    expr_out = solved[0]
                    inputs = {str(s) for s in expr_out.free_symbols}
                    impl = sp.lambdify(inputs, expr_out, modules="math")

                    option = RelationSolverOption(
                        implementation=impl,
                        inputs=inputs,
                        outputs={str(target)},
                        method="symbolic",
                        assumptions=assumes or set(),
                        symbolic_expr=str(expr_out)
                    )

                    cls._solvers.append(option)
                    generated_solvers.append(option)
                except Exception as e:
                    print(f"Failed to solve {eq_str} for {target}: {e}")

        return cls
    return decorator