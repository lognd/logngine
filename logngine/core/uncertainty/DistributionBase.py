from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Type

import numpy as np

class DistributionBase(ABC):

    @property
    @abstractmethod
    def size(self) -> int: pass

    @abstractmethod
    def sample(self) -> np.ndarray: pass
    @abstractmethod
    def mean(self) -> np.ndarray: pass
    @abstractmethod
    def median(self) -> np.ndarray: pass
    @abstractmethod
    def mode(self) -> np.ndarray: pass

    @abstractmethod
    def variance(self) -> np.ndarray: pass
    def std(self) -> np.ndarray: return np.sqrt(self.variance())

    @abstractmethod
    def kld(self) -> float: pass

    @abstractmethod
    def __add__(self, other: Type[DistributionBase] | np.ndarray | float | int) -> DistributionBase: pass
    def __radd__(self, other: Type[DistributionBase] | np.ndarray | float | int) -> DistributionBase: return self.__add__(other)

    @abstractmethod
    def __sub__(self, other: Type[DistributionBase] | np.ndarray | float | int) -> DistributionBase: pass
    def __rsub__(self, other: Type[DistributionBase] | np.ndarray | float | int) -> DistributionBase: return DistributionBase.__add__(-self, other)

    @abstractmethod
    def __mul__(self, other: Type[DistributionBase] | np.ndarray | float | int) -> DistributionBase | float: pass
    def __rmul__(self, other: Type[DistributionBase] | np.ndarray | float | int) -> DistributionBase | float: return self.__mul__(other)

    @abstractmethod
    def __truediv__(self, other: Type[DistributionBase] | np.ndarray | float | int) -> DistributionBase | float: pass
    @abstractmethod
    def __rtruediv__(self, other: Type[DistributionBase] | np.ndarray | float | int) -> DistributionBase | float: pass

    def __idiv__(self, other: Type[DistributionBase] | np.ndarray | float | int) -> DistributionBase | float: self.__truediv__(other)
    def __rfloordiv__(self, other: Type[DistributionBase] | np.ndarray | float | int) -> DistributionBase | float: return self.__rtruediv__(other)

    @abstractmethod
    def __pow__(self, power: Type[DistributionBase] | np.ndarray | float | int, modulo=None) -> DistributionBase | float: pass
    @abstractmethod
    def __rpow__(self, other: Type[DistributionBase] | np.ndarray | float | int) -> DistributionBase | float: pass

    @abstractmethod
    def __neg__(self) -> DistributionBase | float: pass

