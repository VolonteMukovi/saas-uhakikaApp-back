"""One-shot Coolify helper for uhakika API deploy. Secrets stay local; never print them."""
from __future__ import annotations

import json
import os
import secrets
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ENV_PATH = Path(r"D:\projets\coolify-mcp-server\.env")


def load_env(path: Path) -> dict[str, str]:
    vals: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        vals[k.strip()] = v.strip().strip('"').strip("'")
    return vals


def api_base(url: str) -> str:
    url = url.rstrip("/")
    if url.endswith("/api/v1"):
        return url
    if url.endswith("/api"):
        return url + "/v1"
    return url + "/api/v1"


class Coolify:
    def __init__(self, base: str, token: str):
        self.base = base
        self.token = token

    def request(self, method: str, path: str, body: dict | None = None):
        data = None
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json",
        }
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(
            self.base + path, data=data, headers=headers, method=method
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as exc:
            err = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"{method} {path} -> HTTP {exc.code}: {err[:800]}") from exc

    def get(self, path: str):
        return self.request("GET", path)

    def post(self, path: str, body: dict | None = None):
        return self.request("POST", path, body or {})

    def patch(self, path: str, body: dict):
        return self.request("PATCH", path, body)


def as_list(payload):
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("data", "databases", "projects", "applications", "servers"):
            if isinstance(payload.get(key), list):
                return payload[key]
    return []


def find_named(items, name: str):
    name_l = name.lower()
    return [
        i
        for i in items
        if str(i.get("name") or "").lower() == name_l
        or str(i.get("database_name") or "").lower() == name_l
    ]


