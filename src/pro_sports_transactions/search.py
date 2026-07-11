"""Pro Sports Transactions search module.

This module provides classes and utilities for searching and retrieving
professional sports transaction data from prosportstransactions.com.
"""

import json
import warnings
from datetime import date
from enum import Enum, StrEnum
from io import StringIO
from typing import Dict, Optional
from urllib import parse

import pandas as pd
from pandas import DataFrame, read_html

from .handlers import DirectRequestHandler, RequestHandler


class League(StrEnum):
    """Sports leagues supported by the prosportstransactions.com website."""

    MLB = "baseball"
    NBA = "basketball"
    NFL = "football"
    NHL = "hockey"
    MLS = "soccer"


class TransactionType(Enum):
    """Transaction types available for filtering sports transactions."""

    # Maintaining backwards compatibility
    Disciplinary = {"default": "DisciplinaryChkBx"}
    InjuredList = {"default": "ILChkBx", "MLB": "DLChkBx"}
    Injury = {"default": "InjuriesChkBx"}
    LegalIncident = {"default": "LegalChkBx"}
    MinorLeagueToFrom = {"default": "NBADLChkBx", "MLB": "MinorsChkBx"}
    Movement = {"default": "PlayerMovementChkBx"}
    PersonalReason = {"default": "PersonalChkBx"}

    def __getitem__(self, value):
        """Get form field name for the transaction type and league."""
        if isinstance(value, League):
            name = value.name
            return self.value[name] if name in self.value else self.value["default"]
        return self.value


class Search:
    """Main class for searching professional sports transactions."""

    def __init__(
        self,
        league: League = League.NBA,
        transaction_types: TransactionType = (),
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        player: str = None,
        team: str = None,
        starting_row: int = 0,
        request_handler: Optional[RequestHandler] = None,
    ):
        # Resolve date defaults at call time. Using date.today() as an argument
        # default would freeze the value at import time (evaluated once), so a
        # long-lived process would keep defaulting to its import day.
        if start_date is None:
            start_date = date.today()
        if end_date is None:
            end_date = date.today()
        self._url = UrlBuilder.build(
            league=league,
            transaction_types=transaction_types,
            start_date=start_date,
            end_date=end_date,
            player=player,
            team=team,
            starting_row=starting_row,
        )
        # Track if custom handler was provided for backward compatibility
        self._custom_handler = request_handler is not None
        self._request_handler = request_handler or DirectRequestHandler()

    async def get_dataframe(self) -> DataFrame:
        """Get search results as a pandas DataFrame.

        Returns:
            DataFrame with columns: Date, Team, Acquired, Relinquished, Notes
            Includes attrs['pages'] for pagination info and attrs['errors'] if any
        """
        # Generic DataFrame to hold results
        # For backward compatibility, use Http.get() when using default handler
        if not self._custom_handler:
            response = await Http.get(self._url)
        else:
            response = await self._request_handler.get(self._url, headers)

        df = None
        try:
            # Wrap the HTML in StringIO: pandas 3.0 dropped read_html's implicit
            # acceptance of a literal HTML string (it now treats a bare str as a
            # path/URL). StringIO is also accepted by pandas 2.2.x, so this works
            # across the whole supported range.
            df_list = read_html(StringIO(response), header=0, keep_default_na=False)
            df = pd.DataFrame(
                df_list[0],
                columns=["Date", "Team", "Acquired", "Relinquished", "Notes"],
            )
            df.attrs["pages"] = int(df_list[1].columns[2].split(" ")[-1])
        except (ValueError, IndexError, AttributeError, TypeError) as e:
            df = pd.DataFrame(
                columns=["Date", "Team", "Acquired", "Relinquished", "Notes"]
            )
            df.attrs["pages"] = 0
            df.attrs["errors"] = (repr(e),)

        return df

    async def get_dict(self):
        """Get search results as a dictionary."""
        df = await self.get_dataframe()

        data = {}
        data["transactions"] = df.to_dict(orient="records")
        data["pages"] = df.attrs["pages"]
        if "errors" in df.attrs:
            data["errors"] = df.attrs["errors"]
        return data

    async def get_json(self):
        """Get search results as JSON string."""
        return json.dumps(await self.get_dict())

    async def get_url(self):
        """Get the search URL."""
        return self._url


NETLOC = "https://www.prosportstransactions.com"
PATH = "Search/SearchResults.php"

headers = {
    "accept": "*/*",
    "accept-encoding": "gzip, deflate, br",
    "accept-language": "en-US,en;q=0.9",
    "connection": "keep-alive",
    "content-type": "text/html; charset=utf-8 ",
    "referer": "https://www.prosportstransactions.com/",
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        + "AppleWebKit/537.36 (KHTML, like Gecko) "
        + "Chrome/112.0.0.0 Safari/537.36 Edg/112.0.1722.48"
    ),
}


class Parameter:
    """Utility class for creating search parameters."""

    @staticmethod
    def date_param(key: str, value: date) -> Dict:
        """Create a date parameter for search."""
        return {key: value.strftime("%Y-%m-%d") if isinstance(value, date) else ""}

    @staticmethod
    def transaction_type(param_name) -> Dict:
        """Create a transaction type parameter."""
        return {param_name: "yes"}

    @staticmethod
    def start_date(start_date: date) -> Dict:
        """Create start date parameter."""
        return Parameter.date_param("BeginDate", start_date)

    @staticmethod
    def end_date(end_date: date) -> Dict:
        """Create end date parameter."""
        return Parameter.date_param("EndDate", end_date)

    @staticmethod
    def player(player_name: str) -> Dict:
        """Create player name parameter."""
        return {} if player_name is None else {"Player": player_name}

    @staticmethod
    def team(team_name: str) -> Dict:
        """Create team name parameter."""
        return {} if team_name is None else {"Team": team_name}

    @staticmethod
    def starting_row(starting_row: int) -> Dict:
        """Create starting row parameter for pagination."""
        return {"start": str(starting_row)}

    @staticmethod
    def submit():
        """Create submit parameter."""
        return {"Submit": "Search"}


class UrlBuilder:
    """Utility class for building search URLs."""

    @staticmethod
    def build(
        league=League.NBA,
        transaction_types=(),
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        player=None,
        team=None,
        starting_row=None,
    ):
        """Build search URL with given parameters."""
        # Resolve date defaults at call time (see Search.__init__).
        if start_date is None:
            start_date = date.today()
        if end_date is None:
            end_date = date.today()
        params = {}
        params |= Parameter.start_date(start_date)
        params |= Parameter.end_date(end_date)
        params |= Parameter.player(player)
        params |= Parameter.team(team)
        params |= Parameter.starting_row(starting_row)
        params |= Parameter.submit()

        # Add all Transaction Type parameter values
        for transaction_type in transaction_types:
            params |= Parameter.transaction_type(
                TransactionType[transaction_type.name][league]
            )

        return f"{NETLOC}/{league.value}/{PATH}?{parse.urlencode(params)}"


# Backward compatibility - deprecated Http class
class Http:
    """
    Deprecated: Use DirectRequestHandler from .handlers instead.
    This class is kept for backward compatibility and will be removed in v2.0.
    """

    @staticmethod
    async def get(url):
        """Get data from URL (deprecated - use Search class instead)."""
        warnings.warn(
            "Http.get() will be deprecated in a future release. "
            + "Use the Search class methods instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        handler = DirectRequestHandler()
        return await handler.get(url, headers)
