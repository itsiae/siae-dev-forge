-- SAFE: Postgres RLS policy enforces filter at table level — no view-only bypass.

ALTER TABLE dettaglio_canale_mensile ENABLE ROW LEVEL SECURITY;

CREATE POLICY hide_cancelled ON dettaglio_canale_mensile
  USING (EXISTS (
    SELECT 1 FROM report_logico rl
    WHERE rl.id_canale = dettaglio_canale_mensile.id_canale
      AND rl.id_stato_report <> 6
  ));

-- View is now optional convenience; bypass via direct SELECT is also filtered.
CREATE OR REPLACE VIEW dettaglio_canale_mensile_view AS
SELECT * FROM dettaglio_canale_mensile;
