import { redirect } from "next/navigation";

/** Opgegaan in het instellingenvenster; doorverwijzing voor bestaande links (werkwijze-story 042). */
export default function GebruikersPagina() {
  redirect("/instellingen/beheer/gebruikers");
}
