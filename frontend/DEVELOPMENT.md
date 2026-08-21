# Frontend — Development Tooling

This document describes the developer tooling set up for `frontend/`: linting/formatting,
unit tests, static analysis, architecture rules, mutation testing, end-to-end tests, and
optional error observability. Everything here runs locally, for free, with no external
account required.

Run all commands from the `frontend/` directory.

## Setup

```bash
npm install
```

## Lint & format — Biome

[Biome](https://biomejs.dev) replaces the traditional ESLint + Prettier combo with a single
fast tool. Config: `biome.json`.

```bash
npm run lint        # check formatting + lint rules (read-only)
npm run lint:fix     # check + autofix in place
npm run format       # formatter only, autofix
```

## Unit tests — Vitest + React Testing Library

Config lives in the `test` block of `vite.config.js`; global setup (jest-dom matchers) is in
`src/setupTests.js`. Test files live next to the code they cover, as `*.test.js` /
`*.test.jsx`.

```bash
npm run test           # run once (CI mode)
npm run test:watch     # watch mode for local development
npm run test:coverage  # run with a v8 coverage report
```

Current coverage:
- `src/utils/data.test.js` — pure date/currency helpers (`formatarValor`, `diasAte`,
  `diasRestantes`, `urgente`), including null/undefined/empty edge cases.
- `src/components/Carimbo.test.jsx` — presentational badge component.
- `src/components/Logo.test.jsx` — presentational brand/logo components.

## Unused code & dependencies — Knip

[Knip](https://knip.dev) reports unused files, exports, and dependencies. Config:
`knip.json`.

```bash
npm run knip
```

Knip only **reports** findings — nothing is deleted automatically. Review its output and
decide case by case whether something is genuinely dead code or a false positive (e.g. an
entry point only referenced by `index.html`).

## Architecture rules — dependency-cruiser

[dependency-cruiser](https://github.com/sverweij/dependency-cruiser) enforces import
direction rules. Config: `.dependency-cruiser.cjs`. Current rules:

- `src/components/**` must not import from `src/pages/**` (components are leaves that
  pages depend on, never the other way around).
- No circular dependencies anywhere in `src/`.

```bash
npm run depcruise
```

## Mutation testing — Stryker

[StrykerJS](https://stryker-mutator.io) checks that the unit test suite actually catches
bugs, by injecting small mutations into the source and confirming tests fail. Scoped
deliberately small: it only mutates `src/utils/data.js`, the file with the most thorough
unit tests. Config: `stryker.conf.json`, using the Vitest test runner.

```bash
npm run stryker
```

An HTML report is written to `reports/mutation/mutation.html` after a run.

## End-to-end tests — Playwright

[Playwright](https://playwright.dev) drives a real Chromium browser against the app.
Config: `playwright.config.js`. It automatically starts `npm run dev` on port 5173 before
running tests, so you normally don't need to start the dev server yourself. The backend
does **not** need to be running — the e2e tests only assert on frontend behavior and
deliberately tolerate the console errors caused by an unreachable backend.

```bash
npx playwright install chromium   # first time only, downloads the browser binary
npm run test:e2e
```

Tests live in `e2e/*.spec.js`. `e2e/login.spec.js` covers:
1. An unauthenticated visitor sees the login screen ("Entrar na conta"), no console errors.
2. With a token in `localStorage`, the app shell renders the main nav ("Licitações" tab),
   and navigating between tabs doesn't throw any (non-network) console errors.

## Error observability — Sentry (optional, off by default)

`@sentry/react` is wired up in `src/main.jsx`, but it is a **complete no-op** unless you set
`VITE_SENTRY_DSN`. Vite statically replaces `import.meta.env.VITE_*` at build time, so with
no DSN configured, `Sentry.init(...)` is never called — no network requests, no runtime
cost, nothing to sign up for.

To enable it locally (optional — requires your own free Sentry account, created by you,
never automated by tooling in this repo):

1. Create a free project at [sentry.io](https://sentry.io) (or self-host).
2. Create `frontend/.env.local` (already covered by `.gitignore` conventions — don't commit
   secrets) with:
   ```
   VITE_SENTRY_DSN=https://your-dsn-here@oXXXXXX.ingest.sentry.io/XXXXXXX
   ```
3. Restart `npm run dev` / rebuild. Errors will now be reported to your Sentry project.

Leaving `VITE_SENTRY_DSN` unset is the expected default for local development.
