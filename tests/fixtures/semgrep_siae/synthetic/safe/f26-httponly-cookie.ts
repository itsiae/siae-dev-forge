// SAFE: JWT server-side via Set-Cookie HttpOnly + Secure: client never sees JWT.

declare const fetch: (input: string, init?: object) => Promise<Response>;

async function loginSafe(email: string, password: string): Promise<void> {
  await fetch("/api/login", {
    method: "POST",
    credentials: "include",  // cookie HttpOnly inviato dal server
    body: JSON.stringify({ email, password }),
  });
  // Nessun localStorage.setItem("token", ...) — JWT mai esposto al JS
}

// SAFE: non-token use of localStorage (preferences, UI state).
declare const localStorage: { setItem(key: string, value: string): void };
function saveCartId(cartId: string): void {
  localStorage.setItem("cartId", cartId);
}
