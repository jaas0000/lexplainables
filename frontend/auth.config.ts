import type { NextAuthConfig } from "next-auth";

function isPublic(path: string): boolean {
  return path === "/login" || path.startsWith("/api/auth");
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
      const path = request.nextUrl.pathname;
      if (isPublic(path)) return true;
      return !!auth?.user;
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
