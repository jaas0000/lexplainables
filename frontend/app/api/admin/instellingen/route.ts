import { adminProxy } from "@/lib/api-client";

export async function GET() {
  return adminProxy("/v1/admin/instellingen");
}

export async function PUT(req: Request) {
  const body = await req.text();
  return adminProxy("/v1/admin/instellingen", { method: "PUT", body });
}
