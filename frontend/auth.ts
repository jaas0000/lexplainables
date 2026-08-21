import NextAuth, { CredentialsSignin } from "next-auth";
import Credentials from "next-auth/providers/credentials";
import { authConfig } from "./auth.config";
import { API_BASE_URL, API_TOKEN } from "./lib/api-client";

/** Auth.js gooit deze error als 2FA aan staat maar er geen `totp` is meegestuurd. De
 * frontend leest `res.error === "TotpRequired"` en toont een tweede invulscherm. */
class TotpRequired extends CredentialsSignin {
  code = "TotpRequired";
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
          throw new TotpRequired();
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
