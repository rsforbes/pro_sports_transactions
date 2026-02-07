"""Pro Sports Transactions API library."""

import logging

from .search import League, Search, TransactionType

# Library best practice: add NullHandler so log messages don't go to
# stderr if the consuming application hasn't configured logging.
# See https://docs.python.org/3/howto/logging.html#configuring-logging-for-a-library
logging.getLogger(__name__).addHandler(logging.NullHandler())

__all__ = ["League", "Search", "TransactionType"]
