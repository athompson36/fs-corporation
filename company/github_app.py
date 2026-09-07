"""GitHub App authentication and REST helpers. Credentials stay outside prompts and workers."""
from __future__ import annotations
import base64
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
import jwt

GITHUB_API = "https://api.github.com"
_TOKEN_CACHE: dict[str, object] = {"token": None, "expires_at": 0.0}


def github_configured() -> bool:
    app_id = (os.environ.get("GITHUB_APP_ID") or "").strip()
    install_id = (os.environ.get("GITHUB_INSTALLATION_ID") or "").strip()
    key_path = (os.environ.get("GITHUB_PRIVATE_KEY_FILE") or "").strip()
    return bool(app_id and install_id and key_path and Path(key_path).expanduser().is_file())


def _app_id() -> str:
    value = (os.environ.get("GITHUB_APP_ID") or "").strip()
    if not value:
        raise NotImplementedError("GITHUB_APP_ID is not configured")
    return value


def _installation_id() -> str:
    value = (os.environ.get("GITHUB_INSTALLATION_ID") or "").strip()
    if not value:
        raise NotImplementedError("GITHUB_INSTALLATION_ID is not configured")
    return value


def _private_key() -> str:
    path = (os.environ.get("GITHUB_PRIVATE_KEY_FILE") or "").strip()
    if not path or not Path(path).expanduser().is_file():
        raise NotImplementedError("GITHUB_PRIVATE_KEY_FILE is not configured")
    return Path(path).expanduser().read_text()


def make_app_jwt() -> str:
    now = int(time.time())
    payload = {"iat": now - 60, "exp": now + 600, "iss": _app_id()}
    return jwt.encode(payload, _private_key(), algorithm="RS256")


