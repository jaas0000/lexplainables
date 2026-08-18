import { publiekApiProxy } from "@/lib/api-client";

/**
 * Publieke BFF-route: setup-status opvragen (geen sessie nodig).
 */
export async function GET() {
  return publiekApiProxy("/v1/auth/setup-status");
}
