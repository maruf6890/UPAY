import type { ReactNode } from "react";
import { Sidebar } from "@/components/layout/sidebar";
import { Topbar } from "@/components/layout/topbar";
import type { CurrentUser } from "@/types/models";

type AppShellProps = { user: CurrentUser; asOf: string | undefined; children: ReactNode };

export function AppShell({ user, asOf, children }: AppShellProps) {
  return (
    <div className="min-h-screen">
      <Sidebar role={user.role} />
      <div className="lg:pl-64">
        <Topbar user={user} asOf={asOf} />
        <main className="mx-auto w-full max-w-[1400px] px-4 py-6 sm:px-6">{children}</main>
      </div>
    </div>
  );
}
