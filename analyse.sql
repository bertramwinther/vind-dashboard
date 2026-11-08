-- Tjek: hvor mange rækker er der pr. dag? (en hel dag har 48, vintertidsdagen 50)
SELECT date(HourDK) AS dag, COUNT(*) AS raekker
FROM produktion
GROUP BY dag
ORDER BY raekker ASC;

-- De 5 dage med mest vind i alt (kun hele dage)
SELECT date(HourDK) AS dag,
  ROUND(SUM(
    COALESCE(OffshoreWindLt100MW_MWh, 0) +
    COALESCE(OffshoreWindGe100MW_MWh, 0) +
    COALESCE(OnshoreWindLt50kW_MWh, 0) +
    COALESCE(OnshoreWindGe50kW_MWh, 0)
  )) AS vind_mwh
FROM produktion
GROUP BY dag
HAVING COUNT(*) >= 48
ORDER BY vind_mwh DESC
LIMIT 5;

-- Gennemsnitlig vind pr. time (retter for den ekstra time ved vintertid)
SELECT date(HourDK) AS dag,
  ROUND(SUM(
    COALESCE(OffshoreWindLt100MW_MWh, 0) +
    COALESCE(OffshoreWindGe100MW_MWh, 0) +
    COALESCE(OnshoreWindLt50kW_MWh, 0) +
    COALESCE(OnshoreWindGe50kW_MWh, 0)
  ) / COUNT(DISTINCT HourUTC)) AS gennemsnit_pr_time
FROM produktion
GROUP BY dag
HAVING COUNT(*) >= 48
ORDER BY gennemsnit_pr_time DESC
LIMIT 5;