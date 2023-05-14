from datetime import date
from enum import Enum, StrEnum
from pandas import read_html
from typing import Dict
from urllib import parse
import aiohttp
import json
import pandas as pd


class League(StrEnum):
    MLB = "baseball"
    NBA = "basketball"
    NFL = "football"
    NHL = "hockey"
    MLS = "soccer"


class TransactionTypes(Enum):
    DisciplinaryActions = {"default": "DisciplinaryChkBx"}
    InjuredList = {"default": "ILChkBx", "MLB": "DLChkBx"}
    Injuries = {"default": "InjuriesChkBx"}
    LegalIncidents = {"default": "LegalChkBx"}
    MinorLeagueToFrom = {"default": "NBADLChkBx", "MLB": "MinorsChkBx"}
    General = {"default": "PlayerMovementChkBx"}
    PersonalReasons = {"default": "PersonalChkBx"}

    def __getitem__(cls, value):
        if type(value) == League:
            name = value.name
            return cls.value[name] if name in cls.value else cls.value["default"]
        else:
            return cls.value


class Search:
    def __init__(
        self,
        league: League = League.NBA,
        transaction_types: TransactionTypes = (),
        start_date: date = date.today(),
        end_date: date = date.today(),
        player: str = None,
        team: str = None,
        starting_row: int = 0,
    ):
        self._url = UrlBuilder.build(
            league=league,
            transaction_types=transaction_types,
            start_date=start_date,
            end_date=end_date,
            player=player,
            team=team,
            starting_row=starting_row,
        )

    async def _search(self) -> list:
        response = await Http.get(self._url)
        return read_html(response, header=0, keep_default_na=False)

    async def get_dataframe(self):
        data = await self._search()
        df = pd.DataFrame(data[0], columns=["Date", "Team", "Acquired", "Relinquished", "Notes"])
        df.attrs["pages"] = data[1].columns[2].split(" ")[-1]
        return df

    async def get_dict(self):
        results = await self._search()

        data = {}
        data["transactions"] = results[0].to_dict(orient="records")
        data["pages"] = int(results[1].columns[2].split(" ")[-1])

        return data

    async def get_json(self):
        return json.dumps(await self.get_dict())

    async def get_url(self):
        return self._url


netloc = "https://www.prosportstransactions.com"
path = "Search/SearchResults.php"

headers = {
    "accept": "*/*",
    "accept-encoding": "gzip, deflate, br",
    "accept-language": "en-US,en;q=0.9",
    "connection": "keep-alive",
    "content-type": "text/html; charset=utf-8 ",
    "referer": "https://www.prosportstransactions.com/",
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) \
        AppleWebKit/537.36 (KHTML, like Gecko) \
        Chrome/112.0.0.0 Safari/537.36 Edg/112.0.1722.48"
    ),
}


class Parameter:
    @staticmethod
    def date_param(key: str, value: date) -> Dict:
        iso8601 = ""

        if value is not None and type(value) == date:
            iso8601 = value.strftime("%Y-%m-%d")

        return {key: iso8601}

    @staticmethod
    def transaction_type(param_name) -> Dict:
        return {param_name: "yes"}

    @staticmethod
    def start_date(start_date: date) -> Dict:
        return Parameter.date_param("BeginDate", start_date)

    @staticmethod
    def end_date(end_date: date) -> Dict:
        return Parameter.date_param("EndDate", end_date)

    @staticmethod
    def player(player_name: str) -> Dict:
        return {} if player_name is None else {"Player": player_name}

    @staticmethod
    def team(team_name: str) -> Dict:
        return {} if team_name is None else {"Team": team_name}

    @staticmethod
    def starting_row(starting_row: int) -> Dict:
        return {"start": str(starting_row)}

    @staticmethod
    def submit():
        return {"Submit": "Search"}


class UrlBuilder:
    @staticmethod
    def build(
        league=League.NBA,
        transaction_types=(),
        start_date: date = date.today(),
        end_date: date = date.today(),
        player=None,
        team=None,
        starting_row=None,
    ):
        params = {}
        params |= Parameter.start_date(start_date)
        params |= Parameter.end_date(end_date)
        params |= Parameter.player(player)
        params |= Parameter.team(team)
        params |= Parameter.starting_row(starting_row)
        params |= Parameter.submit()

        # Add all Transaction Type parameter values
        for transaction_type in transaction_types:
            params |= Parameter.transaction_type(TransactionTypes[transaction_type.name][league])

        return f"{netloc}/{league.value}/{path}?{parse.urlencode(params)}"


class Http:
    @staticmethod
    async def get(url):
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(url) as response:
                return None if response.status != 200 else await response.text(encoding="utf-8")
