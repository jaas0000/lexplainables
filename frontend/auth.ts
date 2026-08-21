import NextAuth, { CredentialsSignin } from "next-auth";
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

export const { handlers, auth, signIn, signOut } = NextAuth({
  ...authConfig,
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
