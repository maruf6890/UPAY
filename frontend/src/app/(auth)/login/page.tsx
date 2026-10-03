import { Activity, BellRing, Route, ShieldCheck, Zap } from "lucide-react";
import { LoginForm } from "@/components/auth/login-form";

const HIGHLIGHTS = [
  { icon: Activity, title: "Know who runs short", text: "24-hour cash and e-float forecasts for every agent, with the reasons." },
  { icon: Route, title: "Deliver cash where it matters", text: "A route for the DSO, ordered by how close agents are to running out." },
  { icon: BellRing, title: "Review with a human in the loop", text: "Unusual agent behaviour is flagged. A person always decides." },
];

export default function LoginPage() {
  return (
    <div className="grid min-h-screen lg:grid-cols-[1.05fr_1fr]">
      <section className="relative hidden overflow-hidden bg-gradient-to-br from-brand-soft via-white to-secondary-soft/60 p-12 lg:flex lg:flex-col lg:justify-between">
        <div className="absolute -top-24 -right-24 size-80 rounded-full bg-primary/20 blur-3xl" />
        <div className="relative flex items-center gap-2.5">
          <span className="flex size-10 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-xs">
            <Zap className="size-5" strokeWidth={2.5} />
          </span>
          <span className="text-lg font-semibold tracking-tight">upay Pulse</span>
        </div>

        <div className="relative max-w-lg">
          <h1 className="text-4xl leading-tight font-semibold tracking-tight">Know who runs out of cash, before they do.</h1>
          <p className="mt-4 text-base text-ink-secondary">
            Early warning and cash planning for mobile-money agents, built for upay area managers.
          </p>
          <ul className="mt-10 space-y-5">
            {HIGHLIGHTS.map((item) => {
              const Icon = item.icon;
              return (
                <li key={item.title} className="flex gap-3.5">
                  <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-card shadow-xs ring-1 ring-border">
                    <Icon className="size-5" />
                  </span>
                  <div>
                    <div className="text-sm font-semibold">{item.title}</div>
                    <div className="text-sm text-ink-secondary">{item.text}</div>
                  </div>
                </li>
              );
            })}
          </ul>
        </div>

        <div className="relative flex items-center gap-2 text-xs text-muted-foreground">
          <ShieldCheck className="size-4" />
          Built on synthetic data for the DIU CPC x upay AI Hackathon 2026
        </div>
      </section>

      <section className="flex items-center justify-center bg-background px-6 py-12">
        <LoginForm />
      </section>
    </div>
  );
}
