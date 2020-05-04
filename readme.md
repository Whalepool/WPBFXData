
## Data Fetcher, `fetch_lvs.py`
Recommended: 15m scheduled running to fetch data

Fetches 
- Get ticker data
- Get funding data
- Get long /short data for each ticker
- Get long /short funding data for each ticker

Saves
- Save to mongo db 

`fetch_lvs.py`
| Arg | Required | Type | Desc |
| ------ | ------ | ------ | ------ |
| -t | NO | A,B,C list | Defaults to top tickers[X] set in config or supplied -t arg tickers |

**Example usage**
```bash
python fetch_lvs.py
python fetch_lvs.py -t ETHUSD BTCUSD 
```
