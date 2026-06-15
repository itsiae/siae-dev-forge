# Task 03 — README: nota rete SIAE + rollback

**Goal:** allineare la doc d'installazione: il comando manuale `/plugin marketplace
add itsiae/siae-dev-forge` (README riga ~63) assume SSH/proxy raggiungibile e
fallisce su rete SIAE; documentare l'uso di `install.sh` + il rollback della
config git globale.

## File
- Modifica: `README.md` (sezione "Installazione", righe ~57-75)

## Contenuto da aggiungere
Dopo il blocco che mostra `/plugin marketplace add itsiae/siae-dev-forge`
(riga ~63), aggiungere una nota:

```markdown
> **Rete SIAE:** il comando `/plugin marketplace add` sopra usa SSH (bloccato
> dalla rete SIAE) e instrada sul proxy corporate (irraggiungibile fuori VPN).
> Su macchina SIAE usa invece lo script di installazione, che configura
> `github` in DIRECT (NO_PROXY + SSH→HTTPS) prima di registrare il marketplace:
>
> ```bash
> bash <(gh api repos/itsiae/siae-dev-forge/contents/install.sh -q .content | base64 -d)
> ```
>
> Lo stesso vale per il **recovery** da cache-miss
> (`claude plugin marketplace update siae-devforge`): rieseguire `install.sh`.
>
> **Rollback** della config git globale impostata dall'installer:
> ```bash
> git config --global --unset url."https://github.com/".insteadOf
> git config --global --unset http."https://github.com/".proxy
> ```
```

## Vincolo
- NON toccare README riga ~160 (è la tabella skill, non un comando installazione).
- Il comando `gh api ... base64 -d` è quello già presente in `install.sh` riga ~160
  (sezione "Per aggiornare in futuro").

## Done quando
- README contiene la nota "Rete SIAE" + i 2 comandi `--unset` di rollback.
- Nessuna modifica a righe non pertinenti.