def main(argv: list[str]) -> int:
    if not ENV_PATH.exists():
        print("Missing coolify .env", file=sys.stderr)
        return 1
    vals = load_env(ENV_PATH)
    token = vals.get("COOLIFY_API_TOKEN") or vals.get("COOLIFY_TOKEN")
    base = api_base(vals["COOLIFY_URL"])
    if not token:
        print("Missing Coolify token", file=sys.stderr)
        return 1
    c = Coolify(base, token)
    cmd = argv[1] if len(argv) > 1 else "inspect"

    if cmd == "inspect":
        servers = as_list(c.get("/servers"))
        projects = as_list(c.get("/projects"))
        databases = as_list(c.get("/databases"))
        print("SERVERS", len(servers))
        for s in servers:
            print(" server", s.get("name"), s.get("uuid"))
        print("PROJECTS", len(projects))
        for p in projects:
            print(" project", p.get("name"), p.get("uuid"))
        print("DATABASES", len(databases))
        for d in databases:
            print(
                " db",
                d.get("name"),
                d.get("uuid"),
                d.get("status"),
                d.get("type") or d.get("database_type"),
            )
        return 0

    if cmd == "db-url":
        uuid = argv[2]
        details = c.get(f"/databases/{uuid}")
        # Prefer fields Coolify exposes; never print password alone.
        url = (
            details.get("internal_db_url")
            or details.get("internal_url")
            or details.get("url")
            or details.get("database_url")
        )
        if not url:
            # Compose from parts without echoing password in logs beyond URL to stdout for piping.
            host = details.get("internal_host") or details.get("hostname") or details.get("host")
            port = details.get("port") or 3306
            user = details.get("username") or details.get("user") or "mysql"
            password = details.get("password") or details.get("root_password") or ""
            name = details.get("database_name") or details.get("name") or "mysql"
            if host:
                password_q = urllib.parse.quote(str(password), safe="")
                url = f"mysql://{user}:{password_q}@{host}:{port}/{name}"
        if not url:
            print("NO_URL_KEYS", sorted(details.keys())[:40], file=sys.stderr)
            return 2
        # Write to a temp file for later use; print only OK + path
        out = Path(r"D:\projets\uhakikaapp\saas-uhakikaApp-back\.cursor\coolify_db_url.txt")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(url, encoding="utf-8")
        print("WROTE_DB_URL", str(out), "len", len(url))
        return 0

    if cmd == "ensure-app":
        # argv: ensure-app project_uuid server_uuid env_name app_name repo branch domain
        project_uuid, server_uuid, env_name, app_name, repo, branch, domain = argv[2:9]
        apps = as_list(c.get("/applications"))
        matches = [
            a
            for a in apps
            if str(a.get("name") or "") == app_name
            and (
                str(a.get("environment_name") or a.get("environment") or "") in ("", env_name)
                or True
            )
        ]
        named = [a for a in apps if str(a.get("name") or "") == app_name]
        if named:
            app = named[0]
            print("EXISTING_APP", app.get("uuid"))
            print(json.dumps({k: app.get(k) for k in ("uuid", "name", "fqdn", "status", "git_repository", "git_branch")}))
            return 0
        body = {
            "project_uuid": project_uuid,
            "server_uuid": server_uuid,
            "environment_name": env_name,
            "git_repository": repo,
            "git_branch": branch,
            "build_pack": "dockerfile",
            "ports_exposes": "8000",
            "name": app_name,
            "domains": domain if domain.startswith("http") else f"https://{domain}",
            "instant_deploy": False,
            "health_check_enabled": True,
            "health_check_path": "/api/i18n-test/",
            "health_check_port": "8000",
            "health_check_method": "GET",
            "health_check_return_code": 200,
            "health_check_scheme": "http",
        }
        created = c.post("/applications/public", body)
        print("CREATED_APP", created.get("uuid") or created)
        return 0

    if cmd == "set-envs":
        app_uuid = argv[2]
        db_url_file = Path(argv[3])
        db_url = db_url_file.read_text(encoding="utf-8").strip()
        secret = secrets.token_urlsafe(48)
        envs = {
            "DATABASE_URL": db_url,
            "DEBUG": "False",
            "SECRET_KEY": secret,
            "ALLOWED_HOSTS": "api.uhakikaapp.store,localhost",
            "FRONTEND_BASE_URL": "https://uhakikaapp.store",
            "FRONTEND_LOCALE_PREFIX": "/fr",
            "PUBLIC_API_BASE_URL": "https://api.uhakikaapp.store",
            "CSRF_TRUSTED_ORIGINS": "https://api.uhakikaapp.store,https://uhakikaapp.store",
            "PAIEMENT_RETURN_BASE_URL": "https://uhakikaapp.store",
            "PAIEMENT_WEBHOOK_BASE_URL": "https://api.uhakikaapp.store",
        }
        existing = as_list(c.get(f"/applications/{app_uuid}/envs"))
        existing_keys = {str(e.get("key")) for e in existing}
        for key, value in envs.items():
            payload = {
                "key": key,
                "value": value,
                "is_preview": False,
                "is_literal": True,
            }
            if key in existing_keys:
                c.patch(f"/applications/{app_uuid}/envs", payload)
                print("UPDATED", key)
            else:
                c.post(f"/applications/{app_uuid}/envs", payload)
                print("CREATED", key)
        print("ENVS_DONE", len(envs))
        return 0

    if cmd == "update-app":
        app_uuid = argv[2]
        body = json.loads(argv[3])
        result = c.patch(f"/applications/{app_uuid}", body)
        print("UPDATED_APP", app_uuid, list(result.keys())[:10] if isinstance(result, dict) else type(result))
        return 0

    if cmd == "deploy":
        app_uuid = argv[2]
        result = c.post(f"/deploy?uuid={urllib.parse.quote(app_uuid)}&force=false")
        print("DEPLOY", json.dumps(result)[:500])
        return 0

    if cmd == "watch-deploy":
        dep_uuid = argv[2]
        import time
        for i in range(90):
            try:
                d = c.get(f"/deployments/{dep_uuid}")
            except Exception as e:
                print("POLL_ERR", e)
                time.sleep(10)
                continue
            status = d.get("status") or d.get("deployment_status") or d.get("current_process_id")
            print(f"poll#{i}", status, d.get("application_name") or d.get("application_uuid") or "")
            s = str(status or "").lower()
            if s in {"finished", "success", "successful", "completed", "done"}:
                print("DONE", json.dumps({k: d.get(k) for k in list(d.keys())[:20]})[:800])
                return 0
            if s in {"failed", "error", "cancelled", "canceled"}:
                print("FAILED", json.dumps({k: d.get(k) for k in list(d.keys())[:30]})[:1200])
                return 2
            time.sleep(10)
        print("TIMEOUT")
        return 3

    if cmd == "logs":
        app_uuid = argv[2]
        lines = int(argv[3]) if len(argv) > 3 else 100
        result = c.get(f"/applications/{app_uuid}/logs?lines={lines}")
        if isinstance(result, dict):
            text = result.get("logs") or result.get("data") or json.dumps(result)[:2000]
        else:
            text = str(result)
        print(str(text)[-4000:])
        return 0

    if cmd == "get-app":
        app_uuid = argv[2]
        app = c.get(f"/applications/{app_uuid}")
        safe = {
            k: app.get(k)
            for k in (
                "uuid",
                "name",
                "fqdn",
                "status",
                "git_repository",
                "git_branch",
                "build_pack",
                "ports_exposes",
                "health_check_path",
            )
        }
        print(json.dumps(safe, indent=2))
        return 0

    print("Unknown command", cmd, file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
