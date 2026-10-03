import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const alertVariants = cva(
  "relative grid w-full grid-cols-[0_1fr] items-start gap-y-0.5 rounded-xl border px-4 py-3 text-sm has-[>svg]:grid-cols-[calc(var(--spacing)*4)_1fr] has-[>svg]:gap-x-3 [&>svg]:mt-0.5 [&>svg]:size-4",
  {
    variants: {
      variant: {
        default: "bg-card text-foreground",
        info: "border-info-border bg-info-soft text-foreground [&>svg]:text-info",
        warning: "border-warning-border bg-warning-soft text-foreground [&>svg]:text-warning",
        danger: "border-danger-border bg-danger-soft text-foreground [&>svg]:text-danger",
        success: "border-success-border bg-success-soft text-foreground [&>svg]:text-success",
        ai: "border-ai-border bg-ai-soft text-foreground [&>svg]:text-ai",
      },
    },
    defaultVariants: { variant: "default" },
  },
);

type AlertProps = React.ComponentProps<"div"> & VariantProps<typeof alertVariants>;

function Alert({ className, variant, ...props }: AlertProps) {
  return <div data-slot="alert" role="alert" className={cn(alertVariants({ variant }), className)} {...props} />;
}
function AlertTitle({ className, ...props }: React.ComponentProps<"div">) {
  return <div data-slot="alert-title" className={cn("col-start-2 font-medium", className)} {...props} />;
}
function AlertDescription({ className, ...props }: React.ComponentProps<"div">) {
  return <div data-slot="alert-description" className={cn("col-start-2 text-sm text-ink-secondary", className)} {...props} />;
}

export { Alert, AlertTitle, AlertDescription };
