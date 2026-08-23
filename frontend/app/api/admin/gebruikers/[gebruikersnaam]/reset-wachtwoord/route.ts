import { adminProxy } from "@/lib/api-client";

export async function POST(
  _req: Request,
  { params }: { params: Promise<{ gebruikersnaam: string }> },
) {
  const { gebruikersnaam } = await params;
  return adminProxy(`/v1/admin/gebruikers/${gebruikersnaam}/reset-wachtwoord`, {
    method: "POST",
  });
}
