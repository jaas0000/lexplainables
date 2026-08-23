"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AccountPanel } from "@/components/account/AccountPanel";
import { ApiTokensPanel } from "@/components/beheer/ApiTokensPanel";
import { AppInstellingenPanel } from "@/components/beheer/AppInstellingenPanel";
import { BerichtenBeheerPanel } from "@/components/beheer/BerichtenBeheerPanel";
import { FeedbackPanel } from "@/components/beheer/FeedbackPanel";
import { GebruikersPanel } from "@/components/beheer/GebruikersPanel";
import { LlmCallsPanel } from "@/components/beheer/LlmCallsPanel";
import { ModelprofielenPanel } from "@/components/beheer/ModelprofielenPanel";
import { WettenPanel } from "@/components/beheer/WettenPanel";
import { Tabs, type TabDef } from "@/components/ui/Tabs";
import { beheerFetch } from "@/lib/beheer-fetch";
import { INSTELLINGEN_TABS, padVanTab, type TabKey } from "@/lib/instellingen";

const PANEEL: Record<TabKey, React.ReactNode> = {
  account: <AccountPanel />,
  berichten: <BerichtenBeheerPanel />,
  modelprofielen: <ModelprofielenPanel />,
  gebruikers: <GebruikersPanel />,
  wetten: <WettenPanel />,
  instellingen: <AppInstellingenPanel />,
  "llm-calls": <LlmCallsPanel />,
  "api-tokens": <ApiTokensPanel />,
  feedback: <FeedbackPanel />,
};

interface Props {
  actief: TabKey;
  isBeheerder: boolean;
  /** In de dialoog wisselen we van tab met `replace` (geen extra history-entry per tab, zodat de
   *  back-knop de dialoog sluit i.p.v. door de tabs terug te lopen). Op de volle pagina `push`. */
  vervangHistorie?: boolean;
}

/** De inhoud van het instellingenvenster: tabkolom links, paneel rechts. Wordt gedeeld door de
 *  dialoog (vanuit de app) en de volledige pagina (directe link/refresh), zodat beide dezelfde
 *  panelen tonen (werkwijze-story 042, poort van `wetsanalyse-ai`). */
export function InstellingenInhoud({
  actief,
  isBeheerder,
  vervangHistorie = false,
}: Props) {
  const router = useRouter();
  const [ongelezenFeedback, setOngelezenFeedback] = useState(0);
  const zichtbaar = INSTELLINGEN_TABS.filter((t) => !t.admin || isBeheerder);

  // Ongelezen-teller voor de feedbacktab. Alleen voor beheerders (het endpoint eist die rol) en
  // stil falend: een hapering mag het venster niet blokkeren, de badge is een hint. Hergebruikt
  // dezelfde `beheerFetch`-aanroep die eerder inline in het oude `app/beheer/page.tsx` stond.
  const laadFeedbackTeller = useCallback(async () => {
    if (!isBeheerder) return;
    try {
      const data = (await beheerFetch(
        "/api/admin/feedback/ongelezen-aantal",
      )) as {
        aantal: number;
      };
      setOngelezenFeedback(data.aantal);
    } catch {
      /* badge blijft staan zoals hij was */
    }
  }, [isBeheerder]);

  // Bij het openen, en opnieuw zodra je de feedbacktab verlaat — dat paneel markeert bij openen als
  // gezien, dus de teller die we bij het laden ophaalden klopt daarna niet meer.
  useEffect(() => {
    // De setState zit ín de async callback, dus pas ná het await — geen synchrone cascading
    // render. De regel kan daar niet doorheen kijken.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (actief !== "feedback") void laadFeedbackTeller();
  }, [actief, laadFeedbackTeller]);

  const tabs: TabDef[] = zichtbaar.map((t) => ({
    key: t.key,
    label: t.label,
    content: PANEEL[t.key],
    badge: t.key === "feedback" ? ongelezenFeedback : undefined,
  }));

  return (
    <Tabs
      tabs={tabs}
      active={actief}
      label="Instellingen"
      lazy
      onChange={(key) => {
        const pad = padVanTab(key as TabKey);
        if (vervangHistorie) router.replace(pad);
        else router.push(pad);
      }}
    />
  );
}
