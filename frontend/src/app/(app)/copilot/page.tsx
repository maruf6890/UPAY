import Link from "next/link";
import { ArrowUpRight, Sparkles } from "lucide-react";
import { AskCopilot } from "@/components/copilot/ask-copilot";
import { Bilingual } from "@/components/shared/bilingual";
import { EmptyState } from "@/components/shared/empty-state";
import { ErrorState } from "@/components/shared/error-state";
import { PageHeader } from "@/components/shared/page-header";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { safe } from "@/lib/api/safe";
import { requireRole } from "@/lib/auth";
import { drillDownToRoute } from "@/lib/drill-down";
import { formatDateTime, humanize } from "@/lib/format";
import { getAsOf } from "@/lib/session";
import { getCopilotBrief } from "@/services/copilot";
import { TriangleAlert } from "lucide-react";

export default async function CopilotPage() {
  await requireRole(["manager", "analyst"]);
  const asOf = await getAsOf();
  const { data, error, status } = await safe(() => getCopilotBrief(asOf));
  // Purple is reserved for text a language model wrote. The template fallback gets a neutral look.
  const writtenByAi = data ? data.generatedBy.startsWith("langchain") : false;

  return (
    <>
      <PageHeader title="Copilot" description="A morning brief written from the model outputs, and a place to ask questions. Every item links to the details." />

      <div className="grid gap-4 lg:grid-cols-12">
        <div className="space-y-4 lg:col-span-7">
          {!data ? (
            <ErrorState message={error ?? "Could not load the brief."} status={status} />
          ) : (
            <>
              <Card className={writtenByAi ? "border-ai-border bg-gradient-to-br from-ai-soft to-card" : undefined}>
                <CardHeader>
                  <div className="flex items-center justify-between gap-2">
                    <Badge variant={writtenByAi ? "ai" : "secondary"} className="gap-1.5">
                      {writtenByAi ? <Sparkles /> : null} {writtenByAi ? "Morning brief" : "Morning brief (template, no AI key)"}
                    </Badge>
                    <span className="text-xs text-muted-foreground">
                      {formatDateTime(data.asOf)}, {data.scope}
                    </span>
                  </div>
                  <CardTitle className="pt-2 text-xl leading-snug">{data.headline}</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <p className="text-sm leading-relaxed text-ink-secondary">
                    <Bilingual en={data.summary} bn={data.banglaSummary} className="bn" />
                  </p>
                  <p className="text-[11px] text-muted-foreground">
                    Written by: {data.generatedBy}
                    {data.droppedUnverifiedPriorities > 0 ? `. ${data.droppedUnverifiedPriorities} unverified item(s) were removed.` : ""}
                  </p>
                </CardContent>
              </Card>

              {data.warnings.length > 0 ? (
                <Alert variant="warning">
                  <TriangleAlert />
                  <AlertTitle>Some sections are unavailable</AlertTitle>
                  <AlertDescription>{data.warnings.join(" ")}</AlertDescription>
                </Alert>
              ) : null}

              <Card>
                <CardHeader>
                  <CardTitle className="text-[15px]">Priorities</CardTitle>
                  <CardDescription>Most urgent first. Open one to see the detail.</CardDescription>
                </CardHeader>
                <CardContent>
                  {data.priorities.length === 0 ? (
                    <EmptyState title="No priorities today" description="Nothing needs special attention right now." />
                  ) : (
                    <ol className="space-y-3">
                      {data.priorities.map((priority, index) => (
                        <li key={`${priority.section}-${priority.subject}`} className="flex gap-3 rounded-xl border p-3.5">
                          <span className="flex size-6 shrink-0 items-center justify-center rounded-full bg-primary text-xs font-semibold text-primary-foreground">{index + 1}</span>
                          <div className="min-w-0 flex-1">
                            <div className="flex flex-wrap items-center gap-2">
                              <span className="text-sm font-semibold">{priority.subject}</span>
                              <Badge variant="outline">{humanize(priority.section)}</Badge>
                            </div>
                            <p className="mt-1 text-sm">{priority.action}</p>
                            <p className="mt-0.5 text-xs text-ink-secondary">{priority.why}</p>
                          </div>
                          {priority.drillDown ? (
                            <Link href={drillDownToRoute(priority.drillDown)} prefetch={false} className="shrink-0 self-start text-muted-foreground hover:text-foreground" aria-label={`Open ${priority.subject}`}>
                              <ArrowUpRight className="size-4" />
                            </Link>
                          ) : null}
                        </li>
                      ))}
                    </ol>
                  )}
                </CardContent>
              </Card>

              <div className="grid gap-4 sm:grid-cols-2">
                {data.sections.map((section) => (
                  <Card key={section.key} className="gap-3">
                    <CardHeader>
                      <CardTitle className="text-sm">{section.title}</CardTitle>
                      <CardDescription>{section.headline}</CardDescription>
                    </CardHeader>
                    <CardContent>
                      <ul className="space-y-2 text-xs">
                        {section.items.slice(0, 3).map((item) => (
                          <li key={`${item.subject}-${item.detail}`}>
                            <Link href={drillDownToRoute(item.drillDown)} prefetch={false} className="font-medium hover:underline">
                              {item.subject}
                            </Link>
                            <span className="text-ink-secondary">: {item.detail}</span>
                          </li>
                        ))}
                      </ul>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </>
          )}
        </div>

        <div className="lg:col-span-5">
          <AskCopilot />
        </div>
      </div>
    </>
  );
}
