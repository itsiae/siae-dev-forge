---
name: siae-dev-analytics
description: Misura velocità e qualità degli sviluppatori SIAE che usano Claude Code + DevForge. Genera report Excel con 11 KPI (DORA + DX AI Measurement) + ROI Index. Trigger keywords, "misura produttività dev", "ROI Claude Code", "KPI sviluppatori", "analytics dev", "report performance team", "/forge-analytics", "dev metrics", "velocity quality report", "dashboard produttività", "cosa fanno gli sviluppatori", "benchmark dev", "ROI AI coding".
---

# siae-dev-analytics — Developer Analytics & ROI Report

> **Tipo:** Rigid | **Fase SDLC:** 5. Review/Metrics

## LA LEGGE DI FERRO

```
DATI NOMINATIVI SOLO DOPO CONFERMA ESPLICITA — CARD 🔴 ALTO OBBLIGATORIA
```

## Scopo

Analizza repository GitHub SIAE per calcolare KPI velocity + quality per sviluppatore, produce report Excel consumabile da management.

**AUTO-BEST mode:** la skill rileva automaticamente le fonti dati disponibili e tira il massimo:
- GitHub (sempre obbligatorio, ground truth)
- S3 telemetria DevForge (opzionale, se disponibile blend con costi Claude Code)
- Git trailers locali (se repo clonato)

## Flow

### Step 1 — Check ambiente

Run:
```bash
gh auth status 2>&1 | grep -q "Logged in" || echo "ABORT: gh not authenticated"
python3 --version | awk '{print $2}' | awk -F. '{if ($1 < 3 || $2 < 10) print "ABORT"}'
pip install -r skills/siae-dev-analytics/scripts/requirements.txt 2>&1 | tail -3
```

Se ABORT → mostra errore e ferma.

### Step 2 — Carica config

1. Cerca `devforge-analytics.yml` nella working directory
2. Se non esiste → prompt utente per scope minimo (repos + finestra)
3. Valida con Pydantic

### Step 3 — Autodetect sources

Run:
```bash
python3 skills/siae-dev-analytics/scripts/run_analytics.py autodetect --config <path>
```

Output atteso (JSON):
```json
{"github": true, "s3_devforge": false, "s3_blend": false, "mode": "GITHUB-ONLY"}
```

### Step 4 — Gate 🔴 ALTO privacy

Mostra card con N dev, N repo, finestra, mode. Richiedi conferma esplicita.

**Template card:**

| 🔴 ALTO (dati personali sviluppatori) — 🔨 DevForge · siae-dev-analytics |
|:---|
| **⚠️ OPERAZIONE CON DATI PERSONALI** |
| 👥 Dev coinvolti: `<N>` · 📅 Finestra: `<from → to>` · 📁 Repo: `<N>` · 🎯 Mode: `<FULL/HYBRID/GITHUB-ONLY>` |
| **▼ Azione** |
| 1. 📊 Fetch dati GitHub nominativi + calcolo KPI individuali |
| 2. 📤 Output Excel con tabelle per-dev |
| 💡 Perche': Valutazione ROI Claude Code + reportistica management |
| 🚫 Se NO: Abort. Nessun fetch, nessun file prodotto. |
| 🔒 Alternativa: rerun con `--anonymize` → hash SHA256 dei login |

Solo dopo conferma esplicita utente → procedi.

### Step 5 — Pipeline

Run:
```bash
python3 skills/siae-dev-analytics/scripts/run_analytics.py run --config <path> [--anonymize] [--format xlsx|csv|both]
```

### Step 6 — Report narrativo

Dopo produzione Excel, Claude genera markdown summary con:
- Top 3 dev per ROI Index
- Insight principali (es. "il team ha cycle time mediano 24h, in linea con DORA elite")
- Raccomandazioni management
- Path file Excel prodotto

## Trigger Keywords

- "misura produttività dev"
- "ROI Claude Code"
- "KPI sviluppatori"
- "analytics dev"
- "report performance team"
- "/forge-analytics"
- "dev metrics"
- "velocity quality report"
- "dashboard produttività"
- "cosa fanno gli sviluppatori"
- "benchmark dev"
- "ROI AI coding"

## Limiti Operativi

| Vincolo | Limite | Se superato |
|---------|--------|-------------|
| Repo max per run | 50 | Batch in più run |
| Dev max per run | 100 | Report diventa rumoroso |
| Finestra max | 365gg | Spezza in più run annuali |

## Anti-Pattern

| Pensiero | Realtà |
|----------|--------|
| "È solo un report, non serve card 🔴" | Dati nominativi = GDPR. Card sempre. |
| "LOC/giorno è una metrica valida" | Anti-pattern DORA. Non includerla mai. |
| "Self-reporting dev sarebbe utile" | Perception gap documentato (METR 2025). Solo metriche oggettive. |
| "Posso saltare autodetect, so cosa c'è" | L'ambiente cambia. Autodetect sempre. |

## Permission Denied Handling

- Se `pip install` negato → prompt card 🟡 MEDIO con alternative (venv, pipx, uv)
- Se `gh` non autenticato → ABORT con istruzioni `gh auth login`
- Se S3 creds mancanti → graceful degrade GITHUB-ONLY, noted in report
