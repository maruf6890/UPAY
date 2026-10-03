import type { ReactNode } from "react";
import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

type WidgetCardProps = {
  title: string;
  description?: string;
  href?: string;
  linkLabel?: string;
  className?: string;
  contentClassName?: string;
  children: ReactNode;
};

/** The white card every dashboard widget sits in. */
export function WidgetCard({ title, description, href, linkLabel = "View all", className, contentClassName, children }: WidgetCardProps) {
  return (
    <Card className={cn("h-full", className)}>
      <CardHeader>
        <div className="flex items-start justify-between gap-3">
          <div className="space-y-1">
            <CardTitle className="text-[15px]">{title}</CardTitle>
            {description ? <CardDescription>{description}</CardDescription> : null}
          </div>
          {href ? (
            <Link href={href} prefetch={false} className="inline-flex shrink-0 items-center gap-1 text-xs font-medium text-ink-secondary hover:text-foreground">
              {linkLabel}
              <ArrowRight className="size-3.5" />
            </Link>
          ) : null}
        </div>
      </CardHeader>
      <CardContent className={contentClassName}>{children}</CardContent>
    </Card>
  );
}
