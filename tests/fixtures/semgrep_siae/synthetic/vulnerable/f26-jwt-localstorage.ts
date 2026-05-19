// Reproduces PENTEST_REPORT 2026-05-18 F-26 pattern (JWT in localStorage).
// NO real broadcasting code per ADR-004.

declare const fetch: (input: string, init?: object) => Promise<Response>;
declare const localStorage: { setItem(key: string, value: string): void };

// VULNERABLE: JWT stored in localStorage — readable by any XSS payload.
async function loginVulnerable(email: string, password: string): Promise<void> {
  const resp = await fetch("/api/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  const data = await resp.json() as { token: string };
  localStorage.setItem("token", data.token);
}

// VULNERABLE variants:
function saveToken(jwt: string): void {
  localStorage.setItem("jwt", jwt);
}
function saveAccessToken(t: string): void {
  localStorage.setItem("accessToken", t);
}
