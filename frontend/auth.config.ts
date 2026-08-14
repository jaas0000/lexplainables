import type { NextAuthConfig } from "next-auth";

function isPublic(path: string): boolean {
  return path === "/login" || path.startsWith("/api/auth");
}

function isDisclaimerExempt(path: string): boolean {
  return (
    path === "/disclaimer" ||
    path.startsWith("/api/") ||
    path.startsWith("/mockup/")
  );
}

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
      const { pathname, search } = request.nextUrl;
      if (isPublic(pathname)) return true;
      if (!auth?.user) return false;

      // Disclaimer-gate: stuur ingelogde gebruikers zonder cookie naar /disclaimer
      if (!isDisclaimerExempt(pathname)) {
        const disclaimerCookie = request.cookies.get("disclaimer_geaccepteerd");
        if (!disclaimerCookie) {
          return Response.redirect(
            new URL(
              `/disclaimer?callbackUrl=${encodeURIComponent(pathname + search)}`,
              request.url,
            ),
          );
        }
      }

      return true;
    },
    jwt({ token, user }) {
      if (user) {
        token.rol = user.rol;
      }
      return token;
    },
    session({ session, token }) {
      session.user.rol = token.rol as string | undefined;
      return session;
    },
  },
  providers: [],
} satisfies NextAuthConfig;
