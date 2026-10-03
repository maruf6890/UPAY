"use client";
import Link from "next/link";
import { useActionState, useState, useTransition } from "react";
import { Check, LoaderCircle, Sparkles, X } from "lucide-react";
import { explainAlert, reviewAlert, type ExplainResult, type ReviewState } from "@/actions/alerts";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { formatDateTime, formatDay, humanize } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { Alert as AlertType } from "@/types/models";

const initialReview: ReviewState = { ok: false, message: null };

export function AlertCard({ alert }: { alert: AlertType }) {
  const [reviewState, reviewAction, reviewing] = useActionState(reviewAlert, initialReview);
  const [explanation, setExplanation] = useState<ExplainResult | null>(null);
  const [explaining, startExplaining] = useTransition();

  const high = alert.severity === "HIGH";
  const status = alert.review.status;

  function explain() {
    startExplaining(async () => {
      setExplanation(await explainAlert(alert.alertId));
    });
  }

  return (
    <Card className="gap-0 overflow-hidden py-0">
      <div className="flex">
        <div className={cn("w-1.5 shrink-0", high ? "bg-danger" : "bg-warning")} />
        <div className="min-w-0 flex-1 space-y-4 p-5">
          <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
            <Link href={`/agents/${alert.agentCode}`} prefetch={false} className="text-base font-semibold hover:underline">
              {alert.agentCode}
            </Link>
            <span className="text-sm text-muted-foreground">
              {alert.district}, {humanize(alert.archetype)}, flagged {formatDay(alert.date)}
            </span>
            <div className="ml-auto flex items-center gap-2">
              <Badge variant="outline" className="tabular-nums">
                Score {alert.anomalyScore.toFixed(3)}
              </Badge>
              <Badge variant={high ? "danger" : "warning"}>{humanize(alert.severity)}</Badge>
              {status !== "pending" ? <Badge variant={status === "confirmed" ? "success" : "secondary"}>{humanize(status)}</Badge> : null}
            </div>
          </div>

          <ul className="space-y-2">
            {alert.reasons.map((reason) => (
              <li key={reason.signal} className="flex gap-2.5 text-sm">
                <span className="mt-2 size-1.5 shrink-0 rounded-full bg-ai" />
                <span>
                  <span className="font-medium">{reason.label}</span>
                  <span className="text-ink-secondary">: {reason.detail}</span>
                </span>
              </li>
            ))}
          </ul>

          {explanation ? (
            <Alert variant={explanation.generatedBy?.startsWith("langchain") ? "ai" : "default"}>
              <Sparkles />
              <AlertDescription className="text-foreground">
                {explanation.error ? explanation.error : explanation.text}
                {explanation.generatedBy ? <span className="mt-1 block text-[11px] text-muted-foreground">Written by: {explanation.generatedBy}</span> : null}
              </AlertDescription>
            </Alert>
          ) : null}

          {status !== "pending" && alert.review.reviewer ? (
            <p className="text-xs text-muted-foreground">
              Reviewed by {alert.review.reviewer}
              {alert.review.reviewedAt ? ` on ${formatDateTime(alert.review.reviewedAt)}` : ""}
              {alert.review.note ? `. Note: ${alert.review.note}` : ""}
            </p>
          ) : null}

          <div className="flex flex-wrap items-center gap-3 border-t pt-4">
            <Button type="button" variant="ai" size="sm" onClick={explain} disabled={explaining}>
              {explaining ? <LoaderCircle className="animate-spin" /> : <Sparkles />}
              Explain
            </Button>

            <form action={reviewAction} className="ml-auto flex flex-wrap items-center gap-2">
              <input type="hidden" name="alertId" value={alert.alertId} />
              <Input name="note" placeholder="Note (optional)" maxLength={500} className="h-8 w-48 text-xs" />
              <Button type="submit" name="decision" value="dismissed" variant="outline" size="sm" disabled={reviewing}>
                <X /> Dismiss
              </Button>
              <Button type="submit" name="decision" value="confirmed" size="sm" disabled={reviewing}>
                <Check /> Confirm
              </Button>
            </form>
          </div>

          {reviewState.message ? <p className={cn("text-xs", reviewState.ok ? "text-success" : "text-danger")}>{reviewState.message}</p> : null}
        </div>
      </div>
    </Card>
  );
}
