/** Tabdefinities en pad-helpers voor het instellingenvenster (Account + Beheer).
 *
 *  Bewust géén `"use client"`-module — zowel Server Components (`app/instellingen/[[...tab]]/
 *  page.tsx`, de intercepting route) als de client-dialoogschil importeren dit bestand.
 *
 *  Admin-tabs leven onder het `"beheer/"`-padprefix zodat `isAdminTab` één prefix-check blijft,
 *  net als de rolgate in `auth.config.ts` (werkwijze-story 042; poort van
 *  `wetsanalyse-ai/frontend/lib/instellingen.ts`). */
export const INSTELLINGEN_TABS = [
  { key: "account", pad: "account", label: "Account", admin: false },
  {
    key: "berichten",
    pad: "beheer/berichten",
    label: "Berichten",
    admin: true,
  },
  {
    key: "modelprofielen",
    pad: "beheer/modelprofielen",
    label: "LLM-profielen",
    admin: true,
  },
  {
    key: "gebruikers",
    pad: "beheer/gebruikers",
    label: "Gebruikers",
    admin: true,
  },
  { key: "wetten", pad: "beheer/wetten", label: "Wetcatalogus", admin: true },
  {
    key: "instellingen",
    pad: "beheer/instellingen",
    label: "Instellingen",
    admin: true,
  },
  {
    key: "llm-calls",
    pad: "beheer/llm-calls",
    label: "LLM-calls",
    admin: true,
  },
  {
    key: "api-tokens",
    pad: "beheer/api-tokens",
    label: "API-tokens",
    admin: true,
  },
  { key: "feedback", pad: "beheer/feedback", label: "Feedback", admin: true },
] as const;

export type TabKey = (typeof INSTELLINGEN_TABS)[number]["key"];

const STANDAARD_TAB: TabKey = "account";

/** Padsegmenten (uit `[[...tab]]`) → tabsleutel. Onbekend of leeg → de standaardtab. */
export function tabUitPad(segmenten: string[] | undefined): TabKey {
  const pad = (segmenten ?? []).join("/");
  const gevonden = INSTELLINGEN_TABS.find((t) => t.pad === pad);
  return gevonden ? gevonden.key : STANDAARD_TAB;
}

export function padVanTab(key: TabKey): string {
  const tab = INSTELLINGEN_TABS.find((t) => t.key === key);
  return `/instellingen/${tab ? tab.pad : INSTELLINGEN_TABS[0].pad}`;
}

export function isAdminTab(key: TabKey): boolean {
  return INSTELLINGEN_TABS.find((t) => t.key === key)?.admin ?? false;
}
