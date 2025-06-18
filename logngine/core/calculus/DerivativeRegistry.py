from typing import Callable

class DerivativeRegistry:
    def __call__(self, fn: Callable) -> Callable:
        # TODO: Implement this.
        pass

class SecondDerivativeRegistry:
    def __call__(self, fn: Callable) -> Callable:
        # TODO: Implement this.
        pass

d_dx = DerivativeRegistry()
d2_dx2 = SecondDerivativeRegistry()