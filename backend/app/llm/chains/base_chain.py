"""Base fraud scoring chain interface."""
from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseFraudChain(ABC):
    """Abstract base for sector-specific fraud scoring chains."""

    @abstractmethod
    def score(self, data: Dict[str, Any]) -> float:
        """Compute fraud score (0-100) for the given data."""
        pass
