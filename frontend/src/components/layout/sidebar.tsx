"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Zap } from "lucide-react";
import { NAV_ITEMS } from "@/lib/nav";
import { cn } from "@/lib/utils";
import { useUiStore } from "@/store/ui-store";
import { Sheet, SheetContent } from "@/components/ui/sheet";
import type { Role } from "@/types/models";

function SidebarContent({ role }: { role: Role }) {
  const pathname = usePathname();
  const setMobileMenuOpen = useUiStore((state) => state.setMobileMenuOpen);
  const items = NAV_ITEMS.filter((item) => item.roles.includes(role));

  return (
    <div className="flex h-full flex-col">
      <div className="flex h-16 items-center gap-2.5 border-b px-5">
        <span className="flex size-9 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-xs">
          <Zap className="size-5" strokeWidth={2.5} />
        </span>
        <div className="leading-tight">
          <div className="text-[15px] font-semibold tracking-tight">upay Pulse</div>
          <div className="text-[11px] text-sidebar-muted">Agent liquidity intelligence</div>
        </div>
      </div>

      <nav className="flex-1 space-y-1 p-3">
        {items.map((item) => {
          const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              prefetch={false}
              onClick={() => setMobileMenuOpen(false)}
              className={cn(
                "relative flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                active ? "bg-sidebar-active text-foreground" : "text-ink-secondary hover:bg-sidebar-hover hover:text-foreground",
              )}
            >
              {active ? <span className="absolute top-2 bottom-2 left-0 w-[3px] rounded-r-full bg-primary" /> : null}
              <Icon className={cn("size-[18px]", active ? "text-foreground" : "text-sidebar-muted")} />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="m-3 rounded-xl border bg-sidebar-surface p-3.5">
        <div className="text-xs font-medium">Synthetic demo data</div>
        <p className="mt-1 text-[11px] leading-relaxed text-sidebar-muted">
          Forecasts and alerts are advisory. A person makes every decision.
        </p>
      </div>
    </div>
  );
}

/** The fixed menu on large screens and the slide-in menu on small ones. */
export function Sidebar({ role }: { role: Role }) {
  const open = useUiStore((state) => state.mobileMenuOpen);
  const setOpen = useUiStore((state) => state.setMobileMenuOpen);
  return (
    <>
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 border-r bg-sidebar lg:block">
        <SidebarContent role={role} />
      </aside>
      <Sheet open={open} onOpenChange={setOpen}>
        <SheetContent title="Menu">
          <SidebarContent role={role} />
        </SheetContent>
      </Sheet>
    </>
  );
}
