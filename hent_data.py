"""Henter afregnede tal fra Energi Data Service og gemmer dem i vind.db."""

import os
import sqlite3
from contextlib import closing
from pathlib import Path

import pandas as pd
import requests

URL = "https://api.energidataservice.dk/dataset/ProductionConsumptionSettlement"
START = "2026-10-01"
DB_FIL = Path(__file__).parent / "vind.db"


def hent_afregnede_tal():
    """Henter alle tal fra START og frem. Giver en fejl, hvis det ikke lykkes."""
    svar = requests.get(URL, params={"start": START, "limit": 0}, timeout=60)
    svar.raise_for_status()
    raekker = svar.json()["records"]
    if not raekker:
        raise ValueError("API'et sendte ingen rækker")
    return pd.DataFrame(raekker)


def opdater_database():
    """Gemmer tallene i en midlertidig fil og skifter først til den, når alt er gået godt."""
    df = hent_afregnede_tal()
    midlertidig = DB_FIL.with_name(DB_FIL.name + ".tmp")
    try:
        with closing(sqlite3.connect(midlertidig)) as conn:
            df.to_sql("produktion", conn, if_exists="replace", index=False)
        os.replace(midlertidig, DB_FIL)
    finally:
        midlertidig.unlink(missing_ok=True)
    return len(df)


if __name__ == "__main__":
    try:
        print(f"Gemt {opdater_database()} rækker i {DB_FIL.name}")
    except requests.RequestException as fejl:
        print("Fejl fra API:", fejl)
