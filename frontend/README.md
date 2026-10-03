# upay Pulse - Frontend

The web app for the upay Pulse backend (Track 05: agent liquidity intelligence).
Next.js 16 (App Router) + React 19 + Tailwind 4 + shadcn/ui style components + Zustand + Recharts + MapLibre.

**One dashboard, three views.** The same `/dashboard` shows different panels depending on who logs in.

| Role | Sees | Menu |
|---|---|---|
| **Area manager** (DSO) | Cash and e-float risk, riskiest agents, delivery route, alerts, churn, performance, coverage gaps | Dashboard, Liquidity risk, Cash route, Alerts, Agent insights, Coverage map, Copilot |
| **Agent** | Only their own balances, advice (English and Bangla), 24-hour chart, reasons, recent activity | Dashboard |
| **Risk analyst** | Alerts to review, review activity, model quality, performance, where to expand | Dashboard, Alerts, Agent insights, Coverage map, Copilot, Model quality |

---

## 1. Run it

You need the backend running first (it must include the login add-on, with the demo accounts created).

```bash
cd upay-pulse-frontend
cp .env.example .env.local        # API_BASE_URL points at the backend
npm install                       # also copies the map worker files into public/maplibre
npm run dev                       # http://localhost:3000
```

Production build: `npm run build && npm start`.

Log in with a demo account (click the buttons on the login page): `manager`, `agent_ag0142` or `analyst`, password `Pulse@2026`.

> **Tip for demos:** in the backend `.env` set `ACCESS_TOKEN_MINUTES=480`. The app renews expired tokens by itself (section 5), but a long token avoids any renewal during a presentation.

### Environment variables (`.env.local`)

| Variable | Default | Meaning |
|---|---|---|
| `API_BASE_URL` | `http://127.0.0.1:8000` | Backend address. Used **only on the server**, never sent to the browser |
| `COOKIE_SECURE` | `false` | Set `true` when the site is served over HTTPS |
| `SESSION_DAYS` | `7` | Refresh-cookie lifetime. Match `REFRESH_TOKEN_DAYS` in the backend |
| `NEXT_PUBLIC_SHOW_DEMO_LOGINS` | `true` | Shows the three demo buttons on the login page. Set `false` for anything public |
| `NEXT_PUBLIC_MAP_STYLE` | (empty) | Empty = light CARTO basemap. `blank` = plain background (offline). Or a MapLibre style URL |

`NEXT_PUBLIC_*` values are baked in at build time, so rebuild after changing them.

---

## 2. How the code is organised

```
src/
  proxy.ts                  runs before every page: login check + silent token renewal
  app/
    layout.tsx, globals.css root layout, fonts, THE THEME (your tokens + shadcn names)
    (auth)/login/           login page
    (app)/                  everything behind the login (layout = sidebar + top bar)
      dashboard/ risk/ agents/[code]/ route/ alerts/ insights/ coverage/ copilot/ models/
      (each folder: page.tsx, and loading.tsx = the skeleton shown while data loads)
  lib/
    api/
      client.ts             publicApi() and privateApi()  <- the ONLY code that talks to the backend
      convert.ts            snake_case -> camelCase, once, for every response
      errors.ts, safe.ts    ApiError, and safe(): turns a failure into a value
      config.ts             API_BASE_URL
    session.ts, cookies.ts  reading / writing the login cookies
    auth.ts                 getCurrentUser(), requireRole()
    nav.ts                  the menu, per role
    format.ts               money, percent, dates
    drill-down.ts           turns the copilot's backend links into screen links
  services/                 one small typed function per backend endpoint (they call the two functions above)
  actions/                  Server Actions: login, logout, review alert, ask copilot, set demo date
  store/ui-store.ts         Zustand: language (EN/BN) and the mobile menu
  types/                    models.ts (backend data) and widgets.ts (dashboard panels)
  components/
    ui/                     shadcn/ui style components (button, card, table, select, chart ...)
    layout/                 sidebar, top bar, shell
    shared/                 page header, stat card, empty state, error state, skeletons ...
    dashboard/              the dashboard panels, grouped by role
    charts/ map/ alerts/ copilot/ auth/
```

