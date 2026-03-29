"""Seeded RNG wrapper for deterministic gameplay and subsystem isolation."""
from __future__ import annotations

import random


class GameRNG:
    """Seedable RNG that supports forking for subsystem isolation.

    Usage:
        rng = GameRNG(seed=42)
        combat_rng = rng.fork("combat")
        levelgen_rng = rng.fork("levelgen")

    Forked RNGs produce deterministic sequences independent of each other,
    so combat randomness doesn't affect level generation determinism.
    """

    def __init__(self, seed: int | None = None) -> None:
        self.seed = seed if seed is not None else random.randint(0, 2**32 - 1)
        self._rng = random.Random(self.seed)

    def fork(self, namespace: str) -> GameRNG:
        """Create a child RNG with a deterministic seed derived from this one + namespace."""
        child_seed = self._rng.getrandbits(64) ^ hash(namespace)
        child = GameRNG.__new__(GameRNG)
        child.seed = child_seed
        child._rng = random.Random(child_seed)
        return child

    def randint(self, a: int, b: int) -> int:
        return self._rng.randint(a, b)

    def random(self) -> float:
        return self._rng.random()

    def choice(self, seq: list) -> object:
        return self._rng.choice(seq)

    def choices(self, population: list, *, weights: list[float] | None = None, k: int = 1) -> list:
        return self._rng.choices(population, weights=weights, k=k)

    def shuffle(self, seq: list) -> None:
        self._rng.shuffle(seq)

    def sample(self, population: list, k: int) -> list:
        return self._rng.sample(population, k)

    def gauss(self, mu: float, sigma: float) -> float:
        return self._rng.gauss(mu, sigma)

    def getstate(self) -> tuple:
        return self._rng.getstate()

    def setstate(self, state: tuple) -> None:
        self._rng.setstate(state)
