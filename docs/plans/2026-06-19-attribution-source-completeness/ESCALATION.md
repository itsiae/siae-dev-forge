# Attribution — Gap non-code (escalation)

**Data:** 2026-06-19 · **Contesto:** verifica empirica R1–R7 su S3 `siae-devforge-telemetry`.

Questi gap **non si chiudono con codice DevForge**. Tracciati per decisione di processo/org.
Il fix di codice (design.md, metodi A+B) li *misura* e *mitiga*, non li elimina alla radice.

## E1 — Adozione versione plugin (gap 2)

- **Evidenza**: copertura `auth_email` 0% (day04, plugin <1.84) → 79% → 87% (1.91/1.92).
  Il pinning esiste solo dalle versioni recenti; le sessioni vecchie non attribuiscono.
- **Azione**: forzare auto-update del plugin via managed settings org-wide (cfr. memory
  *Managed bypassPermissions org-wide*). Niente codice nel plugin.
- **Owner proposto**: Lorenzo / piattaforma DevForge.
- **Effetto**: la copertura tende a 100% man mano che le sessioni vecchie si esauriscono.

## E2 — Domini esterni / login non-@siae.it (gap 3)

- **Evidenza**: 7 identità distinte non aziendali su day18+19 — `gmail.com` (2),
  `spindox.it` (2), `reply.it` (2), `spaarkly.it` (1), vs 49 `@siae.it`. ~12% delle persone.
  DevForge timbra fedelmente `oauthAccount.emailAddress`: se il vendor si logga con Gmail,
  quello finisce in `auth_email`.
- **Azione**: enforcement SSO — i seat Claude Code devono usare login `@siae.it` (Anthropic
  console / SCIM / SSO IdP). In alternativa, alias-map esterno→interno gestita a valle.
- **Owner proposto**: amministrazione seat Anthropic SIAE (cfr. memory *Anthropic seats SIAE*).
- **Misura**: l'evento `identity_external_domain` (design.md metodo B) fornisce il conteggio
  continuo per perseguire il provisioning.

## E3 — Mirror vendor senza DevForge (gap 5 / R4)

- **Evidenza**: ~16% commit `last:gitlab` (da analisi GitHub-side, non verificabile da S3).
  Vendor (Reply/NTT/…) pushano via mirror automatico senza il plugin installato.
- **Azione**: mandate contrattuale/onboarding di installazione DevForge per tutti i vendor;
  oppure recupero sha-match a valle (euristica GitHub-side che vogliamo rendere superflua).
- **Owner proposto**: gestione fornitori + piattaforma.
- **Nota**: nessun hook DevForge può catturare un commit prodotto su una macchina dove
  DevForge non è installato.

## E4 — `commit_created` su Bedrock/API-key (residuo gap 4)

- **Evidenza**: parte del 26% mancante su `commit_created` sono sessioni Bedrock/API-key
  che non hanno `oauthAccount` → nessuna identità SSO disponibile alla fonte.
- **Azione**: per questi, valutare a valle un segnale secondario forte (git author riconciliato
  con alias-map) — downstream, fuori scope produttore.
- **Misura**: evento `identity_unresolved` (design.md metodo B) quantifica il fenomeno.
