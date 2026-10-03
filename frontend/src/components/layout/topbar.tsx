"use client";
import { useTransition } from "react";
import { CalendarDays, LogOut, Menu } from "lucide-react";
import { logout } from "@/actions/auth";
import { setDemoDate } from "@/actions/preferences";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { DEMO_DATES } from "@/lib/demo-dates";
import { initials } from "@/lib/format";
import { ROLE_LABELS } from "@/lib/nav";
import { cn } from "@/lib/utils";
import { useUiStore } from "@/store/ui-store";
import type { CurrentUser } from "@/types/models";

type TopbarProps = { user: CurrentUser; asOf: string | undefined };

export function Topbar({ user, asOf }: TopbarProps) {
  const [pending, startTransition] = useTransition();
  const language = useUiStore((state) => state.language);
  const setLanguage = useUiStore((state) => state.setLanguage);
  const setMobileMenuOpen = useUiStore((state) => state.setMobileMenuOpen);

  const isPreset = DEMO_DATES.some((preset) => preset.value === asOf);
  const selected = asOf === undefined ? "default" : isPreset ? asOf : "custom";

  function changeDate(value: string) {
    startTransition(async () => {
      await setDemoDate(value);
    });
  }

  return (
    <header className="sticky top-0 z-20 flex h-16 items-center gap-3 border-b bg-card/90 px-4 backdrop-blur sm:px-6">
      <Button variant="ghost" size="icon" className="lg:hidden" onClick={() => setMobileMenuOpen(true)} aria-label="Open menu">
        <Menu />
      </Button>

      <div className="flex items-center gap-2">
        <CalendarDays className="hidden size-4 text-muted-foreground sm:block" />
        <span className="hidden text-xs text-muted-foreground sm:block">Demo date</span>
        <Select value={selected} onValueChange={changeDate} disabled={pending}>
          <SelectTrigger className="h-9 w-[190px]" aria-label="Demo date">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {DEMO_DATES.map((preset) => (
              <SelectItem key={preset.value} value={preset.value}>
                <span className="block">{preset.label}</span>
                <span className="block text-[11px] text-muted-foreground">{preset.hint}</span>
              </SelectItem>
            ))}
            {selected === "custom" ? <SelectItem value="custom">{asOf}</SelectItem> : null}
          </SelectContent>
        </Select>
      </div>

      <div className="ml-auto flex items-center gap-3">
        <div className="inline-flex rounded-lg bg-subtle p-1" role="group" aria-label="Language">
          {(["en", "bn"] as const).map((code) => (
            <button
              key={code}
              type="button"
              onClick={() => setLanguage(code)}
              className={cn(
                "h-7 cursor-pointer rounded-md px-2.5 text-xs font-medium transition-all",
                language === code ? "bg-card text-foreground shadow-xs" : "text-muted-foreground hover:text-foreground",
              )}
            >
              {code === "en" ? "EN" : "বাংলা"}
            </button>
          ))}
        </div>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button type="button" aria-label="Account menu" className="flex cursor-pointer items-center gap-2.5 rounded-full outline-none focus-visible:ring-[3px] focus-visible:ring-ring/40">
              <Avatar>
                <AvatarFallback>{initials(user.fullName)}</AvatarFallback>
              </Avatar>
              <span className="hidden text-left leading-tight md:block">
                <span className="block text-sm font-medium">{user.fullName}</span>
                <span className="block text-[11px] text-muted-foreground">{ROLE_LABELS[user.role]}</span>
              </span>
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuLabel>
              <div className="font-medium">{user.fullName}</div>
              <div className="mt-1 flex flex-wrap items-center gap-1.5">
                <Badge variant="secondary">{ROLE_LABELS[user.role]}</Badge>
                {user.district ? <Badge variant="outline">{user.district}</Badge> : null}
                {user.agentCode ? <Badge variant="outline">{user.agentCode}</Badge> : null}
              </div>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <form action={logout}>
              <DropdownMenuItem asChild>
                <button type="submit" className="w-full">
                  <LogOut />
                  Sign out
                </button>
              </DropdownMenuItem>
            </form>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}