def installation_token(force: bool = False) -> str:
    if not force and _TOKEN_CACHE["token"] and time.time() < float(_TOKEN_CACHE["expires_at"]) - 60:
        return str(_TOKEN_CACHE["token"])
    headers = {
        "Authorization": f"Bearer {make_app_jwt()}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    url = f"{GITHUB_API}/app/installations/{_installation_id()}/access_tokens"
    with httpx.Client(timeout=30.0) as client:
        response = client.post(url, headers=headers)
        response.raise_for_status()
        body = response.json()
    _TOKEN_CACHE["token"] = body["token"]
    expires = body["expires_at"].replace("Z", "+00:00")
    _TOKEN_CACHE["expires_at"] = datetime.fromisoformat(expires).timestamp()
    return str(body["token"])


def app_request(method: str, path: str, *, json_body: dict | None = None, expected: set[int] | None = None):
    """App-level GitHub API calls authenticated with a short-lived App JWT."""
    if not path.startswith("/"):
        path = "/" + path
    headers = {
        "Authorization": f"Bearer {make_app_jwt()}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    with httpx.Client(timeout=60.0, base_url=GITHUB_API) as client:
        response = client.request(method, path, headers=headers, json=json_body)
    if expected and response.status_code in expected:
        return response
    response.raise_for_status()
    if response.status_code == 204:
        return {}
    return response.json()


def github_request(method: str, path: str, *, json_body: dict | None = None, expected: set[int] | None = None):
    if not path.startswith("/"):
        path = "/" + path
    headers = {
        "Authorization": f"Bearer {installation_token()}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    with httpx.Client(timeout=60.0, base_url=GITHUB_API) as client:
        response = client.request(method, path, headers=headers, json=json_body)
    if expected and response.status_code in expected:
        return response
    response.raise_for_status()
    if response.status_code == 204:
        return {}
    return response.json()


def status_summary() -> dict:
    from company.github_webhooks import webhook_secret_configured
    from company.tailscale_funnel import probe_funnel_webhooks
    funnel = probe_funnel_webhooks()
    if not github_configured():
        return {
            "configured": False,
            "live": False,
            "webhook_secret_configured": webhook_secret_configured(),
            "funnel_webhooks": funnel,
        }
    try:
        app = app_request("GET", "/app")
        install = app_request("GET", f"/app/installations/{_installation_id()}")
        installation_token(force=True)
        return {
            "configured": True,
            "live": True,
            "app_slug": app.get("slug"),
            "app_id": app.get("id"),
            "installation_id": install.get("id"),
            "account": (install.get("account") or {}).get("login"),
            "webhook_secret_configured": webhook_secret_configured(),
            "funnel_webhooks": funnel,
        }
    except Exception as exc:
        return {
            "configured": True,
            "live": False,
            "error": str(exc),
            "webhook_secret_configured": webhook_secret_configured(),
            "funnel_webhooks": funnel,
        }


def repo_by_id(repo_id: str) -> dict:
    return github_request("GET", f"/repositories/{repo_id}")


def parse_github_address(raw: str) -> tuple[str, str]:
    """Return (owner, name) from owner/name or https://github.com/owner/name[.git]."""
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError("GitHub address required")
    value = raw.strip().rstrip("/")
    if value.endswith(".git"):
        value = value[:-4]
    lower = value.lower()
    if "://" in value:
        if "github.com/" not in lower:
            raise ValueError("Only github.com addresses are supported")
        path = value.split("github.com/", 1)[1]
        path = path.split("?", 1)[0].split("#", 1)[0]
    else:
        path = value
    parts = [p for p in path.split("/") if p]
    if len(parts) != 2:
        raise ValueError("Expected owner/repo or https://github.com/owner/repo")
    owner, name = parts[0], parts[1]
    if not owner or not name or owner.startswith(".") or name.startswith("."):
        raise ValueError("Invalid owner/repo")
    return owner, name


def installation_account_login() -> str:
    install = app_request("GET", f"/app/installations/{_installation_id()}")
    login = ((install.get("account") or {}).get("login") or "").strip()
    if not login:
        raise NotImplementedError("GitHub App installation account is unavailable")
    return login


def repo_by_full_name(owner: str, name: str) -> dict:
    return github_request("GET", f"/repos/{owner}/{name}")


def ensure_corp_write_repo(owner: str, upstream_name: str) -> tuple[dict, bool]:
    """Ensure same-owner `{upstream_name}-corp` exists. Returns (repo, created)."""
    if not upstream_name or upstream_name.endswith("-corp"):
        raise ValueError("Upstream repo name required (without -corp suffix)")
    corp_name = f"{upstream_name}-corp"
    try:
        return repo_by_full_name(owner, corp_name), False
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code != 404:
            raise
    body = {
        "name": corp_name,
        "private": True,
        "description": f"FS-Corporation write workspace for {owner}/{upstream_name}",
        "auto_init": True,
    }
    try:
        github_request("GET", f"/orgs/{owner}")
        created = github_request("POST", f"/orgs/{owner}/repos", json_body=body)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code != 404:
            raise
        created = github_request("POST", "/user/repos", json_body=body)
    return created, True


def ensure_branch(owner: str, repo: str, branch: str, base_sha: str) -> None:
    path = f"/repos/{owner}/{repo}/git/refs/heads/{branch}"
    try:
        github_request("GET", path)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code != 404:
            raise
        github_request("POST", f"/repos/{owner}/{repo}/git/refs", json_body={
            "ref": f"refs/heads/{branch}",
            "sha": base_sha,
        })


def upsert_file(owner: str, repo: str, branch: str, path: str, content: bytes, message: str) -> dict:
    api_path = f"/repos/{owner}/{repo}/contents/{path.lstrip('/')}"
    body = {
        "message": message,
        "content": base64.b64encode(content).decode("ascii"),
        "branch": branch,
    }
    try:
        existing = github_request("GET", f"{api_path}?ref={branch}")
        if existing.get("sha"):
            body["sha"] = existing["sha"]
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code != 404:
            raise
    return github_request("PUT", api_path, json_body=body)


def open_pull_request(owner: str, repo: str, title: str, head: str, base: str, body: str) -> dict:
    return github_request("POST", f"/repos/{owner}/{repo}/pulls", json_body={
        "title": title,
        "head": head,
        "base": base,
        "body": body,
    })


def merge_pull_request(
    owner: str,
    repo: str,
    pull_number: int,
    *,
    commit_title: str | None = None,
    merge_method: str = "squash",
) -> dict:
    """Merge an open pull request. Requires App permission to merge on the repo."""
    body: dict = {"merge_method": merge_method}
    if commit_title:
        body["commit_title"] = commit_title
    return github_request(
        "PUT", f"/repos/{owner}/{repo}/pulls/{int(pull_number)}/merge", json_body=body)
