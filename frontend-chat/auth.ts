import NextAuth from "next-auth";
import Credentials from "next-auth/providers/credentials";
import { authConfig } from "./auth.config";
import { API_BASE_URL, API_TOKEN } from "./lib/api-client";

// Zelfde Credentials-provider tegen `POST /v1/auth/verify` als frontend/auth.ts, maar zonder
// TOTP/2FA en zonder de live-rol-herverificatie (frontend-chat kent geen rollen) — een minimale
// eerste versie, zie story 056 §Buiten scope.
export const { handlers, auth, signIn, signOut } = NextAuth({
  ...authConfig,
  providers: [
    Credentials({
      credentials: {
        gebruikersnaam: { label: "Gebruikersnaam", type: "text" },
        wachtwoord: { label: "Wachtwoord", type: "password" },
      },
      async authorize(credentials) {
        const gebruikersnaam = String(credentials?.gebruikersnaam ?? "");
        const wachtwoord = String(credentials?.wachtwoord ?? "");
        if (!gebruikersnaam || !wachtwoord) return null;

        const res = await fetch(`${API_BASE_URL}/v1/auth/verify`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${API_TOKEN}`,
          },
          body: JSON.stringify({ gebruikersnaam, wachtwoord }),
          cache: "no-store",
        });

        if (!res.ok) return null;
        const data = (await res.json()) as {
          ok: boolean;
          gebruikersnaam: string;
        };
        if (!data.ok) return null;

        return { id: data.gebruikersnaam, name: data.gebruikersnaam };
      },
    }),
  ],
});
