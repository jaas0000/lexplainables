import { cookies } from "next/headers";
import type { Metadata } from "next";
import { DisclaimerClient } from "@/components/disclaimer/DisclaimerClient";

export const metadata: Metadata = {
  title: "Testomgeving · Lexplainables",
};

export default async function DisclaimerPage({
  searchParams,
}: {
  searchParams: Promise<{ callbackUrl?: string | string[] }>;
}) {
  const cookieStore = await cookies();
  const alGeaccepteerd = cookieStore.has("disclaimer_geaccepteerd");

  const params = await searchParams;
  const callbackUrl =
    (Array.isArray(params.callbackUrl)
      ? params.callbackUrl[0]
      : params.callbackUrl) ?? "/";

  return (
    <DisclaimerClient
      alGeaccepteerd={alGeaccepteerd}
      callbackUrl={callbackUrl}
    />
  );
}
