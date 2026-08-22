"use client";

/** De balk boven het hoofdgebied op smalle schermen: hamburger → sidebar-drawer, plus waar je bent.
 *
 *  `AppSidebar` is onder `lg` een `hidden`-kolom; zonder deze balk is er op een half scherm geen
 *  sidebar en geen manier om er een te krijgen — geen navigatie, geen account, geen uitloggen.
 */
export function MobileTopbar({
  titel,
  onOpenSidebar,
}: {
  /** Waar je bent. De sidebar draagt de volledige navigatie. */
  titel: string;
  onOpenSidebar: () => void;
}) {
  return (
    <div className="flex shrink-0 items-center gap-2 border-b border-line bg-paper px-3 py-2 pt-[max(0.5rem,env(safe-area-inset-top))] print:hidden lg:hidden">
      <button
        type="button"
        onClick={onOpenSidebar}
        aria-label="Menu openen"
        className="focus-ring inline-flex items-center justify-center rounded-lg border border-line p-2 text-lint transition-colors hover:bg-surface"
      >
        <svg
          width="20"
          height="20"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          aria-hidden
        >
          <line x1="3" y1="6" x2="21" y2="6" />
          <line x1="3" y1="12" x2="21" y2="12" />
          <line x1="3" y1="18" x2="21" y2="18" />
        </svg>
      </button>
      <span className="min-w-0 flex-1 truncate text-sm font-medium text-lint">
        {titel}
      </span>
    </div>
  );
}
