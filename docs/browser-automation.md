# Browser Automation Routing

This repository treats browser automation as a routing problem rather than a reason to maintain page-specific JavaScript by default.

## Support Floor

The native route requires the Codex Desktop release dated `2026-06-11` or later and the relevant Browser or Chrome plugin to be visible in the current task. OpenAI's public release notes document the date of the Browser/Chrome Developer mode release but do not publish a stable numeric desktop build floor.

The date alone is not enough. Workspace policy, plan, region, rollout state, plugin installation, and user authorization can still make a browser surface unavailable. The workflow therefore checks capabilities at runtime and fails closed to a named fallback.

## Routing Matrix

| Need | Default surface | Why |
| --- | --- | --- |
| Public page, localhost, visual QA, annotations, downloads | Codex in-app Browser | Shared page view inside the desktop app; isolated browser state |
| Existing Chrome login, open tab, profile, or extension | Codex Chrome extension | Reuses the user's approved Chrome session without copying profile paths or cookies |
| CI, repeatable regression, traces, unattended batch runs | `playwright` | Deterministic CLI/test execution and durable artifacts |
| Platform batch export or a tested command contract | Platform-specific script | Keeps stable bulk behavior that interactive browser actions do not replace |
| Browser-external desktop UI | Computer Use | Handles native GUI surfaces outside browser control |

Prefer a purpose-built connector, API, or CLI before any browser when it supports the complete requested action.

## What Changes

- Interactive browser work no longer starts by writing or loading repository-maintained JavaScript snippets.
- Logged-in tasks use the Chrome extension instead of manually launching Chrome with a repository-owned profile path.
- The in-app Browser is preferred for local frontend review and public pages.
- Existing Playwright and platform scripts remain available for deterministic or batch work.
- Cookie import, local-storage inspection, profile copying, and hidden login-state extraction remain prohibited.

## What Does Not Change

- Browser tools still have an implementation layer; this policy removes custom browser glue from the skill repository, not JavaScript from the web platform.
- Product JavaScript, WebGL assets, HTML interaction code, Playwright test files, and rendering scripts remain valid when they are part of the deliverable or a reproducible test pipeline.
- Publishing and account mutations still require explicit authorization immediately before the action.

## Fail-Closed Checks

Before using the native route, confirm:

1. The Browser or Chrome plugin is available in the current task.
2. The intended surface matches the login-state requirement.
3. The active account and target page are correct.
4. The requested action is read-only or has fresh write authorization.
5. A named Playwright or platform-script fallback exists if the native surface is unavailable.

If any check fails, stop or use the declared fallback and report which capability was missing.
