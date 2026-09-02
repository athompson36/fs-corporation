# Markets, trends and events

## Purpose

Help departments respond to relevant changes without consuming unlimited research budget or changing strategy on every headline. Findings should lead to source-backed decisions, measurable experiments, maintenance work or an explicit decision to take no action.

## Inputs

Official release/security feeds; approved search/news services; user-selected competitor/product pages; permitted analytics; customer feedback; licensed data APIs; GitHub releases and issues. Configure topics, sources, cadence, language/region, freshness horizon, spend cap and recipient departments. No sources are subscribed by this starter.

Use appropriate APIs/feeds and respect access terms. Do not scrape authenticated sources by reusing unrelated credentials. Reputation and source independence affect evidence quality; repeated syndication is not independent corroboration.

## Processing pipeline

Collect → record source and observed timestamps → normalize/canonicalize → deduplicate → classify topic and target projects → assess freshness and relevance → corroborate consequential claims → prepare impact brief → route to authorized head → decision/action → outcome measurement.

Store raw evidence references with access controls, concise summaries, factual claims, citations, confidence basis, missing information, conflicting sources and retention policy. Confidence scores are model estimates, not calibrated probabilities unless actually calibrated.

Freshness is domain-specific: urgent advisories differ from long-term market research. Late-arriving events preserve both publication and observation dates. Repeated events may update evidence, but should not open duplicate tasks. Corrections and retractions link back to affected proposals.

## Example responses

Engineering: platform deprecation → inventory affected projects → migration brief → scoped maintenance task. Hardware skill gaps → assigned employees study approved vendor documentation → independent certification → then firmware work. Marketing: audience trend → relevance check → campaign concept and small experiment. Finance: provider price change → verify official pricing → forecast impact → model-routing recommendation. Sales: relevant public opportunity → eligibility analysis → draft proposal.

No department may infer publishing, outreach or spending permission from a relevant event. If the response is already within its delegation, it may proceed without another CEO request. Otherwise it submits a decision package.

## Proposed impact brief

Signal ID, source URLs, source/observed dates, summary of verified facts, affected projects, impact/severity, uncertainty, alternatives, recommended action, estimated cost, deadline, required authority and review expiry. Include a no-action option when appropriate.

## Cost and noise controls

Deduplicate before inference; cap findings and research rounds; use source/topic filters; apply cooldowns; batch summaries; allow temporary watchlist pause. Research effort must be charged to an approved budget. Do not poll continuously unless the business need justifies it.

## Current core

`ingest_signal` accepts supplied metadata, requires an HTTPS source URL and valid timezone-aware timestamps, classifies records older than 14 days as stale and suppresses exact duplicate source/title/publication combinations. It performs no network fetch, source validation, semantic relevance scoring or automatic action. Signal text has no effect on policy. The demo's example.com event is explicitly synthetic. Hardware skill study reuses this ingest path; live documentation fetch is a separate disabled adapter. See [20-hardware-skills.md](20-hardware-skills.md).

`approve_feed_source` is CEO-only and records an HTTPS URL. `poll_market_feed` requires that enrollment, writes an idempotent `feed_polls` row, fetches RSS/Atom via `MarketFeedAdapter`, ingests up to 50 items as signals, and sets status `applied` with an `ingested` count. Fetch failures set `failed` and raise; retries return the existing row when status is `applied` or `live_unavailable`. Optional `FEED_API_KEY` adds a Bearer header for authenticated feeds.

The production normalizer must replace simple exact-string fingerprinting with canonical event identity, corrections, configurable freshness and source verification.
