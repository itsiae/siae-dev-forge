# Dump Acquisition — Fallback Chain

Acquisizione dump UI per identificare locatori.
Usa questa procedura SOLO dopo aver esaurito file esistenti, dump esistenti e inferenza dal contesto.

---

## Environment Detection — esegui sempre prima di acquisire

```
CHECK 1: adb devices
  → output contiene device/emulator connesso?
  → SÌ: canale ADB disponibile

CHECK 2: appium-mcp disponibile?
  → server Appium in ascolto + sessione aperta sulla pagina corretta?
  → SÌ: canale appium-mcp disponibile

CHECK 3: variabili BS_USERNAME e BS_ACCESS_KEY presenti?
  → SÌ: canale BrowserStack disponibile
```

Dichiara sempre il risultato:
```
ENV DETECTION: ADB=sì | appium-mcp=no | BrowserStack=sì
Canale selezionato: ADB (preferenza 1°)
```

---

## Fallback Chain

### 1° ADB (preferito)

```bash
adb shell uiautomator dump /sdcard/dump.xml
adb pull /sdcard/dump.xml tests/dumps/<PageName>Dump.xml
```

**Prerequisiti:** device/emulatore connesso via USB o TCP
**Vantaggi:** veloce, offline, dump completo, nessuna sessione necessaria

---

### 2° appium-mcp

Metodo: `get_page_source` sulla sessione Appium attiva
Salva in: `tests/dumps/<PageName>Dump.xml`

**Prerequisiti:** server Appium running, sessione attiva sulla pagina corretta
**Vantaggi:** sessione già aperta, nessun device fisico necessario

---

### 3° BrowserStack

| 🔴 ALTO (sessione BS a consumo) — 🔨 DevForge · siae-robot-framework |
|:---|
| ⚠️ WARNING — questa operazione crea una sessione BrowserStack (consumo minuti) |
| 🔑 BS_USERNAME: `${BS_USERNAME}` · 🔑 BS_ACCESS_KEY: `[configurata]` |
| 📱 Piattaforma target: `Android / iOS` |
| **▼ Azione** |
| 1. 🌐 Avvia sessione BS, naviga alla pagina, esegui `get_page_source` |
| 2. 💾 Salva in `tests/dumps/BS/<PageName>Dump.xml` (Android) o `tests/dumps/BS_iOS/<PageName>Dump.xml` (iOS) |
| 💡 Perche': ADB e appium-mcp non disponibili — BS è l'unico canale |
| 🚫 Se NO: nessun dump acquisito. Dichiara BLOCCO ACQUISIZIONE DUMP. |

---

### BLOCCO ACQUISIZIONE DUMP

Se nessun canale è disponibile, dichiara:

```
BLOCCO ACQUISIZIONE DUMP: nessun canale disponibile.
Manca:
  ADB: device non connesso (verifica `adb devices`)
  appium-mcp: nessuna sessione Appium attiva
  BrowserStack: BS_USERNAME / BS_ACCESS_KEY non configurate
Per sbloccare: [azione specifica richiesta — es. connetti device, avvia Appium, configura credenziali BS]
```

**Non produrre file con locatori inventati.**

---

## Metadati dump (obbligatori)

Ogni dump salvato deve avere un file `<PageName>Dump.meta.json` nella stessa directory:

```json
{
  "page": "LoginPage",
  "platform": "android",
  "channel": "adb",
  "app_version": "1.2.3",
  "acquired_at": "2025-01-15T10:30:00",
  "device": "emulator-5554"
}
```

Questo è necessario perché dump Android e iOS hanno strutture xpath diverse.
Un dump Android non può essere usato per derivare locatori iOS.
