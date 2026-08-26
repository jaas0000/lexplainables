import { redirect } from "next/navigation";
import { auth } from "@/auth";
import { AnnotatiesClient } from "@/components/annotatie/AnnotatiesClient";

export default async function AnnotatiesPagina() {
  const session = await auth();
  if (!session?.user?.name) redirect("/login");

  return <AnnotatiesClient gebruikersnaam={session.user.name} />;
}
