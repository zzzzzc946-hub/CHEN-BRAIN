#!/usr/bin/env python3
"""Minimal Feishu/Lark OpenAPI bridge for Codex.

No third-party dependencies. Configure with .env next to this file.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Tuple

HERE = Path(__file__).resolve().parent
ENV_FILE = HERE / ".env"
TOKEN_CACHE = HERE / ".feishu_token_cache.json"
DEFAULT_BASE_URL = "https://open.feishu.cn"


def load_dotenv(path: Path = ENV_FILE) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise SystemExit(f"Missing {name}. Copy .env.example to .env and fill it.")
    return value


def base_url() -> str:
    return os.environ.get("FEISHU_BASE_URL", DEFAULT_BASE_URL).rstrip("/")


def encode_query(params: Optional[Dict[str, str]]) -> str:
    if not params:
        return ""
    clean = {k: v for k, v in params.items() if v is not None and v != ""}
    return "?" + urllib.parse.urlencode(clean) if clean else ""


def http_json(
    method: str,
    endpoint: str,
    *,
    token: Optional[str] = None,
    query: Optional[Dict[str, str]] = None,
    body: Optional[Dict[str, Any]] = None,
    timeout: int = 30,
) -> Tuple[int, Dict[str, str], Any]:
    if endpoint.startswith("http://") or endpoint.startswith("https://"):
        url = endpoint
    else:
        url = base_url() + endpoint
    url += encode_query(query)

    data = None
    headers = {"Content-Type": "application/json; charset=utf-8"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")

    req = urllib.request.Request(url, data=data, headers=headers, method=method.upper())
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            parsed = json.loads(raw) if raw else {}
            return resp.status, dict(resp.headers), parsed
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(raw) if raw else {"error": raw}
        except json.JSONDecodeError:
            parsed = {"error": raw}
        return e.code, dict(e.headers), parsed
    except urllib.error.URLError as e:
        reason = getattr(e, "reason", e)
        return 0, {}, {
            "code": "NETWORK_ERROR",
            "msg": f"无法连接飞书开放平台：{reason}",
            "hint": "如果你在 Codex 沙盒内运行，这通常是网络/DNS 限制；可在本机 Terminal 或双击 .command 脚本运行。"
        }


def feishu_ok(payload: Any) -> bool:
    return isinstance(payload, dict) and payload.get("code") in (0, None)


def tenant_access_token(force: bool = False) -> str:
    load_dotenv()
    if not force and TOKEN_CACHE.exists():
        try:
            cached = json.loads(TOKEN_CACHE.read_text(encoding="utf-8"))
            if cached.get("tenant_access_token") and cached.get("expires_at", 0) > time.time() + 60:
                return cached["tenant_access_token"]
        except Exception:
            pass

    app_id = require_env("FEISHU_APP_ID")
    app_secret = require_env("FEISHU_APP_SECRET")
    status, _, payload = http_json(
        "POST",
        "/open-apis/auth/v3/tenant_access_token/internal",
        body={"app_id": app_id, "app_secret": app_secret},
    )
    if status >= 400 or not isinstance(payload, dict) or payload.get("code") != 0:
        raise SystemExit("Failed to get tenant_access_token:\n" + json.dumps(payload, ensure_ascii=False, indent=2))

    token = payload["tenant_access_token"]
    expire = int(payload.get("expire", 7200))
    TOKEN_CACHE.write_text(
        json.dumps(
            {"tenant_access_token": token, "expires_at": time.time() + expire},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return token


def parse_query(items: Optional[Iterable[str]]) -> Dict[str, str]:
    query: Dict[str, str] = {}
    for item in items or []:
        if "=" not in item:
            raise SystemExit(f"Bad --query {item!r}; expected key=value")
        key, value = item.split("=", 1)
        query[key] = value
    return query


def parse_body_json(value: Optional[str]) -> Optional[Dict[str, Any]]:
    if not value:
        return None
    text = Path(value[1:]).read_text(encoding="utf-8") if value.startswith("@") else value
    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise SystemExit("--body-json must be a JSON object")
    return parsed


def print_json(payload: Any) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def chunk_text(text: str, size: int = 2500) -> Iterable[str]:
    for i in range(0, len(text), size):
        yield text[i : i + size]


def cmd_auth_test(_: argparse.Namespace) -> None:
    token = tenant_access_token(force=True)
    print(f"OK tenant_access_token acquired. token_prefix={token[:8]}... cache={TOKEN_CACHE}")


def cmd_api(args: argparse.Namespace) -> None:
    token = None if args.no_auth else tenant_access_token()
    status, headers, payload = http_json(
        args.method,
        args.endpoint,
        token=token,
        query=parse_query(args.query),
        body=parse_body_json(args.body_json),
    )
    print_json({"status": status, "payload": payload})


def cmd_send_text(args: argparse.Namespace) -> None:
    load_dotenv()
    receive_id_type = args.receive_id_type or os.environ.get("FEISHU_RECEIVE_ID_TYPE") or "open_id"
    receive_id = args.receive_id or os.environ.get("FEISHU_RECEIVE_ID")
    if not receive_id:
        raise SystemExit("Missing receive_id. Pass --receive-id or set FEISHU_RECEIVE_ID in .env")

    content = json.dumps({"text": args.text}, ensure_ascii=False)
    status, _, payload = http_json(
        "POST",
        "/open-apis/im/v1/messages",
        token=tenant_access_token(),
        query={"receive_id_type": receive_id_type},
        body={"receive_id": receive_id, "msg_type": "text", "content": content},
    )
    print_json({"status": status, "payload": payload})


def cmd_push_md_as_message(args: argparse.Namespace) -> None:
    path = Path(args.file)
    if not path.exists():
        raise SystemExit(f"File not found: {path}")
    text = path.read_text(encoding="utf-8")
    total = (len(text) + args.chunk_size - 1) // args.chunk_size
    for idx, part in enumerate(chunk_text(text, args.chunk_size), start=1):
        prefix = f"【{path.name}｜{idx}/{total}】\n" if total > 1 else f"【{path.name}】\n"
        cmd_send_text(argparse.Namespace(
            text=prefix + part,
            receive_id=args.receive_id,
            receive_id_type=args.receive_id_type,
        ))


def docx_raw_content(document_id: str) -> str:
    status, _, payload = http_json(
        "GET",
        f"/open-apis/docx/v1/documents/{document_id}/raw_content",
        token=tenant_access_token(),
    )
    if status >= 400:
        raise SystemExit("Failed to fetch docx raw_content:\n" + json.dumps(payload, ensure_ascii=False, indent=2))
    data = payload.get("data", {}) if isinstance(payload, dict) else {}
    content = data.get("content") or data.get("raw_content")
    if content is None:
        return json.dumps(payload, ensure_ascii=False, indent=2)
    return str(content)


def cmd_docx_raw(args: argparse.Namespace) -> None:
    content = docx_raw_content(args.document_id)
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(content, encoding="utf-8")
        print(f"Wrote {out}")
    else:
        print(content)


def safe_filename(name: str) -> str:
    bad = '<>:"/\\|?*\n\r\t'
    result = "".join("-" if c in bad else c for c in name).strip()
    return result or "feishu-docx"


def cmd_pull_docx_to_vault(args: argparse.Namespace) -> None:
    title = args.title or args.document_id
    content = docx_raw_content(args.document_id)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{safe_filename(title)}.md"
    if out.exists() and not args.overwrite:
        raise SystemExit(f"Refuse to overwrite existing file: {out}. Add --overwrite if intended.")
    md = f"---\nsource: feishu-docx\ndocument_id: {args.document_id}\nimported_at: {time.strftime('%Y-%m-%d %H:%M:%S')}\n---\n\n# {title}\n\n{content.rstrip()}\n"
    out.write_text(md, encoding="utf-8")
    print(f"Wrote {out}")


def cmd_docx_create(args: argparse.Namespace) -> None:
    load_dotenv()
    folder_token = args.folder_token or os.environ.get("FEISHU_DEFAULT_FOLDER_TOKEN") or ""
    query = {"folder_token": folder_token} if folder_token else None
    status, _, payload = http_json(
        "POST",
        "/open-apis/docx/v1/documents",
        token=tenant_access_token(),
        query=query,
        body={"title": args.title},
    )
    print_json({"status": status, "payload": payload})


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Minimal Feishu/Lark OpenAPI bridge for Codex")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("auth-test", help="get tenant_access_token and cache it")
    s.set_defaults(func=cmd_auth_test)

    s = sub.add_parser("api", help="call any Feishu OpenAPI endpoint")
    s.add_argument("method", choices=["GET", "POST", "PUT", "PATCH", "DELETE"])
    s.add_argument("endpoint", help="e.g. /open-apis/docx/v1/documents/xxx/raw_content")
    s.add_argument("--query", action="append", help="query string item, key=value")
    s.add_argument("--body-json", help="JSON object string, or @path/to/body.json")
    s.add_argument("--no-auth", action="store_true", help="do not attach tenant token")
    s.set_defaults(func=cmd_api)

    s = sub.add_parser("send-text", help="send text message to Feishu")
    s.add_argument("--text", required=True)
    s.add_argument("--receive-id")
    s.add_argument("--receive-id-type")
    s.set_defaults(func=cmd_send_text)

    s = sub.add_parser("push-md-as-message", help="send a Markdown file as chunked Feishu text messages")
    s.add_argument("--file", required=True)
    s.add_argument("--receive-id")
    s.add_argument("--receive-id-type")
    s.add_argument("--chunk-size", type=int, default=2500)
    s.set_defaults(func=cmd_push_md_as_message)

    s = sub.add_parser("docx-raw", help="print or save Feishu Docx raw text content")
    s.add_argument("--document-id", required=True)
    s.add_argument("--out")
    s.set_defaults(func=cmd_docx_raw)

    s = sub.add_parser("pull-docx-to-vault", help="import Feishu Docx raw text as a Markdown note")
    s.add_argument("--document-id", required=True)
    s.add_argument("--title")
    s.add_argument("--out-dir", default="2-日常MAX语料")
    s.add_argument("--overwrite", action="store_true")
    s.set_defaults(func=cmd_pull_docx_to_vault)

    s = sub.add_parser("docx-create", help="create an empty Feishu Docx document")
    s.add_argument("--title", required=True)
    s.add_argument("--folder-token")
    s.set_defaults(func=cmd_docx_create)

    return p


def main() -> None:
    load_dotenv()
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
