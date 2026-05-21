# Functional bug report

- **Run id**: example-ts-frontend
- **Scope hash**: 4f1c8a9d
- **Skill semver**: 1.1.0
- **Model id**: claude-opus-4-7
- **Mode**: report-only
- **Generated at**: 2026-05-21T00:00:00Z
- **Confidence (global)**: medium
- **Findings**: 0 SEV-1 · 1 SEV-2 · 1 SEV-3 · 0 SEV-4
- **Lang**: en

## Index

| Finding | Journey | Severity | Title | Entry point |
|---|---|---|---|---|
| F-0001 | J-001 | SEV-2 | Pay button accepts double click within request window | nx:web/components/checkout/PayButton.tsx |
| F-0002 | J-002 | SEV-3 | Signup form clears on browser back navigation | nx:web/app/signup/page.tsx |

## Journey J-001

### F-0001 — Pay button accepts double click within request window

- **Severity**: SEV-2 (rubric row R-SEV2-03)
- **Pattern**: BP-014
- **Category**: data-race
- **Entry point**: nx:web/components/checkout/PayButton.tsx
- **Confidence**: medium

**Preconditions**

- The user has a populated cart and a valid stored payment method.
- The user is on the page /checkout.

**Steps**

1. (ui-user) Click the button labeled "Pay"
2. (ui-user) Click the button labeled "Pay" within 100 ms
3. (observer) Open the table "payments" on database "siae-checkout-prod" and report the row count for the user's order_id

**Expected result**

Exactly one row is inserted in the table "payments" for the order_id.

**Actual result**

Two rows are inserted in the table "payments" for the same order_id; the second row is reconciled only by a nightly job.

**Evidence**

- `components/checkout/PayButton.tsx:22-34` @ `c1a4f8d`
  > const onClick = async () => { await api.pay(orderId); };
- `app/api/pay/route.ts:11-19` @ `c1a4f8d`
  > await db.payments.insert({ orderId, ts: Date.now() });

**Suggested fix direction**

Disable the button after the first click until the response settles, and add a server-side dedupe key on (user_id, order_id, minute).

**Reproduction rate target**

`95%`

---

## Journey J-002

### F-0002 — Signup form clears on browser back navigation

- **Severity**: SEV-3 (rubric row R-SEV3-07)
- **Pattern**: BP-013
- **Category**: business-logic
- **Entry point**: nx:web/app/signup/page.tsx
- **Confidence**: medium

**Preconditions**

- Public access to the application; the user is not yet authenticated.
- Browser history is enabled (standard Chrome / Firefox / Safari).

**Steps**

1. (ui-user) Open the page /signup
2. (ui-user) Type "mario.rossi@example.com" in the field "email"
3. (ui-user) Type "Pa$$w0rd1!" in the field "password"
4. (ui-user) Click the button labeled "Continue"
5. (ui-user) Press the browser back arrow once
6. (observer) Inspect the page /signup and report the value of the field "email"

**Expected result**

The field "email" still contains "mario.rossi@example.com" after the back navigation.

**Actual result**

The field "email" is empty; the user must re-enter the address.

**Evidence**

- `app/signup/page.tsx:38-52` @ `c1a4f8d`
  > const [email, setEmail] = useState("");
- `app/signup/page.tsx:71-78` @ `c1a4f8d`
  > router.push("/signup/confirm");

**Suggested fix direction**

Persist the form state in sessionStorage keyed by route, or wire the form to a route-level loader that rehydrates state on popstate.

**Reproduction rate target**

`95%`

---
