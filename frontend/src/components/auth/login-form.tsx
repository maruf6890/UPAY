"use client";
import { useActionState, useState } from "react";
import { CircleAlert, LoaderCircle, Zap } from "lucide-react";
import { login, type LoginState } from "@/actions/auth";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const showDemoLogins = process.env.NEXT_PUBLIC_SHOW_DEMO_LOGINS === "true";
const DEMO_PASSWORD = "Pulse@2026";
const DEMO_ACCOUNTS = [
  { label: "Area manager", username: "manager" },
  { label: "Agent", username: "agent_ag0142" },
  { label: "Analyst", username: "analyst" },
];

const initialState: LoginState = { error: null };

export function LoginForm() {
  const [state, formAction, pending] = useActionState(login, initialState);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  function fillDemo(demoUsername: string) {
    setUsername(demoUsername);
    setPassword(DEMO_PASSWORD);
  }

  return (
    <div className="w-full max-w-sm">
      <div className="mb-6 flex items-center gap-2.5 lg:hidden">
        <span className="flex size-9 items-center justify-center rounded-xl bg-primary text-primary-foreground">
          <Zap className="size-5" strokeWidth={2.5} />
        </span>
        <span className="text-lg font-semibold tracking-tight">upay Pulse</span>
      </div>

      <Card className="gap-5 py-7 shadow-sm">
        <CardHeader>
          <CardTitle className="text-xl">Welcome back</CardTitle>
          <CardDescription>Sign in to see today&apos;s liquidity picture.</CardDescription>
        </CardHeader>
        <CardContent>
          <form action={formAction} className="space-y-4">
            {state.error ? (
              <Alert variant="danger">
                <CircleAlert />
                <AlertDescription>{state.error}</AlertDescription>
              </Alert>
            ) : null}

            <div className="space-y-1.5">
              <Label htmlFor="username">Username</Label>
              <Input id="username" name="username" autoComplete="username" value={username} onChange={(event) => setUsername(event.target.value)} placeholder="manager" />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="password">Password</Label>
              <Input id="password" name="password" type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} placeholder="••••••••" />
            </div>

            <Button type="submit" className="w-full" disabled={pending}>
              {pending ? <LoaderCircle className="animate-spin" /> : null}
              {pending ? "Signing in..." : "Sign in"}
            </Button>
          </form>

          {showDemoLogins ? (
            <div className="mt-6 border-t pt-5">
              <p className="mb-2.5 text-xs font-medium text-muted-foreground">Demo accounts (click to fill)</p>
              <div className="flex flex-wrap gap-2">
                {DEMO_ACCOUNTS.map((account) => (
                  <button
                    key={account.username}
                    type="button"
                    onClick={() => fillDemo(account.username)}
                    className="cursor-pointer rounded-full border bg-card px-3 py-1 text-xs font-medium text-ink-secondary transition hover:border-primary hover:bg-brand-soft"
                  >
                    {account.label}
                  </button>
                ))}
              </div>
            </div>
          ) : null}
        </CardContent>
      </Card>
    </div>
  );
}
