"""uxandeh: African Fractal Hash (AFH) Package.

This package implements the African Fractal Hash (AFH) algorithm using discrete
Iterated Function Systems (IFS) and Sona Permutations.

All code and comments follow British English spelling conventions.
"""

from .hash import uxandeh
from .compression import DEFAULT_IV, PRIME_P

__all__ = ["uxandeh", "DEFAULT_IV", "PRIME_P"]
