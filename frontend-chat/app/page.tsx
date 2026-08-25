import { redirect } from "next/navigation";
import { auth } from "@/auth";
import { ChatVenster } from "@/components/ChatVenster";

export default async function HomePagina() {
  const session = await auth();
  if (!session?.user?.name) redirect("/login");

  return <ChatVenster gebruikersnaam={session.user.name} />;
}
