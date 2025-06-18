from __future__ import annotations
from typing import Type, Callable, final
from enum import Flag, auto

from loguru import logger
import numpy as np

from .DistributionBase import DistributionBase
from ..calculus.DerivativeRegistry import d_dx, d2_dx2

@final
class NormalDistribution(DistributionBase):
    """
    Represents a multivariate normal distribution with support for arithmetic operations
    including addition, subtraction, multiplication, division, exponentiation, and negation.
    Uses approximation methods for non-linear operations like multiplication and exponentiation.
    Invalid operations are masked out with NaN values and log warnings are issued for approximations.
    """

    class _DebugFlag(Flag):
        NONE = 0
        MULTIPLICATION_APPROXIMATION_WARNING = auto()
        DIVISION_APPROXIMATION_WARNING = auto()
        CONST_POWER_APPROXIMATION_WARNING = auto()
        NORM_POWER_APPROXIMATION_WARNING = auto()

    LOGGER: logger = logger
    __logger_flags: int = _DebugFlag.NONE

    @classmethod
    def from_extrema(cls, min_: np.ndarray | float | int, max_: np.ndarray | float | int) -> NormalDistribution:
        mu = 0.5 * (max_ + min_)
        sigma = 0.5 * (max_ - min_)  # At least 95% confidence that value lies within extrema, 66% within half of extrema. (That seems fair to me.)
        return NormalDistribution(mu, sigma)

    def __init__(self, mu: np.ndarray | float | int, sigma: np.ndarray | float | int):
        """
        Initialize the normal distribution.

        Parameters:
            mu (float | int | np.ndarray): Mean(s) of the distribution
            sigma (float | int | np.ndarray): Standard deviation(s)
        """
        # Broadcast scalars to match shapes
        if isinstance(mu, (float, int)) and isinstance(sigma, (float, int)):
            mu = np.array([mu])
            sigma = np.array([sigma])
        elif isinstance(mu, (float, int)):
            mu = np.ones_like(sigma) * mu
        elif isinstance(sigma, (float, int)):
            sigma = np.ones_like(mu) * sigma

        self.__mean: np.ndarray = mu
        self.__variance: np.ndarray = sigma * sigma

        # Validate shape compatibility
        if self.__mean.shape != self.__variance.shape:
            self.LOGGER.error(f"NormalDistribution init failed: mismatched shapes "
                         f"mu.shape={mu.shape}, sigma.shape={sigma.shape}")
            raise ValueError("Shape mismatch between mean and variance.")

        if len(self.__mean.shape) != 1:
            self.LOGGER.error(f"NormalDistribution init failed: only 0D/1D supported, "
                         f"received shape={self.__mean.shape}")
            raise ValueError("Only 0D and 1D vectors are supported.")

        self.__size = self.__mean.shape[0]

    def size(self) -> int:
        """Return the number of dimensions."""
        return self.__size

    def sample(self) -> np.ndarray:
        """Draw a random sample from the distribution."""
        return np.random.normal(self.__mean, np.sqrt(self.__variance))

    def mean(self) -> np.ndarray:
        """Return the mean vector."""
        return self.__mean

    def median(self) -> np.ndarray:
        """Return the median vector (same as mean for normal)."""
        return self.__mean

    def mode(self) -> np.ndarray:
        """Return the mode vector (same as mean for normal)."""
        return self.__mean

    def variance(self) -> np.ndarray:
        """Return the variance vector."""
        return self.__variance

    def std(self) -> np.ndarray:
        """Return the standard deviation."""
        return np.sqrt(self.__variance)

    def kld(self) -> float:
        """Return Kullback-Leibler divergence from itself (always 0)."""
        return 0.0

    def apply_(self, fn: Callable[[np.ndarray], np.ndarray]) -> None:
        """
        Applies function in-place to a normal distribution and approximates output as normal using first-order delta approximation.
        """
        df_dx = d_dx(fn)
        d2f_dx2 = d2_dx2(fn)

        self.__mean = fn(self.__mean) + 0.5 * d2f_dx2 * self.__variance
        self.__variance *= df_dx * df_dx

    def apply(self, fn: Callable[[np.ndarray], np.ndarray]) -> NormalDistribution:
        """
        Applies function in-place to a normal distribution and approximates output as normal using first-order delta approximation.
        """
        _cpy = self
        _cpy.apply_(fn)
        return _cpy

    def __add__(self, other: Type[DistributionBase] | np.ndarray | float | int) -> DistributionBase:
        """Element-wise addition between distributions or constants."""
        if isinstance(other, NormalDistribution):
            return NormalDistribution(self.__mean + other.__mean, self.__variance + other.__variance)
        elif isinstance(other, (float, int, np.ndarray)):
            return NormalDistribution(self.__mean + other, self.__variance)
        raise NotImplementedError

    def __sub__(self, other: Type[DistributionBase] | np.ndarray | float | int) -> DistributionBase:
        """Element-wise subtraction."""
        return self.__add__(-other)

    def __mul__(self, other: Type[DistributionBase] | np.ndarray | float | int) -> DistributionBase | float:
        """
        Approximates product of normal with scalar or another normal using moment matching.
        Only exact when multiplying by a scalar.
        """
        if isinstance(other, (float, int, np.ndarray)):
            return NormalDistribution(self.__mean * other, self.__variance * other * other)
        elif isinstance(other, NormalDistribution):
            mean = self.__mean * other.__mean
            var = self.__mean * self.__mean * other.__variance + other.__mean * other.__mean * self.__variance + self.__variance * other.__variance
            if not self.__logger_flags & self._DebugFlag.MULTIPLICATION_APPROXIMATION_WARNING:
                self.__logger_flags |= self._DebugFlag.MULTIPLICATION_APPROXIMATION_WARNING
                self.LOGGER.warning("Approximating non-normal product of two normals as normal distribution.")
            return NormalDistribution(mean, np.sqrt(var))
        raise NotImplementedError

    def __truediv__(self, other: Type[DistributionBase] | np.ndarray | float | int) -> DistributionBase | float:
        """
        Approximates element-wise division using delta method. NaNs are used for divisions with 0-mean denominators.
        """
        if isinstance(other, (float, int, np.ndarray)):
            return NormalDistribution(self.__mean / other, self.__variance / (other * other))

        elif isinstance(other, NormalDistribution):
            mask = other.__mean != 0

            result_mu = np.full_like(self.__mean, np.nan)
            result_var = np.full_like(self.__variance, np.nan)

            if not self.__logger_flags & self._DebugFlag.DIVISION_APPROXIMATION_WARNING:
                self.__logger_flags |= self._DebugFlag.DIVISION_APPROXIMATION_WARNING
                self.LOGGER.warning("Using delta-method to approximate division of two normals X / Y. "
                               "This is numerically unstable when E[Y] = 0. Masking those cases.")

            result_mu[mask] = self.__mean[mask] / other.__mean[mask] * (1 + other.__variance[mask] / other.__mean[mask] ** 2)
            result_var[mask] = self.__variance[mask] / other.__mean[mask] ** 2 + (self.__mean[mask] ** 2) * other.__variance[mask] / other.__mean[mask] ** 4

            return NormalDistribution(result_mu, np.sqrt(result_var))

        raise NotImplementedError("Unsupported operand for division.")

    def __rtruediv__(self, other: Type[DistributionBase] | np.ndarray | float | int) -> DistributionBase | float:
        """Reverse division for constant / normal. Equivalent to constant * (1 / normal)."""
        if isinstance(other, (float, int, np.ndarray)):
            num = NormalDistribution(other, 0.0)
            return num.__truediv__(self)
        raise NotImplementedError

    def __pow__(self, power: Type[DistributionBase] | np.ndarray | float | int, modulo=None) -> DistributionBase | float:
        """
        Approximates X^Y where X is this normal and Y is scalar or another normal.
        Uses moment matching and masks invalid regions where X <= 0.
        """
        if isinstance(power, NormalDistribution):
            mask = self.__mean > 0
            result_mu = np.full_like(self.__mean, np.nan)
            result_var = np.full_like(self.__variance, np.nan)

            if not self.__logger_flags & self._DebugFlag.NORM_POWER_APPROXIMATION_WARNING:
                self.__logger_flags |= self._DebugFlag.NORM_POWER_APPROXIMATION_WARNING
                self.LOGGER.warning("Numerical instability: Approximating X^Y where X and Y are normally distributed. "
                               "This is a non-analytic form. Using moment-matching approximation and masking invalid domains (X <= 0).")

            log_x = np.zeros_like(self.__mean)
            log_x[mask] = np.log(self.__mean[mask])

            result_mu[mask] = np.exp(power.__mean[mask] * log_x[mask] +
                                     0.5 * (power.__variance[mask] * log_x[mask] ** 2 +
                                            power.__mean[mask] ** 2 * self.__variance[mask] / self.__mean[mask] ** 2))

            result_var[mask] = (
                    result_mu[mask] ** 2 *
                    (np.exp(power.__variance[mask] * log_x[mask] ** 2 +
                            power.__mean[mask] ** 2 * self.__variance[mask] / self.__mean[mask] ** 2 +
                            self.__variance[mask] * power.__variance[mask] * log_x[mask] ** 2 / self.__mean[mask] ** 2) - 1)
            )

            return NormalDistribution(result_mu, np.sqrt(result_var))

        elif isinstance(power, (float, int, np.ndarray)):
            a = power
            mask = self.__mean > 0
            result_mu = np.full_like(self.__mean, np.nan)
            result_var = np.full_like(self.__variance, np.nan)

            if not self.__logger_flags & self._DebugFlag.CONST_POWER_APPROXIMATION_WARNING:
                self.__logger_flags |= self._DebugFlag.CONST_POWER_APPROXIMATION_WARNING
                self.LOGGER.warning("Using delta-method approximation for X^a where X ~ N(\u03bc, \u03c3\u00b2). "
                               "This approximation is only accurate if \u03c3/\u03bc < 0.2 and \u03bc > 0. Masking invalid (\u03bc <= 0) elements.")

            result_mu[mask] = self.__mean[mask] ** a + 0.5 * a * (a - 1) * self.__mean[mask] ** (a - 2) * self.__variance[mask]
            result_var[mask] = (a ** 2) * self.__mean[mask] ** (2 * a - 2) * self.__variance[mask]

            return NormalDistribution(result_mu, np.sqrt(result_var))

        raise NotImplementedError("Unsupported operand for power.")

    def __rpow__(self, other: Type[DistributionBase] | np.ndarray | float | int) -> DistributionBase | float:
        """
        Approximates a^X where a is constant and X is a normal distribution.
        Uses log-normal moment-matching formula.
        """
        if not isinstance(other, (float, int)):
            raise NotImplementedError("Only constant^Normal is supported.")

        if other <= 0:
            self.LOGGER.error(f"Invalid operation: constant {other} cannot be raised to a normal exponent. Base must be > 0.")
            raise ValueError("Base must be positive for real-valued power of a normal distribution.")

        log_a = np.log(other)
        mu = np.exp(self.__mean * log_a + 0.5 * self.__variance * log_a ** 2)
        var = (np.exp(self.__variance * log_a ** 2) - 1) * np.exp(2 * self.__mean * log_a + self.__variance * log_a ** 2)

        return NormalDistribution(mu, np.sqrt(var))

    def __neg__(self) -> DistributionBase | float:
        """Return the negation of the normal distribution (flip mean sign)."""
        return NormalDistribution(-self.__mean, self.__variance)