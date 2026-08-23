import { redirect } from "next/navigation";

/** Opgegaan in het instellingenvenster; doorverwijzing voor bestaande links (werkwijze-story 042). */
export default function LlmCallsPagina() {
  redirect("/instellingen/beheer/llm-calls");
}
