-- Check if the eszkozok_osszesen and forrasok_osszesen has any difference.
SELECT
	BESZAMOLOK.et_ev,
	ADATOK.eszkozok_osszesen,
	ADATOK.forrasok_osszesen,
	(ADATOK.eszkozok_osszesen - ADATOK.forrasok_osszesen) AS eszkozok_forrasok_DIFF
FROM
	02773_research.beszamolo_adatok ADATOK 
    INNER JOIN 02773_research.beszamolok BESZAMOLOK
		ON ADATOK.beszamolo_id = BESZAMOLOK.id
;