# /forge-analytics

Invoca la skill `siae-dev-analytics` per generare report ROI degli sviluppatori SIAE che usano Claude Code + DevForge.

## Uso

```
/forge-analytics [--config <path>] [--anonymize] [--format xlsx|csv|both]
```

## Parametri

- `--config`: path al file YAML di configurazione (default: `./devforge-analytics.yml`)
- `--anonymize`: hash SHA256 dei login → report esterni
- `--format`: formato output (default: xlsx)

## Flow

1. Check `gh auth` + Python deps
2. Carica config YAML (o prompt interattivo)
3. Autodetect fonti (GitHub + S3 telemetry opzionale)
4. Gate 🔴 ALTO privacy — conferma esplicita
5. Fetch + compute + export
6. Narrativa markdown finale

## Esempi

```
/forge-analytics --config devforge-analytics.yml
/forge-analytics --anonymize --format both
```

## Quando usarlo

- Quarterly review ROI Claude Code
- Report trimestrale per management (carlo.stoppani)
- Benchmark team dopo introduzione nuova skill DevForge
- Identificazione top/bottom performer per coaching

## Permission denied

- `pip install` negato → prompt card 🟡 con alternative (venv, pipx, uv)
- `gh` non autenticato → abort con istruzioni `gh auth login`
- AWS S3 creds mancanti → graceful degrade GITHUB-ONLY

## Skill referenziata

`skills/siae-dev-analytics/`
