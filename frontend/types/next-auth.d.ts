import type { DefaultSession } from "next-auth";

declare module "next-auth" {
  interface User {
    rol?: string;
  }
  interface Session {
    user: {
      rol?: string;
    } & DefaultSession["user"];
  }
}

declare module "next-auth/jwt" {
  interface JWT {
    rol?: string;
    /** Unix-ms van de laatste live-rol-check (fase 2b.3). */
    laatste_check?: number;
  }
}
