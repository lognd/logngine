from typing import Type

import numpy as np
from loguru import logger

from logngine.core.uncertainty.DistributionBase import DistributionBase

class TrivialDistribution(DistributionBase):

    def __init__(self, value: np.ndarray | float | int):
        if isinstance(value, (float, int)):
            value = np.array([value])
        self.__val = value

        if len(self.__val.shape) != 1:
            logger.error(f"NormalDistribution init failed: only 0D/1D supported, "
                         f"received shape={self.__val.shape}")
            raise ValueError("Only 0D and 1D vectors are supported.")

        self.__size = self.__val.shape[0]

    @property
    def size(self) -> int:
        return self.__size

    def sample(self) -> np.ndarray:
        return self.__val

    def mean(self) -> np.ndarray:
        return self.__val

    def median(self) -> np.ndarray:
        return self.__val

    def mode(self) -> np.ndarray:
        return self.__val

    def variance(self) -> np.ndarray:
        return np.zeros_like(self.__val)

    def kld(self) -> float:
        return np.zeros_like(self.__val)

    def __add__(self, other: Type[DistributionBase] | np.ndarray | float | int) -> DistributionBase:
        if isinstance(other, TrivialDistribution):
            return TrivialDistribution(self.__val + other.__val)
        elif isinstance(other, (float, int)):
            return TrivialDistribution(self.__val + other)
        return other + self.__val

    def __sub__(self, other: Type[DistributionBase] | np.ndarray | float | int) -> DistributionBase:
        if isinstance(other, TrivialDistribution):
            return TrivialDistribution(self.__val - other.__val)
        elif isinstance(other, (float, int)):
            return TrivialDistribution(self.__val - other)
        return other - self.__val

    def __mul__(self, other: Type[DistributionBase] | np.ndarray | float | int) -> DistributionBase | float:
        if isinstance(other, TrivialDistribution):
            return TrivialDistribution(self.__val * other.__val)
        elif isinstance(other, (float, int)):
            return TrivialDistribution(self.__val * other)
        return other * self.__val

    def __truediv__(self, other: Type[DistributionBase] | np.ndarray | float | int) -> DistributionBase | float:
        if isinstance(other, TrivialDistribution):
            return TrivialDistribution(self.__val / other.__val)
        elif isinstance(other, (float, int)):
            return TrivialDistribution(self.__val / other)
        return self.__val / other

    def __rtruediv__(self, other: Type[DistributionBase] | np.ndarray | float | int) -> DistributionBase | float:
        if isinstance(other, (float, int)):
            return TrivialDistribution(other / self.__val)
        return other / self.__val

    def __pow__(self, power: Type[DistributionBase] | np.ndarray | float | int,
                modulo=None) -> DistributionBase | float:
        if isinstance(power, TrivialDistribution):
            return TrivialDistribution(self.__val ** power.__val)
        elif isinstance(power, (float, int)):
            return TrivialDistribution(self.__val ** power)
        return self.__val ** power

    def __rpow__(self, other: Type[DistributionBase] | np.ndarray | float | int) -> DistributionBase | float:
        if isinstance(other, (float, int)):
            return TrivialDistribution(other ** self.__val)
        return other ** self.__val

    def __neg__(self) -> DistributionBase | float:
        return TrivialDistribution(-self.__val)