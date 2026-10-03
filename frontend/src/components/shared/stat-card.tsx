import type { LucideIcon } from "lucide-react";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";

type Tone = "default" | "danger" | "warning" | "success" | "info" | "ai";

const TONES: Record<Tone, string> = {
  default: "bg-brand-soft text-[#8a6a00]",
  danger: "bg-danger-soft text-danger",
  warning: "bg-warning-soft text-warning",
  success: "bg-success-soft text-success",
  info: "bg-info-soft text-info",
  ai: "bg-ai-soft text-ai",
};

type StatCardProps = { label: string; value: string; hint?: string; icon?: LucideIcon; tone?: Tone; className?: string };

export function StatCard({ label, value, hint, icon: Icon, tone = "default", className }: StatCardProps) {
  return (
    <Card className={cn("gap-3 py-4", className)}>
      <div className="flex items-center justify-between px-5">
        <span className="text-xs font-medium text-muted-foreground">{label}</span>
        {Icon ? (
          <span className={cn("flex size-8 items-center justify-center rounded-lg", TONES[tone])}>
            <Icon className="size-4" />
          </span>
        ) : null}
      </div>
      <div className="px-5">
        <div className="text-2xl font-semibold tabular-nums tracking-tight">{value}</div>
        {hint ? <div className="mt-0.5 text-xs text-muted-foreground">{hint}</div> : null}
      </div>
    </Card>
  );
}
