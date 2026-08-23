import { adminProxy } from "@/lib/api-client";

export async function POST() {
  return adminProxy("/v1/admin/feedback/markeer-gezien", { method: "POST" });
}
