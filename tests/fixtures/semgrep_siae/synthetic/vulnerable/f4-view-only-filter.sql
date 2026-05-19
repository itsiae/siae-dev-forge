-- Reproduces PENTEST_REPORT 2026-05-18 F-04 pattern (soft-delete view-only).
-- NO real broadcasting code per ADR-004.

-- VULNERABLE: view filters CANCELLATO but underlying table has no RLS;
-- if app user has SELECT GRANT on table, the filter is trivially bypassed.

CREATE OR REPLACE VIEW dettaglio_canale_mensile_view AS
SELECT
  dcm.id_canale,
  dcm.anno_riferimento,
  dcm.mese_riferimento,
  dcm.importo
FROM dettaglio_canale_mensile dcm
WHERE EXISTS (
  SELECT 1 FROM report_logico rl
  WHERE rl.id_canale = dcm.id_canale
    AND EXTRACT(YEAR FROM rl.periodo_inizio) = dcm.anno_riferimento
    AND EXTRACT(MONTH FROM rl.periodo_inizio) = dcm.mese_riferimento
    AND rl.id_stato_report <> 6     -- 6 = CANCELLATO (soft-delete)
);

-- WHITESPACE VARIANT: tab/extra spaces around <> 6 should still match.
CREATE VIEW	v_dettaglio_giornaliero AS
SELECT *
FROM dettaglio_canale_giornaliero dcg
WHERE id_stato_report   <>    6;
