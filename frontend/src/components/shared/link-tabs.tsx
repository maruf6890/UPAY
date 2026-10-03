import Link from "next/link";
import { cn } from "@/lib/utils";

export type LinkTab = { href: string; label: string; active: boolean; count?: number };

/** Tabs that are plain links, so the server fetches the right data for each one. */
export function LinkTabs({ tabs }: { tabs: LinkTab[] }) {
  return (
    <div className="inline-flex w-fit flex-wrap items-center gap-1 rounded-lg bg-subtle p-1">
      {tabs.map((tab) => (
        <Link
          key={tab.href}
          href={tab.href}
          prefetch={false}
          className={cn(
            "inline-flex h-7 items-center gap-1.5 whitespace-nowrap rounded-md px-3 text-sm font-medium transition-all",
            tab.active ? "bg-card text-foreground shadow-xs" : "text-muted-foreground hover:text-foreground",
          )}
        >
          {tab.label}
          {tab.count !== undefined ? (
            <span className={cn("rounded-full px-1.5 text-[11px] tabular-nums", tab.active ? "bg-brand-muted" : "bg-card")}>{tab.count}</span>
          ) : null}
        </Link>
      ))}
    </div>
  );
}
