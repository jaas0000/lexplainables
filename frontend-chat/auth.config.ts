import type { NextAuthConfig } from "next-auth";

function isPublic(path: string): boolean {
  return path === "/login" || path.startsWith("/api/auth");
}

// Zelfde vorm als frontend/auth.config.ts — hier zonder de rol-gate (geen admin-routes) en
// zonder de disclaimer-gate (die hoort bij frontend/'s specifieke onboarding, niet bij deze
// minimale eerste chat-UI, zie story 056 §Buiten scope).
export const authConfig = {
  trustHost: true,
  pages: { signIn: "/login" },
  session: { strategy: "jwt" as const, maxAge: 12 * 60 * 60 },
  cookies: {
    sessionToken: {
      name:
        process.env.NODE_ENV === "production"
          ? "__Secure-authjs.session-token"
          : "authjs.session-token",
      options: {
        httpOnly: true,
        sameSite: "lax" as const,
        path: "/",
        secure: process.env.NODE_ENV === "production",
      },
    },
  },
  callbacks: {
    authorized({ auth, request }) {
      const { pathname } = request.nextUrl;
      if (isPublic(pathname)) return true;
      return Boolean(auth?.user);
    },
  },
  providers: [],
} satisfies NextAuthConfig;
