Pro Sports Transactions API
===============

An API for Software Engineers, Data Scientists, and sports fans of all to over the world to easily pull transactional data from https://www.prosportstransactions.com/.

&nbsp;
# About
What is sports data without the transactions?
- "Did he just throw his mouthpiece into the stands?"
- "Yep."

`2023-01-27	| Warriors | • Stephen Curry | fined $25,000 by NBA for throwing his mouthpiece into the stands`
  
&nbsp;
# Getting Started
## Usage
```python
from datetime import date
import asyncio
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

# Define the corouting that will be called by our code
async def search_transactions() -> str:
    
    # How to Search for Transactions
    return await pst.Search(
        # Required
        league=league, 
        # Required (at least one)
        transaction_types=transaction_types,
        # Optional
        start_date=start_date, 
        # Optional
        end_date=end_date,
        # Optional
        player="LeBron James",
        # Optional
        team="Lakers",
        # Optional
        starting_row=starting_row,
    ).get_dataframe() # Supports get_dict(), and get_json()

# Example execution block
if __name__ == "__main__":
    df = asyncio.run(search_transactions())
```
## Results
```
# DataFrame
print(df)

# returns
          Date    Team        Acquired    Relinquished                                     Notes
0   2022-11-10  Lakers                  • LeBron James  placed on IL with strained left adductor
1   2022-11-25  Lakers  • LeBron James                                         activated from IL
2   2022-12-07  Lakers                  • LeBron James         placed on IL with sore left ankle
3   2022-12-09  Lakers  • LeBron James                                         activated from IL
4   2022-12-19  Lakers                  • LeBron James         placed on IL with sore left ankle
5   2022-12-21  Lakers  • LeBron James                                         activated from IL
6   2023-01-09  Lakers                  • LeBron James         placed on IL with sore left ankle
7   2023-01-12  Lakers  • LeBron James                                         activated from IL
8   2023-02-09  Lakers                  • LeBron James         placed on IL with sore left ankle
9   2023-02-15  Lakers  • LeBron James                                         activated from IL
10  2023-02-27  Lakers                  • LeBron James       placed on IL with right foot injury
11  2023-03-26  Lakers  • LeBron James                                         activated from IL

# Pages
print(df.attrs["pages])

# returns
1

```

# Requirements
Pro Sports Transactions presents data in an HTML table. To make retrieval easy, [`pandas.read_html`](https://pandas.pydata.org/docs/reference/api/pandas.read_html.html) is used which in turn results in additional depencies. The following are a list of required libraries: 
- python = "^3.11"
- aiohttp = "^3.8.4"
- pandas = "^2.0.0"
- brotli = "^1.0.9"
- lxml = "^4.9.2"
- html5lib = "^1.1"
- bs4 = "^0.0.1"

&nbsp;
# Thank You Frank Marousek!
Huge thanks to Frank Marousek @ Pro Sports Transactions for all of his efforts, and the efforts of those who have helped him, in compiling an excellent source of transactional information.
  
&nbsp;
# Disclaimer on accuracy, usage, and completeness of information.
The Pro Sports Transactions API is in no way affiliated with [Pro Sports Transactions](https://www.prosportstransactions.com/). The Pro Sports Transactions API provides a means for programatic access to [Pro Sports Transactions](https://www.prosportstransactions.com/). While the The Pro Sports Transactions API is open source under an MIT License, usage of all information obtained via the Pro Sports Transactions API is subject to all rights reserved by [Pro Sports Transactions](https://www.prosportstransactions.com/). No warranty, express or implied, is made regarding accuracy, adequacy, completeness, legality, reliability or usefulness of any information.

For questions, concerns, or other regarding the information provided via the Pro Sports Transaction API, please visit [Pro Sports Transactions](https://www.prosportstransactions.com/).