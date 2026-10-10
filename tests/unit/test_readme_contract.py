"""The README is the library's contract: everything it shows must keep
working as written.

Some checks read the README itself (its imports and the keyword arguments its
examples pass), so a new example is checked automatically; the rest pin what
the README describes in prose (handler methods, results).
"""

import ast
import dataclasses
import importlib
import importlib.util
import inspect
import json
import re
from pathlib import Path

import pytest

import pro_sports_transactions as pst
from pro_sports_transactions import handlers
from pro_sports_transactions.handlers import (
    DirectRequestHandler,
    NodriverConfig,
    NodriverRequestHandler,
    RequestHandler,
    UnflareConfig,
    UnflareRequestHandler,
)

README = Path(__file__).parents[2] / "README.md"
DATA_DIR = Path(__file__).parent / "data"


def readme_python_blocks():
    return re.findall(r"```python\n(.*?)```", README.read_text(), re.S)


def readme_calls():
    """Every call in the README's examples, as (callee name, keyword names)."""
    for block in readme_python_blocks():
        for node in ast.walk(ast.parse(block)):
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Attribute):
                    name = func.attr
                elif isinstance(func, ast.Name):
                    name = func.id
                else:  # e.g. make()() or handlers[0](): no name to check
                    continue
                yield name, {k.arg for k in node.keywords if k.arg}


class TestReadmeExamples:
    @pytest.mark.unit
    def test_examples_are_valid_python(self):
        blocks = readme_python_blocks()

        assert blocks
        for block in blocks:
            ast.parse(block)

    @pytest.mark.unit
    def test_example_imports_resolve(self):
        for block in readme_python_blocks():
            for node in ast.walk(ast.parse(block)):
                if isinstance(node, ast.ImportFrom) and (node.module or "").startswith(
                    "pro_sports_transactions"
                ):
                    module = importlib.import_module(node.module)
                    for alias in node.names:
                        assert hasattr(module, alias.name) or importlib.util.find_spec(
                            f"{node.module}.{alias.name}"
                        ), f"README imports {alias.name} from {node.module}"
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        importlib.import_module(alias.name)

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "callable_, name",
        [
            (pst.Search, "Search"),
            (NodriverConfig, "NodriverConfig"),
            (UnflareConfig, "UnflareConfig"),
            (NodriverRequestHandler, "NodriverRequestHandler"),
            (UnflareRequestHandler, "UnflareRequestHandler"),
        ],
    )
    def test_example_keyword_arguments_are_accepted(self, callable_, name):
        accepted = set(inspect.signature(callable_).parameters)
        for called, keywords in readme_calls():
            if called == name:
                assert keywords <= accepted, f"{name} no longer accepts {keywords}"


class TestReadmeApi:
    @pytest.mark.unit
    def test_top_level_names(self):
        assert {"League", "Search", "TransactionType"} <= set(dir(pst))

    @pytest.mark.unit
    def test_handler_names(self):
        assert {
            "RequestHandler",
            "RequestConfig",
            "DirectRequestHandler",
            "UnflareRequestHandler",
            "UnflareConfig",
            "NodriverRequestHandler",
            "NodriverConfig",
        } <= set(handlers.__all__)

    @pytest.mark.unit
    def test_leagues(self):
        assert {league.name for league in pst.League} >= {
            "MLB",
            "MLS",
            "NBA",
            "NFL",
            "NHL",
        }

    @pytest.mark.unit
    def test_transaction_types(self):
        assert {t.name for t in pst.TransactionType} >= {
            "Disciplinary",
            "InjuredList",
            "Injury",
            "LegalIncident",
            "MinorLeagueToFrom",
            "Movement",
            "PersonalReason",
        }

    @pytest.mark.unit
    def test_search_methods(self):
        for method in ("get_dataframe", "get_dict", "get_json", "get_url"):
            assert inspect.iscoroutinefunction(getattr(pst.Search, method))

    @pytest.mark.unit
    def test_config_fields(self):
        assert {f.name for f in dataclasses.fields(NodriverConfig)} >= {
            "browser_executable_path",
            "headless",
            "sandbox",
            "verify_attempts",
            "solve_timeout",
            "browser_args",
        }
        assert {f.name for f in dataclasses.fields(UnflareConfig)} >= {
            "url",
            "timeout",
            "proxy",
        }

    @pytest.mark.unit
    @pytest.mark.usefixtures("fake_nodriver")
    @pytest.mark.parametrize(
        "handler_class",
        [DirectRequestHandler, UnflareRequestHandler, NodriverRequestHandler],
    )
    def test_every_handler_constructs_bare_and_supports_close(self, handler_class):
        """Switching handlers is a one-line change: each constructs with no
        arguments and supports close() and ``async with``."""
        handler = handler_class()

        assert isinstance(handler, RequestHandler)
        for method in ("close", "__aenter__", "__aexit__"):
            assert inspect.iscoroutinefunction(getattr(handler, method))

    @pytest.mark.unit
    @pytest.mark.usefixtures("fake_nodriver")
    @pytest.mark.parametrize(
        "handler_class", [UnflareRequestHandler, NodriverRequestHandler]
    )
    def test_bypass_handlers_expose_the_cache(self, handler_class):
        handler = handler_class()

        assert handler.is_cache_valid() is False
        assert handler.has_cached_cookies is False
        assert handler.cache_expiry_time == 0
        handler.cache_credentials([{"name": "cf_clearance", "value": "x"}], {})
        assert handler.is_cache_valid() is True
        handler.clear_cache()
        assert handler.is_cache_valid() is False


class PageHandler(RequestHandler):
    def __init__(self, page):
        self.page = page

    async def get(self, url, headers):
        return self.page


class TestReadmeResults:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_dataframe_columns_and_pages(self):
        page = (DATA_DIR / "valid_response.html").read_text(encoding="utf-8")
        search = pst.Search(request_handler=PageHandler(page))

        df = await search.get_dataframe()

        assert list(df.columns) == ["Date", "Team", "Acquired", "Relinquished", "Notes"]
        assert isinstance(df.attrs["pages"], int)
        assert "errors" not in df.attrs

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_failure_is_reported_in_errors_not_raised(self):
        search = pst.Search(request_handler=PageHandler(None))

        df = await search.get_dataframe()
        data = await search.get_dict()

        assert df.empty
        assert df.attrs["errors"]
        assert set(data) == {"transactions", "pages", "errors"}
        assert json.loads(await search.get_json())["errors"]
