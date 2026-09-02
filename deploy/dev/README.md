# Local Docker development

Run the control API in a container for early development. This is **not** the fs-dev production path (native systemd + Caddy). Use it when you want a consistent Python 3.12 environment without installing dependencies on the host.

## Quick start

From the repository root:

```bash
docker compose up --build -d
```

**macOS:** use this directory only (`/Users/.../fs-corporation`). Do **not** `git clone` again inside the repo, and do **not** run `deploy/fs-dev/install.sh` (Debian servers only). If something breaks, run:

```bash
./scripts/dev-doctor.sh
# or full integration suite (models, GitHub, VAPID, container dispatch, unit tests):
./scripts/run_all_verifications.sh
```

**Claude model ids:** use ids from your account (e.g. `claude-sonnet-5`). Legacy names like `claude-3-5-haiku-latest` return `LookupError`, not a generic credentials error.

After changing `.env` or Python code, recreate the API container:

```bash
docker compose up -d --force-recreate
```

`scripts/` and `company/` are mounted read-only into the container for local dev, so verify scripts and core changes apply without rebuilding. Rebuild when `pyproject.toml` dependencies change.

| Endpoint | URL |
|---|---|
| Health | http://localhost:8013/api/v1/health |
| CEO desk | http://localhost:8013/ |
| API base | http://localhost:8013 |

Owner bearer token (first run creates it):

```bash
docker compose exec api cat /data/owner.token
```

Paste that token into the CEO desk (browser localStorage `ownerToken`) or companion **Settings**.

## Companion on the host

The container runs the API only. Run the Vite dev server on your machine and point it at the container:

```bash
cd companion
npm install
VITE_API_BASE=http://localhost:8013 npm run dev
```

`FS_CORP_ALLOW_CORS=1` is set in `docker-compose.yml` so the companion preview on port 5173 can call the API.

## Data persistence

SQLite and the owner token live in the named volume `fs-corp-data`. To reset:

```bash
docker compose down -v
```

## Environment

| Variable | Default in compose | Purpose |
|---|---|---|
| `FS_CORP_DATA_DIR` | `/data` | Data directory inside the container |
| `FS_CORP_DB` | `/data/company.db` | SQLite path (also used by Alembic on start) |
| `FS_CORP_ALLOW_CORS` | `1` | Allow companion dev preview origins |
| `FS_CORP_PUBLIC_URL` | `http://localhost:8013` | Pairing QR URLs |

Optional secrets (GitHub, model keys) can be added under `environment:` or an `env_file:` — never commit real values. See [docs/26-owner-live-configuration.md](../../docs/26-owner-live-configuration.md).

### Verify GitHub App

After setting env vars (see `.env` or `deploy/fs-dev/secrets.example.env`):

```bash
python3 scripts/verify_github_app.py
# or in Docker:
docker compose exec api python scripts/verify_github_app.py
curl -H "Authorization: Bearer $(docker compose exec -T api cat /data/owner.token)" \
  http://localhost:8013/api/v1/github/status
```

Enroll a pilot repo (CEO token), then `apply_github_effect` can open a live PR when credentials are configured.

### Verify model provider

```bash
python3 scripts/verify_model_provider.py
curl -H "Authorization: Bearer $(docker compose exec -T api cat /data/owner.token)" \
  http://localhost:8013/api/v1/model/status
```

Set `MODEL_PROVIDER_API_KEY` and/or `ANTHROPIC_API_KEY` in `.env`. Optional: `MODEL_PROVIDER_BASE_URL` for OpenAI-compatible endpoints (Ollama, etc.).

### Verify Web Push (VAPID)

```bash
python3 scripts/generate_vapid_keys.py   # paste output into .env (gitignored)
docker compose up -d --force-recreate
docker compose exec api python scripts/verify_vapid.py
curl -H "Authorization: Bearer $(docker compose exec -T api cat /data/owner.token)" \
  http://localhost:8013/api/v1/push/status
```

### Market feed pilot

CEO-approve a feed, then poll (ingests RSS/Atom items as signals):

```bash
TOKEN=$(docker compose exec -T api cat /data/owner.token)
curl -s -X POST http://localhost:8013/api/v1/feeds \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: feed-github-blog" \
  -d '{"payload":{"id":"github-blog","url":"https://github.blog/feed/"}}' | jq

curl -s -X POST http://localhost:8013/api/v1/feeds/github-blog/poll \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: feed-poll-github-blog" \
  -d '{"payload":{}}' | jq
```

List approved feeds: `GET /api/v1/feeds`

### Container worker dispatch

Build the worker image, rebuild the API (includes Docker CLI + socket mount), then exercise:

```bash
docker compose --profile workers build
docker compose up --build -d --force-recreate

TOKEN=$(docker compose exec -T api cat /data/owner.token)
docker compose exec -T api docker image inspect fs-corporation-worker:local >/dev/null

python3 scripts/exercise_container_dispatch.py \
  --token-file <(docker compose exec -T api cat /data/owner.token) \
  --task-id container-pilot-$(date +%s)
```

Requires project `app` enrolled and Docker Desktop running. On macOS, set `FS_CORP_WORKER_SCRATCH_HOST` in `.env` to the **absolute host path** of `.local/worker-scratch` (the API container cannot bind-mount its own paths to sibling containers).

**OpenAI-compatible pilot**

```bash
docker compose exec api python -c "
import os, json
from company.core import Company
c = Company(os.environ['FS_CORP_DB'])
out = c.invoke_model('pilot', 'Reply with exactly: openai pilot OK', {'profiles': {
  'pilot': {'provider': 'openai', 'model': 'gpt-4o-mini', 'enabled': True,
            'capabilities': ['text'], 'allowed_data': ['public']}}})
print(json.dumps(out, indent=2)); c.close()
"
```

**Claude pilot** — list models your key can access, then pick an `id`:

```bash
docker compose exec api python -c "
import os, httpx
r = httpx.get('https://api.anthropic.com/v1/models',
    headers={'x-api-key': os.environ['ANTHROPIC_API_KEY'], 'anthropic-version': '2023-06-01'})
print([m['id'] for m in r.json().get('data', [])])
"

docker compose exec api python -c "
import os, json
from company.core import Company
c = Company(os.environ['FS_CORP_DB'])
out = c.invoke_model('pilot', 'Reply with exactly: claude pilot OK', {'profiles': {
  'pilot': {'provider': 'anthropic', 'model': 'claude-sonnet-5', 'enabled': True,
            'capabilities': ['text'], 'allowed_data': ['public'],
            'credential_ref': 'ANTHROPIC_API_KEY'}}})
print(json.dumps(out, indent=2)); c.close()
"
```

Use a model `id` from the list (e.g. `claude-sonnet-5`, not legacy `claude-3-5-haiku-latest`).
## Build only

```bash
docker build -f deploy/dev/Dockerfile.api -t fs-corporation-api:dev .
docker run --rm -p 8013:8000 -v fs-corp-data:/data fs-corporation-api:dev
```

## Production

For LAN/Tailscale hosting on an owned Debian host, use [25-fs-dev-deployment.md](../../docs/25-fs-dev-deployment.md) and `deploy/fs-dev/install.sh`. Container workers remain separate (`deploy/fs-dev/Dockerfile.worker`).
