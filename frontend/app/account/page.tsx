import { redirect } from "next/navigation";

/** Account is opgegaan in het instellingenvenster. Deze route blijft bestaan als doorverwijzing
 *  voor bestaande links en bladwijzers (werkwijze-story 042). */
export default function AccountPagina() {
  redirect("/instellingen/account");
}