---

## 3. The API layer (read this one first)

Everything that talks to the backend lives in `src/lib/api/client.ts` as **two functions**:

```ts
publicApi<T>(path, options)    // no login needed, for example logging in
privateApi<T>(path, options)   // sends the logged-in user's token
```

Both run **on the server** and use Next.js's built-in `fetch`. The browser never sees the backend address or the token (it is in an httpOnly cookie).
`privateApi` redirects to `/login` when there is no token or the backend says 401.

Every other file goes through a small function in `src/services`:

```ts
// src/services/alerts.ts
export function getAlerts(params) {
  return privateApi<AlertsResponse>("/alerts", { query: { as_of: params.asOf, status: params.status } });
}
```

What the layer does for you:

- **Converter:** responses arrive as `cash_topup_bdt` and are converted once to `cashTopupBdt`. Where the backend is inconsistent (`/risk` says `stockout_prob`, the forecast says `stockout_probability`) a small converter in `services/liquidity.ts` makes them match.
- **Errors:** every failure becomes an `ApiError` with a readable message (`detail` from the backend, validation messages joined, or "Cannot reach the server").
- **`safe()`:** pages call `const { data, error, status } = await safe(() => getRisk(...))` and show an `ErrorState` instead of crashing. Redirects are not swallowed.
- **Loading and empty states:** each route has a `loading.tsx` skeleton, lists have `EmptyState`, and `app/error.tsx` is the last safety net.

**Pages fetch on the server** (async Server Components, no `useEffect`). Changes go through **Server Actions** (`src/actions`), which also call `privateApi`.

### Add a new screen in three steps
1. `src/services/mything.ts`: add `export function getMyThing() { return privateApi<MyThing>("/my-thing"); }` and its type in `src/types/models.ts`.
2. `src/app/(app)/my-thing/page.tsx`: `const { data, error, status } = await safe(() => getMyThing());` then render `data` (or `<ErrorState .../>`).
3. `src/lib/nav.ts`: add a menu item and the roles that may see it.

---

## 4. State

- **Zustand** (`store/ui-store.ts`): the English/Bangla switch (read by `<Bilingual en bn />`) and the mobile menu.
- **The URL**: filters (`?level=HIGH&district=Sylhet`) so the server can fetch the right data and links can be shared.
- **A cookie**: the "demo date" picked in the top bar (set by a Server Action), used by every page.
- Forms use plain React state and Server Actions. There is no validation library; checks are ordinary `if` statements, and the backend's own error messages are shown.

---

## 5. Login and session flow

```
/login  --Server Action--> publicApi POST /auth/login --> httpOnly cookies (access + refresh)
every request --> proxy.ts
   access cookie present            -> continue
   access gone, refresh present     -> POST /auth/refresh, store the new pair, continue (the user notices nothing)
   refresh rejected                 -> clear cookies, go to /login
   no cookies                       -> go to /login
privateApi gets a 401              -> /login?expired=1   (the proxy clears the cookies there, so no redirect loop)
Sign out                           -> POST /auth/logout, clear cookies
```

Behaviour I tested in a real browser: cookies are httpOnly (`document.cookie` is empty), a removed access cookie is renewed from the refresh cookie, a corrupted cookie leads to the login page once without looping, a logged-in user who opens `/login` goes to the dashboard, and sign-out locks the dashboard again.

**Known weak spot:** the backend's refresh tokens work **once**, and re-use ends all sessions. If two requests try to renew the same expired token at the same moment, the second one fails and the user is sent to log in again. The sidebar and tab links turn prefetching off to make this unlikely. If it bothers you in a demo, use the long `ACCESS_TOKEN_MINUTES` tip above.

---

## 6. Roles

The menu and each page are limited by role (`lib/nav.ts`, `requireRole()`), and an agent who opens another agent's page is sent to their own.
**This is a screen rule only.** The backend does not restrict its endpoints by role, so anyone with a token can still call them directly. Do not treat it as security.

