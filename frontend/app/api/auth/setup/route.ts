import { publiekApiProxy } from "@/lib/api-client";

/**
 * Publieke BFF-route: eerste beheerder aanmaken (geen sessie nodig).
 * Geeft 409 terug als de setup al voltooid is.
 */
export async function POST(req: Request) {
  const body = await req.text();
  return publiekApiProxy("/v1/auth/setup", { method: "POST", body });
}
