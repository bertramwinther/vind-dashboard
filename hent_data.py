import requests
import sqlite3
import pandas as pd

url = "https://api.energidataservice.dk/dataset/ProductionConsumptionSettlement"
params = {"start": "2026-10-01", "end": "2026-11-01", "limit": 0}

response = requests.get(url, params=params)

if response.status_code != 200:
    print("Fejl fra API:", response.status_code, response.text)
    exit()

data = response.json()
df = pd.DataFrame(data["records"])

print(df.columns)
print(df.head())

conn = sqlite3.connect("vind.db")
df.to_sql("produktion", conn, if_exists="replace", index=False)
print(f"Gemt {len(df)} rækker")