import type { ReactNode } from "react";
import { Inbox, type LucideIcon } from "lucide-react";

type EmptyStateProps = { title: string; description?: string; icon?: LucideIcon; action?: ReactNode };

/** Shown when a list has nothing in it. */
export function EmptyState({ title, description, icon: Icon = Inbox, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center rounded-xl border border-dashed bg-card px-6 py-12 text-center">
      <div className="mb-3 flex size-11 items-center justify-center rounded-full bg-subtle text-muted-foreground">
        <Icon className="size-5" />
      </div>
      <p className="text-sm font-medium">{title}</p>
      {description ? <p className="mt-1 max-w-sm text-sm text-muted-foreground">{description}</p> : null}
      {action ? <div className="mt-4">{action}</div> : null}
    </div>
  );
}
