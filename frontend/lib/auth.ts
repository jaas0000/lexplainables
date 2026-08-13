"use client";

export const KEYCLOAK_URL =
  process.env.NEXT_PUBLIC_KEYCLOAK_URL ?? "http://localhost:8080";
export const KEYCLOAK_REALM =
  process.env.NEXT_PUBLIC_KEYCLOAK_REALM ?? "wetsanalyse";
export const KEYCLOAK_CLIENT_ID =
  process.env.NEXT_PUBLIC_KEYCLOAK_CLIENT_ID ?? "lexplainables";
const REDIRECT_URI =
  typeof window !== "undefined"
    ? `${window.location.origin}/auth/callback`
    : "";

function base64urlEncode(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer);
  let str = "";
  for (const byte of bytes) {
    str += String.fromCharCode(byte);
  }
  return btoa(str).replace(/\+/g, "-").replace(/\//g, "_").replace(/=/g, "");
}

export function generateCodeVerifier(): string {
  const array = new Uint8Array(32);
  window.crypto.getRandomValues(array);
  return base64urlEncode(array.buffer);
}

export async function generateCodeChallenge(verifier: string): Promise<string> {
  const encoder = new TextEncoder();
  const data = encoder.encode(verifier);
  const digest = await window.crypto.subtle.digest("SHA-256", data);
  return base64urlEncode(digest);
}

export async function startLogin(): Promise<void> {
  const verifier = generateCodeVerifier();
  const challenge = await generateCodeChallenge(verifier);
  sessionStorage.setItem("pkce_verifier", verifier);

  const params = new URLSearchParams({
    response_type: "code",
    client_id: KEYCLOAK_CLIENT_ID,
    redirect_uri: REDIRECT_URI,
    code_challenge: challenge,
    code_challenge_method: "S256",
    scope: "openid profile email",
  });

  // eslint-disable-next-line @next/next/no-location-assign-relative-destination
  window.location.href = `${KEYCLOAK_URL}/realms/${KEYCLOAK_REALM}/protocol/openid-connect/auth?${params.toString()}`;
}

export async function handleCallback(code: string): Promise<void> {
  const verifier = sessionStorage.getItem("pkce_verifier");
  if (!verifier) {
    throw new Error(
      "Geen PKCE-verifier gevonden. Probeer opnieuw in te loggen.",
    );
  }

  const response = await fetch(
    `${KEYCLOAK_URL}/realms/${KEYCLOAK_REALM}/protocol/openid-connect/token`,
    {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({
        grant_type: "authorization_code",
        client_id: KEYCLOAK_CLIENT_ID,
        redirect_uri: REDIRECT_URI,
        code,
        code_verifier: verifier,
      }).toString(),
    },
  );

  if (!response.ok) {
    throw new Error(
      `Authenticatie mislukt: ${response.status} ${response.statusText}`,
    );
  }

  const tokenData = await response.json();
  const accessToken: string = tokenData.access_token;

  // Decode JWT payload without verification
  const payload = JSON.parse(atob(accessToken.split(".")[1])) as {
    preferred_username?: string;
  };
  const gebruikersnaam: string = payload.preferred_username ?? "";

  sessionStorage.removeItem("pkce_verifier");
  localStorage.setItem("access_token", accessToken);
  localStorage.setItem("gebruikersnaam", gebruikersnaam);
}

export function getToken(): string | null {
  return localStorage.getItem("access_token");
}

export function getGebruikersnaam(): string | null {
  return localStorage.getItem("gebruikersnaam");
}

export function clearAuth(): void {
  localStorage.removeItem("access_token");
  localStorage.removeItem("gebruikersnaam");
}

export function getKeycloakLogoutUrl(): string {
  return `${KEYCLOAK_URL}/realms/${KEYCLOAK_REALM}/protocol/openid-connect/logout?redirect_uri=${encodeURIComponent(window.location.origin + "/login")}`;
}
