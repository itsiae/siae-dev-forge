# Piano — Installer network resilience (github su rete SIAE)

**Design:** [../2026-06-13-installer-network-resilience-design.md](../2026-06-13-installer-network-resilience-design.md)
**Branch:** `fix/installer-network-resilience` (da `main`)
**Tema:** estende network resilience github di PR #318 al path install/recovery.

## Goal
`install.sh` (e README) resilienti alla rete SIAE: niente più fallimenti SSH
(shorthand github→SSH bloccato) né hang sul proxy corporate off-VPN, su prima
installazione e recovery da cache-miss.

## Criteri di accettazione (dal design)
1. Dev fresco off-VPN completa `install.sh` senza hang SSH/proxy.
2. Recovery `claude plugin marketplace update siae-devforge` clona HTTPS direct.
3. On-VPN invariato (nessuna regressione).
4. `setup_github_network` idempotente; side-effect git globale annunciato.
5. README allineato (no comandi che assumono SSH/proxy raggiungibile) + rollback.

## Task

| # | Task | Stato |
|---|------|-------|
| 01 | Test strutturale `setup_github_network` (TDD red) | [PENDING] |
| 02 | Implementa `setup_github_network()` + call site in install.sh (green) | [PENDING] |
| 03 | README: nota rete SIAE + rollback nella sezione Installazione | [PENDING] |

## Note esecuzione
- TDD: Task 01 prima (test fallisce), Task 02 fa passare.
- Verifica empirica della meccanica già fatta in sessione (clone HTTPS direct 3s
  sotto proxy morto; recovery OK post git-config) — i test qui sono strutturali.
