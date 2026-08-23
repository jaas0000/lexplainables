import { redirect } from "next/navigation";

/** Opgegaan in het instellingenvenster; doorverwijzing voor bestaande links (werkwijze-story 042). */
export default function FeedbackPagina() {
  redirect("/instellingen/beheer/feedback");
}