---

## 7. Theme

`src/app/globals.css` contains the team's tokens unchanged (`--color-primary: #FFC900`, `--bg-base`, `--success`, `--ai` ...) and maps them to the names shadcn/ui and Tailwind expect (`--primary`, `--card`, `bg-danger-soft` ...).

- Yellow is the brand colour and the main button. Dark text sits on it for contrast.
- Risk badges: high = danger, medium = warning, low = success.
- **Purple (`--ai`) is reserved for text a language model wrote.** When the backend falls back to its template (no Gemini key), the brief, explanations and answers get a neutral look and say which one wrote them.

---

## 8. Components, charts, maps

- **shadcn/ui:** the 17 components in `src/components/ui` are written by hand in the shadcn "new-york" style (the shadcn registry could not be reached while building). They use Radix UI under the hood. `components.json` is included, so `npx shadcn@latest add <name>` works on your machine and may overwrite a file with the official version.
- **Charts:** Recharts, wrapped by `ui/chart.tsx` (the shadcn chart pattern): balance projection (cash/e-float), hourly net outflow with the model's range, anomaly score with thresholds.
- **Maps:** MapLibre GL through `react-map-gl`. mapcn (the shadcn-style map library) could not be installed here, so this uses MapLibre directly, which mapcn is also built on.
  - Coverage map: hexagons coloured by gap type, click for details.
  - Route map: dashed route, numbered stops, depot.
  - The basemap is the light CARTO style. If it cannot load, the map falls back to a plain background and the data still shows.
  - MapLibre 6 needs its worker files served by you. `scripts/copy-map-worker.mjs` copies them to `public/maplibre` on `npm install`, `dev` and `build`.
- **Fonts:** Inter and Noto Sans Bengali, bundled through npm (no Google Fonts request).

---

## 9. What was tested, and what was not

**Tested** (real backend + real browser, headless Chromium, 25 page loads across the 3 roles, no errors): login (wrong password, backend down), every page, role redirects, the Bangla switch, the demo-date switch, confirming an alert (recorded under the logged-in user), the explanation button, the copilot question box, session renewal / corruption / sign-out, and a 390px phone layout. I looked at screenshots of the pages.

**Not tested:**
- A live Gemini answer. Without a key the app shows the backend's template text and labels it.
- The online basemap (the test machine had no internet). The fallback was tested.
- Safari and Firefox (only Chromium).
- Many users at once, and the refresh-token race described in section 5.
- Accessibility with a screen reader, beyond using labelled controls and Radix components.

**Limitations to say out loud:**
- The data is synthetic. The coverage demand and the churn/performance episodes are assumptions.
- The probability shown for stockouts is a ranking aid and tends to read low (the UI says so).
- The cash route is a simple heuristic. It warns when a van would arrive after an agent has run out.
- Language switching covers the advice, reasons and brief. Menu and labels stay in English.

---

## 10. Troubleshooting

| Problem | Fix |
|---|---|
| "The server is not reachable" | Start the backend, and check `API_BASE_URL` in `.env.local` |
| Always sent back to the login page | The backend must have the login add-on, and demo accounts: `python3 -m scripts.create_user demo` |
| Login says "Too many failed attempts" | Wait 15 minutes, or `python3 -m scripts.create_user unlock --username manager` |
| Map is blank grey-blue | Normal when offline. With internet the basemap appears under the hexagons |
| Map pages show "Worker failed to load" | Run `node scripts/copy-map-worker.mjs`, then restart. Check `public/maplibre` exists |
| Bangla text looks like boxes | The bundled Noto Sans Bengali failed to load. Run `npm install` again |
| Changed `.env.local` but nothing changed | Restart `npm run dev`. `NEXT_PUBLIC_*` values need a rebuild |
| Dashboard shows "Some panels are unavailable" | That backend add-on (churn, coverage ...) is missing or not trained. The rest still works |
