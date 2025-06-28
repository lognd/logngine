from .Bundle import Bundle
from .Coupling import Coupling
from .State import State
from .Relation import Relation

class SolverEngine:
    def __init__(self, bundles: dict[str, Bundle]):
        self.bundles = bundles  # e.g., {"inlet": <Bundle>, "outlet": <Bundle>}
        self.active_assumptions: set[str] = set()

    def solve_for(self, target_var: str, in_bundle: str) -> bool:
        bundle = self.bundles[in_bundle]
        state = bundle.states.get(target_var)

        if state is None:
            print(f"State {target_var} does not exist in bundle '{in_bundle}'")
            return False

        if state.is_known():
            print(f"{in_bundle}.{target_var} is already known: {state.value}")
            return True

        known_vars = {k for k, s in bundle.states.items() if s.is_known()}
        print(f"Trying to solve for {in_bundle}.{target_var} (knowns: {known_vars})")

        # === RELATION SOLVERS (single-bundle) ===
        for relation_cls in Relation._registry.values():
            solver_options = relation_cls.get_applicable_solvers(target_var, known_vars, self.active_assumptions)

            for solver in solver_options["valid"]:
                try:
                    solver.implementation(bundle)
                    state.source = solver.implementation.__name__
                    print(f"Succeeded with Relation: {solver.implementation.__name__}")
                    return True
                except Exception as e:
                    print(f"[Relation] Failed: {solver.implementation.__name__}: {e}")

            if solver_options["assumable"]:
                print(f"[Relation] Assumable solvers exist for {target_var}, not applied yet.")

        # === COUPLING SOLVERS (cross-bundle) ===
        target_key = (in_bundle, target_var)
        known_keys = {
            (bname, var)
            for bname, bundle in self.bundles.items()
            for var, s in bundle.states.items()
            if s.is_known()
        }

        for coupling_cls in Coupling._registry.values():
            solver_options = coupling_cls.get_applicable_solvers(target_key, known_keys, self.active_assumptions)

            for solver in solver_options["valid"]:
                try:
                    bundles_subset = {b: self.bundles[b] for b, _ in solver.inputs.union(solver.outputs)}
                    solver.implementation(bundles_subset)
                    state.source = solver.implementation.__name__
                    print(f"Succeeded with Coupling: {solver.implementation.__name__}")
                    return True
                except Exception as e:
                    print(f"[Coupling] Failed: {solver.implementation.__name__}: {e}")

            if solver_options["assumable"]:
                print(f"[Coupling] Assumable solvers exist for {in_bundle}.{target_var}, not applied yet.")

        print(f"Could not solve for {target_var} in bundle '{in_bundle}'.")
        return False