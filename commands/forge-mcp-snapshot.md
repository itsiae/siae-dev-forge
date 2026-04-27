---
name: forge-mcp-snapshot
description: Genera uno snapshot della topologia MCP sport-kg in memory locale (~/.claude/projects/<project>/memory/sport_kg_topology_snapshot.md). On-demand, non automatico. Usato per protezione context window in sessioni successive — Claude legge lo snapshot invece di fare list_services full-dump (50KB+) ogni volta. TTL pratico 24h: ri-eseguire quando il KG e' stato re-indicizzato.
---

# /forge-mcp-snapshot

Genera uno snapshot compatto della topologia MCP `sport-kg` e lo salva in memory.
On-demand, non automatico. Sostituisce le query `list_services()` ripetute in sessioni
successive con una lettura diretta del file.

## Utilizzo

```
/forge-mcp-snapshot
```

## Prerequisiti

- MCP server `sport-kg` connesso.

## Comportamento

1. Chiama `mcp__sport-kg__list_services()` (full-dump, no filter — bug noto: filter case-sensitive).
2. Chiama `mcp__sport-kg__graph_stats` per metadata sul KG.
3. Aggrega in formato compatto (1 riga per servizio: nome, prefisso cluster, last_indexed).
4. Scrive su `~/.claude/projects/<project>/memory/sport_kg_topology_snapshot.md` con frontmatter type=reference + timestamp generazione.
5. Aggiorna `MEMORY.md` index se non gia' presente.

## Output

File `sport_kg_topology_snapshot.md` con struttura:

```markdown
---
name: MCP sport-kg topology snapshot
description: Snapshot compatto dei N servizi indicizzati nel KG sport-kg, generato il YYYY-MM-DD HH:MM
type: reference
generated_at: 2026-04-27T14:30:00Z
ttl_hours: 24
---

# Topologia sport-kg — N servizi (snapshot YYYY-MM-DD)

## Cluster sport-*-service (K servizi)
- sport-accentramenti-service (last_indexed: ...)
- sport-accertamenti-adm-service (last_indexed: ...)
...

## Cluster pop-*-service (K servizi)
- pop-be (...)
- pop-pagamenti-service (...)
...

[etc per ogni prefisso]

## Note
- Stale dopo 24h: ri-eseguire `/forge-mcp-snapshot` se il KG e' stato re-indicizzato.
- Per disambiguare classi/metodi (manca tool `find_service_for_symbol`): grep nel snapshot per match prefisso.
```

## Quando usarlo

- All'inizio di una nuova sessione su task sport — riduce context da 50KB list_services full a 2-3KB.
- Dopo re-indicizzazione del KG (annuncio team o cambio significativo nei repo).

## Quando NON usarlo

- MCP non disponibile (Docker giu', VPN giu'): comando fallisce esplicitamente con istruzioni recovery.
- Snapshot fresco (<24h dal generated_at): no-op con messaggio "snapshot ancora valido".

## Note

- Lo snapshot NON sostituisce `mcp-impact-analyst` per pre-flight: e' una cache di topologia, non di impatto.
- `service_full_context`, `demand_impact`, `service_health` ritornano dati ES live e NON vanno cachati (cambiano ogni 24h).
- Il file e' in memory (`type: reference`): viene letto da Claude on-demand, non iniettato sempre.
