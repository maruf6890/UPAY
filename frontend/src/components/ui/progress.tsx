import * as React from "react";
import { cn } from "@/lib/utils";

type ProgressProps = { value: number; className?: string; barClassName?: string };

/** A simple bar. value is 0 to 100. */
function Progress({ value, className, barClassName }: ProgressProps) {
  const width = Math.max(0, Math.min(100, value));
  return (
    <div data-slot="progress" className={cn("h-2 w-full overflow-hidden rounded-full bg-subtle", className)}>
      <div className={cn("h-full rounded-full bg-primary transition-all", barClassName)} style={{ width: `${width}%` }} />
    </div>
  );
}

export { Progress };
