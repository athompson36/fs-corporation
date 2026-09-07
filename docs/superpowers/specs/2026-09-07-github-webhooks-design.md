# Design: GitHub webhook receiver (M4 completion)

Date: 2026-09-07. Status: implementing.

## Goal

Complete the M4 gap “webhooks not wired”: accept GitHub App webhook deliveries with signature verification, replay protection, bounded body size, event allowlist, and durable delivery IDs. Payload content is untrusted task data only — never authority.

## Constraints

- GitHub.com cannot reach LAN `192.168.4.100` or private Tailscale without Funnel/public HTTPS. Local fail-closed receiver + tests are in scope; live delivery is optional owner config.
- No bearer token on the webhook route; HMAC (`X-Hub-Signature-256`) is authentication.
- Fail closed when `GITHUB_WEBHOOK_SECRET` is unset (503).

## Design

1. `company/github_webhooks.py`: verify HMAC-SHA256 over raw bytes; allowlist `ping`, `push`, `pull_request`; max body 1 MiB.
2. `Company.ingest_github_webhook(...)`: persist `github_webhook_deliveries` by `delivery_id`; duplicates return prior row; emit `github.webhook_received` with normalized summary (repo id, event, action) — never store full issue bodies as policy.
3. `POST /api/v1/github/webhooks`: raw `Request.body()`, headers `X-GitHub-Event`, `X-GitHub-Delivery`, `X-Hub-Signature-256`.
4. `GET /api/v1/github/status` adds `webhook_secret_configured` boolean.
5. Deploy stages `GITHUB_WEBHOOK_SECRET` when present in `.env`.

## Non-goals

- Auto-merge / auto-dispatch from webhook text
- Public Funnel setup (document only)
- TailscaleKit / dedicated worker host

## Acceptance

1. Missing secret → 503; bad signature → 401; oversize → 413; unknown event → 422 (or 200 ignored with status `ignored`).
2. Valid signed `ping`/`push`/`pull_request` → 200, row persisted; retry same delivery id → 200, no duplicate row.
3. Unit tests cover verify + ingest + HTTP path.
