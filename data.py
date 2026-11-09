"""Henter live-tal fra Energi Data Service uden at overskride rate limits."""

import threading
import time

import requests
import streamlit as st

API_URL = "https://api.energidataservice.dk/dataset/"

# Hvor ofte hver kilde må hentes, styres af "interval" (sekunder).
KILDER = {
    "hele_dk": {
        "datasaet": "PowerSystemRightNow",
        "sorter": "Minutes1UTC DESC",
        "offset": "-PT10M",
        "interval": 60,
    },
    "omraader": {
        "datasaet": "ElectricityProdex5MinRealtime",
        "sorter": "Minutes5UTC DESC",
        "offset": "-PT15M",
        "interval": 300,
    },
}


@st.cache_resource
def _lager():
    """Fælles hukommelse for alle besøgende, så ti besøgende ikke giver ti kald."""
    return {
        navn: {"lock": threading.Lock(), "raekker": None, "hentet": None, "fejl": None, "naeste_kald": 0}
        for navn in KILDER
    }


def _hent_fra_api(kilde):
    """Laver selve kaldet. Returnerer (rækker, fejl, sekunder til næste kald)."""
    try:
        svar = requests.get(
            API_URL + kilde["datasaet"],
            params={"start": "now", "startOffset": kilde["offset"], "sort": kilde["sorter"]},
            timeout=15,
        )
    except requests.RequestException:
        return None, "Kunne ikke kontakte Energi Data Service", kilde["interval"]

    if svar.status_code == 429:
        # API'et fortæller selv, hvor længe vi skal vente.
        try:
            vent = int(svar.headers.get("Retry-After", kilde["interval"]))
        except ValueError:
            vent = kilde["interval"]
        return None, "For mange kald lige nu (rate limit)", max(vent, 1)

    if svar.status_code != 200:
        return None, f"API-fejl {svar.status_code}", kilde["interval"]

    try:
        raekker = svar.json()["records"]
    except (ValueError, KeyError):
        return None, "API'et sendte et svar, der ikke kunne læses", kilde["interval"]

    if not raekker:
        return None, "API'et sendte ingen nye tal", kilde["interval"]

    return raekker, None, kilde["interval"]


def _hent(navn):
    """Henter kun, hvis det er tid til det. Ellers bruges de seneste gode tal."""
    plads = _lager()[navn]
    with plads["lock"]:  # Kun én besøgende ad gangen må lave kaldet.
        if time.time() >= plads["naeste_kald"]:
            raekker, fejl, vent = _hent_fra_api(KILDER[navn])
            plads["naeste_kald"] = time.time() + vent
            plads["fejl"] = fejl
            if raekker is not None:
                plads["raekker"] = raekker
                plads["hentet"] = time.time()
        return {"raekker": plads["raekker"], "hentet": plads["hentet"], "fejl": plads["fejl"]}


def seneste_hele_dk():
    """Nyeste minut for hele Danmark. "raekke" er None, hvis vi endnu intet har."""
    svar = _hent("hele_dk")
    raekke = svar["raekker"][0] if svar["raekker"] else None
    return {"raekke": raekke, "hentet": svar["hentet"], "fejl": svar["fejl"]}


def seneste_omraade(omraade):
    """Nyeste 5 minutter for "DK1" eller "DK2"."""
    svar = _hent("omraader")
    raekke = None
    for r in svar["raekker"] or []:
        if r["PriceArea"] == omraade:
            raekke = r  # Rækkerne er sorteret med nyeste først.
            break
    return {"raekke": raekke, "hentet": svar["hentet"], "fejl": svar["fejl"]}


def tal(raekke, kolonne):
    """Som COALESCE(kolonne, 0) i SQL: en tom værdi tæller som 0."""
    return raekke[kolonne] or 0


def vind(raekke):
    """Vind i MW. Kolonnerne hedder det samme i begge datasæt."""
    return tal(raekke, "OffshoreWindPower") + tal(raekke, "OnshoreWindPower")


# ---------------------------------------------------------------------------
# Forbrug = produktion + import. Datasættene har ikke forbruget som kolonne.
# Kør `python data.py` for at tjekke formlerne.
# ---------------------------------------------------------------------------

def forbrug_hele_dk(raekke):
    """Beregnet forbrug i MW for hele Danmark (PowerSystemRightNow).

    Læg sammen: ProductionGe100MW, ProductionLt100MW, OffshoreWindPower,
    OnshoreWindPower, SolarPower og Exchange_Sum.
    Træk fra: Exchange_Bornholm_SE.
    """
    return (
        tal(raekke, "ProductionGe100MW")
        + tal(raekke, "ProductionLt100MW")
        + tal(raekke, "OffshoreWindPower")
        + tal(raekke, "OnshoreWindPower")
        + tal(raekke, "SolarPower")
        + tal(raekke, "Exchange_Sum")
        - tal(raekke, "Exchange_Bornholm_SE")
    )

def forbrug_omraade(raekke):
    """Beregnet forbrug i MW for DK1 eller DK2 (ElectricityProdex5MinRealtime).

    Læg sammen: ProductionLt100MW, ProductionGe100MW, OffshoreWindPower,
    OnshoreWindPower, SolarPower, ExchangeGreatBelt, ExchangeGermany,
    ExchangeNetherlands, ExchangeGreatBritain, ExchangeNorway og ExchangeSweden.
    BornholmSE4 skal ikke med.
    """
    return (
        tal(raekke, "ProductionLt100MW")
        + tal(raekke, "ProductionGe100MW")
        + tal(raekke, "OffshoreWindPower")
        + tal(raekke, "OnshoreWindPower")
        + tal(raekke, "SolarPower")
        + tal(raekke, "ExchangeGreatBelt")
        + tal(raekke, "ExchangeGermany")
        + tal(raekke, "ExchangeNetherlands")
        + tal(raekke, "ExchangeGreatBritain")
        + tal(raekke, "ExchangeNorway")
        + tal(raekke, "ExchangeSweden")
    )


def tjek_formler():
    """Tester formlerne på faste tal fra API'et, hvor resultatet er kendt."""
    hele_dk = {
        "ProductionGe100MW": 1041.939941, "ProductionLt100MW": 764.909973,
        "OffshoreWindPower": 657.159973, "OnshoreWindPower": 239.690002,
        "SolarPower": 55.52, "Exchange_Sum": 2208.379883,
        "Exchange_Bornholm_SE": 21.66,
    }
    dk2 = {
        "ProductionLt100MW": 307.679993, "ProductionGe100MW": 734.059998,
        "OffshoreWindPower": 24.15, "OnshoreWindPower": 15.03, "SolarPower": 28.110001,
        "ExchangeGreatBelt": 253.5, "ExchangeGermany": 600.02002,
        "ExchangeNetherlands": None, "ExchangeGreatBritain": None,
        "ExchangeNorway": None, "ExchangeSweden": -93.169998, "BornholmSE4": 22.139999,
    }
    tests = [
        ("Hele DK", forbrug_hele_dk, hele_dk, 4945.94),
        ("DK2", forbrug_omraade, dk2, 1869.38),
    ]
    for navn, formel, raekke, forventet in tests:
        resultat = formel(raekke)
        status = "OK" if abs(resultat - forventet) < 0.01 else "FORKERT"
        print(f"{status}  {navn}: fik {resultat:.2f} MW, forventede {forventet} MW")


if __name__ == "__main__":
    tjek_formler()
