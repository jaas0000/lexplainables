import NextAuth from "next-auth";
import Credentials from "next-auth/providers/credentials";
import { authConfig } from "./auth.config";
import { API_BASE_URL, API_TOKEN } from "./lib/api-client";

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
          rol: string;
        };
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
