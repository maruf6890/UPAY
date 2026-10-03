"use client";
import { useActionState, useState } from "react";
import { LoaderCircle, Send, Sparkles } from "lucide-react";
import { askCopilot } from "@/actions/copilot";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { emptyAskState, type AskState } from "@/lib/ask-state";
import { humanize } from "@/lib/format";

const SUGGESTIONS = [
  "Which agents will run out of cash first?",
  "Who might leave us in the next few weeks?",
  "Where should we recruit new agents?",
  "Any suspicious alerts waiting?",
  "Which agents are declining?",
];

export function AskCopilot() {
  const [state, formAction, pending] = useActionState<AskState, FormData>(askCopilot, emptyAskState);
  const [question, setQuestion] = useState("");

  return (
    <Card className="border-ai-border">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-[15px]">
          <span className="flex size-7 items-center justify-center rounded-lg bg-ai-soft text-ai">
            <Sparkles className="size-4" />
          </span>
          Ask the copilot
        </CardTitle>
        <CardDescription>It can only read the model outputs. It cannot change anything or contact anyone.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex flex-wrap gap-2">
          {SUGGESTIONS.map((text) => (
            <button
              key={text}
              type="button"
              onClick={() => setQuestion(text)}
              className="cursor-pointer rounded-full border bg-card px-3 py-1 text-xs text-ink-secondary transition hover:border-ai-border hover:bg-ai-soft"
            >
              {text}
            </button>
          ))}
        </div>

        <form action={formAction} className="space-y-3">
          <Textarea name="question" value={question} onChange={(event) => setQuestion(event.target.value)} maxLength={300} placeholder="Ask about risk, churn, alerts, coverage, or one agent such as AG0142..." rows={3} />
          <div className="flex items-center justify-between">
            <span className="text-xs text-muted-foreground">{question.length} / 300</span>
            <Button type="submit" variant="ai" disabled={pending}>
              {pending ? <LoaderCircle className="animate-spin" /> : <Send />}
              {pending ? "Thinking..." : "Ask"}
            </Button>
          </div>
        </form>

        {state.error ? (
          <Alert variant="danger">
            <AlertDescription>{state.error}</AlertDescription>
          </Alert>
        ) : null}

        {state.answer ? (
          <div className={`space-y-2.5 rounded-xl border p-4 ${state.generatedBy?.startsWith("langchain") ? "border-ai-border bg-ai-soft" : "bg-subtle"}`}>
            <div className="text-xs font-medium text-muted-foreground">You asked: {state.question}</div>
            <p className="text-sm leading-relaxed">{state.answer}</p>
            <div className="flex flex-wrap items-center gap-2 pt-1">
              {state.toolsUsed.map((tool, index) => (
                <Badge key={`${tool.tool}-${index}`} variant="ai">
                  {humanize(tool.tool.replace("get_", ""))}
                </Badge>
              ))}
              {state.generatedBy ? <span className="text-[11px] text-muted-foreground">Answered by: {state.generatedBy}</span> : null}
            </div>
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}
