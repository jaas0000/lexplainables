import { redirect } from "next/navigation";

/** Beheer is opgegaan in het instellingenvenster (tabs onder /instellingen/beheer/…). Deze route
 *  blijft bestaan als doorverwijzing; de rolgate zit op het doelpad (werkwijze-story 042). */
export default function BeheerPagina() {
  redirect("/instellingen/beheer/modelprofielen");
}
