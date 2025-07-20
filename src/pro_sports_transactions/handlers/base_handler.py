"""Base classes for HTTP request handling."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class RequestConfig:
    """Base configuration for request handling"""


class RequestHandler(ABC):  # pylint: disable=too-few-public-methods
    """Abstract base class for handling HTTP requests"""

    @abstractmethod
    async def get(self, url: str, headers: Dict[str, str]) -> Optional[str]:
        """Make a GET request and return the response text"""
