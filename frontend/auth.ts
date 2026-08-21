import NextAuth, { CredentialsSignin } from "next-auth";
import type { JWT } from "next-auth/jwt";
import Credentials from "next-auth/providers/credentials";
import { authConfig } from "./auth.config";
import { API_BASE_URL, API_TOKEN } from "./lib/api-client";

/** Auth.js gooit een CredentialsSignin met onze eigen `code` als 2FA aan staat maar er geen
 * `totp` is meegestuurd. De frontend leest `res.code === "TotpRequired"` en toont een tweede
 * invulscherm.
 *
 * Waarom geen subclass: `CredentialsSignin.constructor` zet zelf `this.code = "credentials"`,
 * en zowel class-field-syntax als een subclass-constructor die na `super()` een assignment
 * doet blijken in de Turbopack-build niet stabiel te overrulen (Next.js verplaatst class
 * fields naar vóór super(), of vergelijkbaar). Een aparte `new CredentialsSignin()` + directe
 * property-mutation gaat om die bouw-transformatie heen. */
function totpRequiredError(): CredentialsSignin {
  const err = new CredentialsSignin();
  err.code = "TotpRequired";
  return err;
}

/** TTL voor de live-rol-check (fase 2b.3): elke ~5 min ververst de JWT-callback rol/actief
 * bij de api. Env-gedreven zodat e2e-tests 'm heel kort kunnen zetten. */
const SESSION_CHECK_TTL_MS = Number(
  process.env.SESSION_CHECK_TTL_MS ?? 5 * 60 * 1000,
);

/** Fetch de live rol/actief-status via `GET /v1/auth/me`. Retourneert:
 * - `{ rol }` bij 200 (rol kan gewijzigd zijn sinds login)
 * - `"inactive"` bij 401 (account gedeactiveerd of niet meer bestaand → sessie invalideren)
 * - `null` bij netwerkfout of onverwacht antwoord (token onaangeroerd laten — geen
 *   force-logout op transient issues; server-side fetch is server-only). */
async function haalLiveStatus(
  gebruikersnaam: string,
): Promise<{ rol: string } | "inactive" | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/v1/auth/me`, {
      headers: {
        Authorization: `Bearer ${API_TOKEN}`,
        "X-User-Id": gebruikersnaam,
      },
      cache: "no-store",
    });
    if (res.status === 401) return "inactive";
    if (!res.ok) return null;
    const data = (await res.json()) as { rol: string; actief: boolean };
    if (!data.actief) return "inactive";
    return { rol: data.rol };
  } catch {
    // Netwerkfout — geen force-logout, wachten op volgende cyclus.
    return null;
  }
}

export const { handlers, auth, signIn, signOut } = NextAuth({
  ...authConfig,
  callbacks: {
    ...authConfig.callbacks,
    /** JWT-callback met live-rol-check (fase 2b.3). Overschrijft de basisversie in
     * `auth.config.ts`: bij een verse login zet 'ie rol + `laatste_check`; op vervolg-
     * requests herrifresh die na SESSION_CHECK_TTL_MS via `GET /v1/auth/me`. Een 401 of
     * `actief=false` maakt de sessie ongeldig (return `null`). Netwerkfout laat de token
     * ongewijzigd — de check probeert het bij het volgende request opnieuw. */
    async jwt({ token, user }): Promise<JWT | null> {
      if (user) {
        // Verse login — bewaar rol + tijdstempel voor de live-check.
        token.rol = user.rol;
        token.laatste_check = Date.now();
        return token;
      }
      const laatste = (token.laatste_check as number | undefined) ?? 0;
      if (Date.now() - laatste < SESSION_CHECK_TTL_MS) {
        return token;
      }
      const gebruikersnaam = token.name;
      if (!gebruikersnaam) return token;
      const status = await haalLiveStatus(gebruikersnaam);
      if (status === "inactive") return null;
      if (status !== null) {
        token.rol = status.rol;
      }
      token.laatste_check = Date.now();
      return token;
    },
  },
  providers: [
    Credentials({
      credentials: {
        gebruikersnaam: { label: "Gebruikersnaam", type: "text" },
        wachtwoord: { label: "Wachtwoord", type: "password" },
        totp: { label: "TOTP-code", type: "text" },
      },
      async authorize(credentials) {
        const gebruikersnaam = String(credentials?.gebruikersnaam ?? "");
        const wachtwoord = String(credentials?.wachtwoord ?? "");
        const totp = credentials?.totp ? String(credentials.totp) : undefined;
        if (!gebruikersnaam || !wachtwoord) return null;

        const res = await fetch(`${API_BASE_URL}/v1/auth/verify`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${API_TOKEN}`,
          },
          body: JSON.stringify({ gebruikersnaam, wachtwoord, totp }),
          cache: "no-store",
        });

        if (!res.ok) return null;
        const data = (await res.json()) as {
          ok: boolean;
          gebruikersnaam: string;
          rol: string;
          code: string;
        };

        if (!data.ok && data.code === "totp_required") {
          throw totpRequiredError();
        }
        if (!data.ok) return null;

        return {
          id: data.gebruikersnaam,
          name: data.gebruikersnaam,
          rol: data.rol,
        };
      },
    }),
  ],
});
