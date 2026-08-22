export interface NavSectie {
  pad: string;
  titel: string;
  /** Extra paden die tot dezelfde sectie horen (bv. de mockup-variant vóór promotie). */
  aliassen?: string[];
}

/** Eén bron voor "bij welke sectie hoort dit pad" — gebruikt door de mobiele topbar-titel
 *  (`AppShell.tsx`) én de sidebar-navigatie (`AppSidebar.tsx`), zodat ze niet uit de pas kunnen
 *  lopen (zoals eerder met `/mockup/beheer`, dat maar op één van de twee plekken meetelde). */
export const NAV_SECTIES: NavSectie[] = [
  { pad: "/projecten", titel: "Projecten" },
  { pad: "/werkplek", titel: "Werkplek" },
  { pad: "/account", titel: "Account" },
  { pad: "/beheer", titel: "Beheer", aliassen: ["/mockup/beheer"] },
  { pad: "/berichten", titel: "Berichten" },
  { pad: "/wetcatalogus", titel: "Wetcatalogus" },
];

export function actieveSectie(pathname: string | null): NavSectie | undefined {
  if (!pathname) return undefined;
  return NAV_SECTIES.find(
    (s) =>
      pathname.startsWith(s.pad) ||
      s.aliassen?.some((alias) => pathname.startsWith(alias)),
  );
}
