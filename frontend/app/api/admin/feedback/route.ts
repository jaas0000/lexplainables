import { adminProxy } from "@/lib/api-client";

export async function GET() {
  return adminProxy("/v1/admin/feedback");
}
