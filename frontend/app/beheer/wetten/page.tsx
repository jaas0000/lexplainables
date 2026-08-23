import { redirect } from "next/navigation";

/** Opgegaan in het instellingenvenster; doorverwijzing voor bestaande links (werkwijze-story 042). */
export default function WettenPagina() {
  redirect("/instellingen/beheer/wetten");
}
