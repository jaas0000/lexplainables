import "server-only";
import { API_BASE_URL, API_TOKEN } from "./api-client";

/**
 * Vraagt direct de backend of setup nog nodig is.
 * Geeft `true` als `needs_setup: true`, `false` als ingericht, `null` bij fout.
 * Callers bepalen zelf de fallback: setup-pagina kiest `?? true` (fail-open),
 * login-pagina kiest `?? false` (fail-closed, toon login).
 */
export async function haalSetupStatus(): Promise<boolean | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/v1/auth/setup-status`, {
      headers: { Authorization: `Bearer ${API_TOKEN}` },
      cache: "no-store",
    });
    if (!res.ok) return null;
    const data = (await res.json()) as { needs_setup: boolean };
    return data.needs_setup;
  } catch {
    return null;
  }
}
