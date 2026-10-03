import type { ReactNode } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { ErrorState } from "@/components/shared/error-state";
import { safe } from "@/lib/api/safe";
import { getCurrentUser } from "@/lib/auth";
import { getAsOf } from "@/lib/session";

export default async function AppLayout({ children }: { children: ReactNode }) {
  const { data: user, error, status } = await safe(() => getCurrentUser());
  const asOf = await getAsOf();

  if (!user) {
    return (
      <div className="mx-auto flex min-h-screen max-w-lg flex-col justify-center px-6">
        <ErrorState message={error ?? "Could not load your account."} status={status} />
      </div>
    );
  }

  return (
    <AppShell user={user} asOf={asOf}>
      {children}
    </AppShell>
  );
}
