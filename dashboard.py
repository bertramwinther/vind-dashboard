import sqlite3
import pandas as pd
import streamlit as st

st.title("Dansk vindproduktion, oktober 2026")

conn = sqlite3.connect("vind.db")

query = """
SELECT date(HourDK) AS dag,
  SUM(
    COALESCE(OffshoreWindLt100MW_MWh, 0) +
    COALESCE(OffshoreWindGe100MW_MWh, 0) +
    COALESCE(OnshoreWindLt50kW_MWh, 0) +
    COALESCE(OnshoreWindGe50kW_MWh, 0)
  ) AS vind_mwh
FROM produktion
GROUP BY dag
HAVING COUNT(*) >= 48
ORDER BY dag
"""

df = pd.read_sql(query, conn)
st.line_chart(df, x="dag", y="vind_mwh")
st.dataframe(df)