import { adminProxy } from "@/lib/api-client";

export async function GET() {
  return adminProxy("/v1/admin/profielen");
}

export async function POST(req: Request) {
  const body = await req.text();
  return adminProxy("/v1/admin/profielen", { method: "POST", body });
}
