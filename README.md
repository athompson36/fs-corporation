# FS-Corporation — Cursor starter

A persistent AI corporation inspired by ChatDev: CEO governance, delegated department heads, mixed-model teams, controlled project forks, market intelligence, and a headquarters that grows with accepted work.

**Deliverable status: v0.3.25 live GitHub pilot + model/feed adapters + Docker dev + container workers (default on fs-dev) + Web Push (VAPID) + fs-dev worker install path.** ChatDev, billed model usage in production workers, and dedicated worker-host egress on `.101` still need owner follow-up.

Start with [START_HERE.md](START_HERE.md), then open [the Cursor workspace](fs-corporation.code-workspace). Copy the prompt from [CURSOR_KICKOFF.md](CURSOR_KICKOFF.md) into Cursor Agent.

## Run in under a minute

From the extracted project root, using Python 3.12 or newer:

```bash
python3 -m company demo
python3 -m company status
python3 -m unittest discover -s tests -v
python3 scripts/check_bundle.py
```

The demo uses the standard library. API, migration, and desk tests need `python3 -m venv .venv && source .venv/bin/activate && pip install -e .`. Then `python3 -m company.service --host 127.0.0.1 --port 8000`.

On Windows use `py -3.12` in place of `python3`. The demo creates `.local/company.db`, approves a sample delegation, produces and accepts a synthetic deliverable, approves construction, and provisions a second virtual room. Rerunning the completed demo leaves its completed state intact. Use `--db .local/another-demo.db` for a fresh run.

## Included

| Component | Status |
|---|---|
| SQLite company state and event history | Implemented locally |
| CEO-approved policy revisions and scoped grants | Implemented locally, including reject/withdraw/rollback |
| Loopback FastAPI control service with bearer tokens | Implemented on 127.0.0.1; not a remote trust boundary |
| Parent/child delegation and delegated approvals | Implemented locally |
| Action-bound, expiring approvals | Implemented for mock actions |
| Integer budgets, reservations, period caps | Implemented for simulated spend |
| Project acceptance and approved room growth | Implemented using synthetic artifact hashes |
| Model profile selection with capability/data filtering | Implemented selector; mock invoke; OpenAI-compatible live invoke when `MODEL_PROVIDER_API_KEY` set |
| Signal ingestion and impact briefs | Implemented; live RSS/Atom poll ingests signals from CEO-approved HTTPS feeds |
| Hardware firmware skill gaps and learning | Implemented locally; live documentation fetch disabled |
| Quality Control inspection before acceptance | Implemented locally; producer and CEO cannot inspect |
| Human Resources development and training | Implemented locally; catalog id `people` |
| Employee hire, training files, goals and trends | Implemented locally; overdue training blocks hired dispatch |
| Master Consultant | Heuristic scan, durable CEO decisions, revision/work-order handoff |
| ChatDev, GitHub and market integration interfaces | GitHub live when App configured; feed poll live for approved RSS/Atom URLs; ChatDev and doc fetch still disabled |
| 14 departments and role prompts | Configuration plus optional catalog seed |
| CEO desk and headquarters projection | Cosmic-glass HTML/SVG desk; 2D + isometric tiles; room selection opens persisted work; companion shares the same tokens |
| Isolated subprocess workers with gateway allowlist | Implemented; fs-dev defaults to container when ready; workers remain `--network none` |
| fs-dev production hosting | systemd + Caddy edge + Docker worker image; `.101` NIC presence reported in workers/status |
| Mobile CEO companion PWA + dashboard APIs | Implemented; LAN HTTPS and Tailscale access documented; Web Push live when VAPID keys configured |
| Live providers inside worker boundary | Model invoke when key set; GitHub when App installed; feed fetch for approved URLs; ChatDev/doc fetch not connected |

## Documentation map

- [Project context and decisions](docs/00-project-context.md)
- [Product requirements and acceptance criteria](docs/01-product-requirements.md)
- [Architecture and trust boundaries](docs/02-architecture.md)
- [Domain model and event contracts](docs/03-data-model.md)
- [CEO governance and delegated authority](docs/04-governance.md)
- [Organization and department operations](docs/05-organization.md)
- [Models, tools and team composition](docs/06-model-routing.md)
- [Pinned ChatDev integration](docs/07-chatdev-integration.md)
- [GitHub forks and Cursor collaboration](docs/08-github-cursor.md)
- [Markets, trends and events](docs/09-market-intelligence.md)
- [Growth, construction and headquarters](docs/10-growth-and-building.md)
- [User experience specification](docs/11-user-experience.md)
- [Security and execution boundaries](docs/12-security.md)
- [Operations, budgets and recovery](docs/13-operations.md)
- [Milestones and implementation backlog](docs/14-roadmap.md)
- [Testing and definition of done](docs/15-testing.md)
- [API contract (loopback)](docs/16-api-contract.md)
- [Source references and upstream decisions](docs/17-sources.md)
- [Handoff and current limitations](docs/18-handoff.md)
- [Master Consultant and improvement proposals](docs/19-master-consultant.md)
- [Hardware projects and skill learning](docs/20-hardware-skills.md)
- [Quality Control and Human Resources](docs/21-quality-hr.md)
- [Employee development, training and performance](docs/22-employee-development.md)
- [Isolated workers and gateway](docs/23-isolated-workers.md)
- [Mobile CEO companion](docs/24-mobile-companion.md)
- [fs-dev deployment](docs/25-fs-dev-deployment.md)
- [Owner live-configuration checklist](docs/26-owner-live-configuration.md)
- [Local Docker development](deploy/dev/README.md)

This bundle contains original starter code, not a vendored ChatDev checkout. The upstream integration baseline is pinned in [upstream.lock.json](config/upstream.lock.json). Licensing and attribution details are in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
