# Start here

## 1. Open the project

Extract the ZIP, move `fs-corporation` to your development folder, and open `fs-corporation.code-workspace` in Cursor. Keep the documentation and source together. The starter is independent of your existing project repositories.

## 2. Verify the environment

Use Python 3.12+. No install is required to run from the root. Optional isolation on macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m company demo
python -m unittest discover -s tests -v
```

Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m company demo
python -m unittest discover -s tests -v
```

Expected first demo result: `mode` is `offline_mock`, policy version 2, one task, one completion, one synthetic signal, simulated spend of 150 cents, two rooms, and a valid audit chain. This does not represent real spending or a real delivered application.

### Docker (optional)

Run the control API without a host venv:

```bash
docker compose up --build
curl http://localhost:8013/api/v1/health
docker compose exec api cat /data/owner.token
```

See [deploy/dev/README.md](deploy/dev/README.md).

## 3. Start the Cursor implementation session

Read [AGENTS.md](AGENTS.md), then paste [CURSOR_KICKOFF.md](CURSOR_KICKOFF.md) into Cursor Agent. Cursor rules are included in `.cursor/rules/`. If your Cursor version does not automatically load them, explicitly attach AGENTS.md and the kickoff file.

The next concrete work is **owner-supplied live configuration** — track items in [docs/26-owner-live-configuration.md](docs/26-owner-live-configuration.md) and run `python3 scripts/check_owner_config.py`. For local API development without a host venv, use `docker compose up --build` ([deploy/dev/README.md](deploy/dev/README.md)).

## 4. Configure only what is needed

Templates in `config/` describe departments, providers, enrolled projects, grants, research watchlists, hardware skills and employee development. Loading product configuration into the service is done with `Company.seed_catalog` / `seed_models` / `seed_hardware_skills` / `seed_development_skills` (M2). Editing JSON templates does not automatically change a running company. To exercise the implemented policy API directly, see [examples/governance.py](examples/governance.py).

The company name is **FS-Corporation** and hybrid CEO mode is the default. No specific GitHub repository, paid subscription, deployment target, or daily budget has been authorized or connected by this bundle. Gather those values when implementing the relevant integration rather than blocking local development now.

## 5. Retain your work

Initialize a Git repository when ready, create a private remote you control, and commit the source and docs. Ignore `.local`, `.env`, provider credentials, workspaces and generated artifacts. Keep local data backups separately. The archive deliberately contains no `.git` history or live databases.

## Optional consultant demonstration

Run `python3 -m company.consultant --root .` for a read-only heuristic scan and `python3 -m examples.consultant_proposal` for a synthetic proposal/CEO approval example. No AI calls or fixes occur. See [the consultant design](docs/19-master-consultant.md).
