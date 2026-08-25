import type { ReactNode } from "react";

/** Minimale versie van frontend/'s `AuthFrame` — één gecentreerde kaart, zonder het
 * Belastingdienst-logo/de volledige huisstijl-parity (buiten scope voor deze eerste
 * chat-UI-story, zie `docs/project/stories/056-frontend-chat.md` §Buiten scope). */
export function AuthFrame({
  titel,
  onderschrift,
  children,
}: {
  titel: string;
  onderschrift?: ReactNode;
  children: ReactNode;
}) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-surface px-4 py-10">
      <div className="w-full max-w-sm">
        <div className="card">
          <h1 className="text-2xl font-semibold text-lint">{titel}</h1>
          {onderschrift && (
            <p className="mt-1 text-sm text-muted">{onderschrift}</p>
          )}
          <div className="mt-6">{children}</div>
        </div>
      </div>
    </div>
  );
}
