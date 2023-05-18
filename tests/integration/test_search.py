from datetime import date
from pro_sports_transactions.search import Search, League, TransactionType
import pytest


@pytest.mark.asyncio
async def test_search_unicode():
    transaction_types = tuple([t for t in TransactionType])
    start_date = date.fromisoformat("2000-01-05")
    end_date = date.fromisoformat("2005-04-05")

    actual = await Search(
        league=League.NBA,
        transaction_types=transaction_types,
        start_date=start_date,
        end_date=end_date,
        player="O'Neal",
        team="Pacers",
        starting_row=25,
    ).get_json()

    expected = (
        '{"transactions": [{"Date": "2004-12-23", "Team": "Pacers", '
        '"Acquired": "\\u2022 Jermaine O\'Neal", "Relinquished": ""'
        ', "Notes": "reinstated from suspension"}, {"Date": "2005-03-04", '
        '"Team": "Pacers", "Acquired": "", "Relinquished": '
        '"\\u2022 Jermaine O\'Neal", "Notes": "placed on IL '
        'with sprained right shoulder"}], "pages": 2}'
    )

    assert actual == expected


@pytest.mark.asyncio
async def test_search_readme_md_example():
    from datetime import date
    import pro_sports_transactions as pst

    # League (MLB, MLS, NBA, NFL, and NHL)
    league = pst.League.NBA

    # Disciplinary Actions, Injured List, Injuries,
    # Legal Incidents, Minor League To/For, Personal Reasons,
    # and General (e.g., Trades, Acquisitions, Waivers, Draft Picks, etc.)
    transaction_types = tuple([t for t in pst.TransactionType])

    # From the start of the 2022-23 NBA Regular Season
    start_date = date.fromisoformat("2022-10-18")

    # From the end of the 2022-23 NBA Regular Season
    end_date = date.fromisoformat("2023-04-09")

    # Pro Sports Transactions provides 25 rows (one page) at a time.
    # The first row of the first page is always 0, and ends with 24.
    # The first row of the second page is always 25, and ends with 49.
    # Note: If the starting_row is set to 9; the 10th row of the results,
    # then the last row of the first page wil be 34 (9 + 25)..
    starting_row = 0

    # How to Search
    actual = await pst.Search(
        league=league,
        transaction_types=transaction_types,
        start_date=start_date,
        end_date=end_date,
        player="LeBron James",
        team="Lakers",
        starting_row=starting_row,
    ).get_json()

    expected = (
        '{"transactions": [{"Date": "2022-11-10", "Team": "Lakers", "Acquired": "", '
        '"Relinquished": "\\u2022 LeBron James", "Notes": "placed on IL with strained '
        'left adductor"}, {"Date": "2022-11-25", "Team": "Lakers", "Acquired": '
        '"\\u2022 LeBron James", "Relinquished": "", "Notes": "activated from IL"}, '
        '{"Date": "2022-12-07", "Team": "Lakers", "Acquired": "", "Relinquished": '
        '"\\u2022 LeBron James", "Notes": "placed on IL with sore left ankle"}, '
        '{"Date": "2022-12-09", "Team": "Lakers", "Acquired": "\\u2022 LeBron James", '
        '"Relinquished": "", "Notes": "activated from IL"}, {"Date": "2022-12-19", '
        '"Team": "Lakers", "Acquired": "", "Relinquished": "\\u2022 LeBron James", '
        '"Notes": "placed on IL with sore left ankle"}, {"Date": "2022-12-21", '
        '"Team": "Lakers", "Acquired": "\\u2022 LeBron James", "Relinquished": '
        '"", "Notes": "activated from IL"}, {"Date": "2023-01-09", "Team": '
        '"Lakers", "Acquired": "", "Relinquished": "\\u2022 LeBron James", '
        '"Notes": "placed on IL with sore left ankle"}, {"Date": "2023-01-12", '
        '"Team": "Lakers", "Acquired": "\\u2022 LeBron James", "Relinquished": '
        '"", "Notes": "activated from IL"}, {"Date": "2023-02-09", "Team": '
        '"Lakers", "Acquired": "", "Relinquished": "\\u2022 LeBron James", "Notes": '
        '"placed on IL with sore left ankle"}, {"Date": "2023-02-15", "Team": '
        '"Lakers", "Acquired": "\\u2022 LeBron James", "Relinquished": "", '
        '"Notes": "activated from IL"}, {"Date": "2023-02-27", "Team": "Lakers", '
        '"Acquired": "", "Relinquished": "\\u2022 LeBron James", "Notes": '
        '"placed on IL with right foot injury"}, {"Date": "2023-03-26", "Team": '
        '"Lakers", "Acquired": "\\u2022 LeBron James", "Relinquished": "", '
        '"Notes": "activated from IL"}], "pages": 1}'
    )

    assert actual == expected
