"""
Request handlers for the Pro Sports Transactions library.

This module provides a plugin architecture for handling HTTP requests,
allowing different strategies for bypassing Cloudflare protection and
other network challenges.
"""

from .base_handler import RequestConfig, RequestHandler
from .direct_handler import DirectRequestHandler
from .unflare_handler import UnflareConfig, UnflareRequestHandler

__all__ = [
    "RequestHandler",
    "RequestConfig",
    "DirectRequestHandler",
    "UnflareRequestHandler",
    "UnflareConfig",
]
