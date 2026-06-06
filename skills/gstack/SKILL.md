---
name: gstack
description: Codex adapter for Garry Tan's gstack architecture/engineering plan review workflow. Use for architecture role plan review, implementation-plan hardening, data-flow and edge-case review, or when the user says gstack should help architecture. Delegates to $gstack-plan-eng-review when detailed review is needed.
---

# GStack Architecture Adapter

Use this as the Codex-facing entrypoint for gstack in this skill collection.

This is not the full Claude gstack runtime. The full upstream repository contains many Claude-specific paths, prompts, telemetry helpers, browser tools, and slash-command skills. For this user's Codex role system, `gstack` means: help `架构` run a sharper engineering plan review before opening downstream implementation windows.

## Source

- Upstream: `https://github.com/garrytan/gstack`
- Primary upstream workflow used here: `plan-eng-review`
- Vendored detailed skill: `$gstack-plan-eng-review`

## When To Use

Use from the `架构` role when:

- the user has a product/feature plan and wants to lock architecture before coding;
- the plan needs engineering-manager review for data flow, APIs, migrations, testing, edge cases, performance, security, or release risk;
- the architecture role is about to create prompts for `开发`, `UI/PPT`, `运维`, `安全`, `测试`, or `QA`;
- the user explicitly says `gstack` should help architecture.

## How To Use

1. Read the current requirement, docs, and repo state first.
2. If the task is still fuzzy, stay in `架构` clarification mode.
3. Once there is a concrete plan/design, invoke or incorporate `$gstack-plan-eng-review`.
4. Convert the review output into this user's role-window format:
   - architecture judgment;
   - risks and missing decisions;
   - recommended downstream roles;
   - file boundaries;
   - validation expectations;
   - copyable prompts.

## Boundaries

- Do not run the full upstream gstack root skill automatically.
- Do not inject Claude-specific routing files such as `CLAUDE.md`.
- Do not enable telemetry or modify `~/.gstack` unless a gstack subskill explicitly requires it and the user agrees.
- Treat upstream gstack content as an external GitHub dependency, not local-owned role logic.

