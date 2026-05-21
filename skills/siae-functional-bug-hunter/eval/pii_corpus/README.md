# PII corpus

Fixtures for `scripts/redact_pii.py`. Each fixture is a pair:

- `<id>.input.txt` — raw text containing one or more PII tokens.
- `<id>.expected.txt` — same text with every PII token replaced by the
  appropriate `<REDACTED:type>` placeholder.

The unit test that drives Quality Bar #10 simply runs

    python3 scripts/redact_pii.py < <id>.input.txt > /tmp/out.txt
    diff /tmp/out.txt <id>.expected.txt

and asserts an empty diff for every fixture.

## Seed fixtures (shipped with v1.0.0)

The skill ships with the seven fixtures listed in `manifest.json` in
this directory. Each exercises one row of the regex catalog in
`redact_pii.py`. Operators add their own fixtures as needed; they must
be sanitized (no real PII; use clearly-synthetic patterns).

## Adding a fixture

1. Pick a unique slug for the new PII variant (e.g. `slack-token`).
2. Write `<slug>.input.txt` with one synthetic token of that variant
   in a realistic sentence.
3. Write `<slug>.expected.txt` with the token replaced by
   `<REDACTED:<TYPE>>` where `<TYPE>` matches the `redact_pii.py`
   placeholder.
4. Add `<slug>.input.txt` to `manifest.json` `fixtures` array.
5. If the variant is not yet in the regex catalog, also update
   `redact_pii.py` (minor semver bump) and re-run all fixtures.

## Important

These fixtures MUST use synthetic values. No real credentials, no real
fiscal codes, no real IBANs, no real customer emails. The standard
synthetic patterns are:

- email: `mario.rossi@example.com`
- IPv4: `203.0.113.5` (TEST-NET-3, never routable)
- IPv6: `2001:db8::1` (RFC 3849, never routable)
- JWT: a clearly-synthetic three-segment token whose body decodes to
  obvious test data.
- AWS access key id: `AKIAIOSFODNN7EXAMPLE` (the AWS-documented test
  value).
- AWS secret: `wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY` (the
  AWS-documented test value).
- Italian fiscal code: `RSSMRA85M01H501Z` (well-formed but assigned
  to a fictional Mario Rossi).
- Italian IBAN: `IT60X0542811101000000123456` (synthetic check digits).
- Hex: 64 zeroes or `deadbeef…` repeated.
