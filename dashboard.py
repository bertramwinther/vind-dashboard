import sqlite3
from datetime import date

import pandas as pd
import streamlit as st

import data

st.set_page_config(page_title="Dansk vindkraft")
st.title("Dansk vindkraft")

omraade = st.radio("Område", ["Hele DK", "DK1", "DK2"], horizontal=True)


def dansk_tal(vaerdi, decimaler=0):
    """Viser 1234.5 som 1.234,5."""
    tekst = f"{vaerdi:,.{decimaler}f}"
    return tekst.replace(",", "X").replace(".", ",").replace("X", ".")


# run_every gentager kun denne del af siden, ikke hele siden.
@st.fragment(run_every="60s")
def vis_live(omraade):
    if omraade == "Hele DK":
        svar = data.seneste_hele_dk()
        beregn_forbrug = data.forbrug_hele_dk
        tid_kolonne = "Minutes1DK"
        opdateres = "hvert minut"
    else:
        svar = data.seneste_omraade(omraade)
        beregn_forbrug = data.forbrug_omraade
        tid_kolonne = "Minutes5DK"
        opdateres = "hvert 5. minut"

    raekke = svar["raekke"]
    if raekke is None:
        st.warning(f"Ingen live-tal lige nu. {svar['fejl'] or ''}")
        return

    vind = data.vind(raekke)
    forbrug = beregn_forbrug(raekke)
    andel = dansk_tal(vind / forbrug * 100, 1) + " %" if forbrug > 0 else "–"

    kol1, kol2, kol3 = st.columns(3)
    kol1.metric("Vind lige nu", dansk_tal(vind) + " MW")
    kol2.metric("Vindens andel af forbruget", andel)
    kol3.metric("Beregnet forbrug", dansk_tal(forbrug) + " MW")

    tidspunkt = pd.Timestamp(raekke[tid_kolonne]).strftime("%d/%m/%Y kl. %H:%M")
    st.caption(
        f"Foreløbige tal fra {tidspunkt}, opdateres {opdateres}. "
        "Forbruget er beregnet som produktion + import. "
        "Andelen kan komme over 100 %, når vi producerer mere vind, end vi bruger."
    )
    if svar["fejl"]:
        st.warning(f"Viser de seneste gode tal. {svar['fejl']}.")


vis_live(omraade)

st.subheader("Vind pr. dag")
st.caption("Afregnede tal. De kommer ca. 9 dage efter, så de nyeste dage mangler.")

conn = sqlite3.connect("vind.db")

# En hel dag har mindst 23 timer (23 ved sommertid, 25 ved vintertid).
HELE_DAGE = "HAVING COUNT(DISTINCT HourUTC) >= 23"

foerste, sidste = conn.execute(f"""
    SELECT MIN(dag), MAX(dag)
    FROM (SELECT date(HourDK) AS dag FROM produktion GROUP BY dag {HELE_DAGE})
""").fetchone()
foerste, sidste = date.fromisoformat(foerste), date.fromisoformat(sidste)

valgt = st.date_input(
    "Periode",
    value=(foerste, sidste),
    min_value=foerste,
    max_value=sidste,
    format="DD/MM/YYYY",
)
if len(valgt) != 2:
    st.info("Vælg både en start- og en slutdato.")
    st.stop()
fra, til = valgt

# :fra, :til og :omraade er de valg, brugeren har lavet på siden.
query = f"""
SELECT date(HourDK) AS dag,
  SUM(
    COALESCE(OffshoreWindLt100MW_MWh, 0) +
    COALESCE(OffshoreWindGe100MW_MWh, 0) +
    COALESCE(OnshoreWindLt50kW_MWh, 0) +
    COALESCE(OnshoreWindGe50kW_MWh, 0)
  ) AS vind_mwh
FROM produktion
WHERE date(HourDK) BETWEEN :fra AND :til
  AND (:omraade = 'Hele DK' OR PriceArea = :omraade)
GROUP BY dag
{HELE_DAGE}
ORDER BY dag
"""

df = pd.read_sql(
    query,
    conn,
    params={"fra": fra.isoformat(), "til": til.isoformat(), "omraade": omraade},
)
conn.close()

if df.empty:
    st.info("Der er ingen hele dage i den valgte periode.")
    st.stop()

df["dag"] = pd.to_datetime(df["dag"])
st.line_chart(df, x="dag", y="vind_mwh", x_label="Dato", y_label="Vind (MWh pr. dag)")
st.dataframe(
    df,
    hide_index=True,
    column_config={
        "dag": st.column_config.DateColumn("Dato", format="DD/MM/YYYY"),
        "vind_mwh": st.column_config.NumberColumn("Vind (MWh)", format="%.0f"),
    },
)

st.caption("Kilde: Energinet (energidataservice.dk), licens CC BY 4.0.")
