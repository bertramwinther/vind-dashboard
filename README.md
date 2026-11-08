# Danish Wind Power Dashboard

Henter timedata for dansk elproduktion fra Energinet, gemmer det i SQLite
og analyserer vindproduktionen.

## Kom i gang
1. `pip install requests pandas`
2. `python hent_data.py` henter data for oktober 2026 og gemmer dem i `vind.db`
3. Åbn `vind.db` i f.eks. DB Browser for SQLite og kør forespørgslerne i `analyse.sql`

## Fund (oktober 2026)
- De tre blæsende dage var 25.-27. oktober. Den 26. oktober var højest med ca. 130.000 MWh.
- Den 31. oktober er kun delvist med, fordi Energinet først udsender data efter ca. 8 dage. Dagen er udeladt fra analyserne.
- Den 25. oktober har 25 timer på grund af skiftet til vintertid, så analysen regner også gennemsnit pr. time.

## Planlagt
- Dashboard med grafer (Streamlit)
- Automatisk opdatering af data
- Mulighed for at stille spørgsmål til dataene med AI

## Datakilde
Kilde: Energinet (www.energidataservice.dk)
