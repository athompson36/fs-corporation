# Model assignments and mixed teams

## Stable positions, replaceable models

A position defines responsibilities, required capabilities, memory access and tool permissions. A model profile defines provider, exact model ID, endpoint policy, capabilities, allowed data classifications, context limits, price metadata, credential reference and enabled status. Assignment history preserves which profile/version produced each artifact.

Selection precedence: explicit approved task assignment → position override → department default → company default. The reference `choose_model` implements position override followed by department default with ordered capability/data filtering; task/company fallback is future work.

Never broaden data permissions on fallback. A restricted project must not silently move to a public cloud provider because a local model is unavailable. If no suitable provider is available, block the task with a clear reason.

## Team patterns

- Creator/reviewer: different roles and optionally different models; reviewer sees requirements, artifact and test evidence.
- Creator/critic/arbiter: two bounded review rounds, then an authorized decision or escalation.
- Specialist tool use: reasoning model writes an image brief; a compatible image tool creates assets; a vision-capable reviewer checks the output.
- Cheap-first routing: routine classification uses a smaller eligible model; uncertain cases escalate within the same data and budget policy.

Multiple models do not guarantee independence or truth. Assess disagreement against sources and tests, rather than treating majority voting as proof. Stop conditions must be explicit: accepted, budget exhausted, maximum revisions, blocked dependency or timeout.

## Configuration

`config/models.example.json` uses disabled placeholder profiles instead of guessed current model names. Set exact provider-supported IDs during onboarding. Capabilities in config are claims that must be tested during registration. Chat/text, image generation, audio, video, tool calls and structured outputs require different adapters and validation.

The offline profile is deterministic and free. `choose_model` selects metadata only; it does not perform inference. Ensemble scheduling, rate limits, retries, price refresh, provider health and billing reconciliation are planned.

## Evaluation before promotion

Use a small role-specific benchmark with known acceptance criteria: code tests, source grounding, accessibility, brand adherence or document completeness. Record quality, latency, estimated/actual cost, failure rate and review effort. Compare on the actual role tasks, preserve configuration snapshots, and let the CEO approve material assignment changes.

Context layers: company charter → role instructions → effective delegated scope → approved project brief → relevant approved memory → task inputs → retrieved evidence clearly marked as data. Keep private project context out of other departments/projects unless allowed.
