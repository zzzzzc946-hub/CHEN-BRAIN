#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
作品链接采集器

把飞书多维表格第一列的抖音 / 小红书 / 视频号链接解析成标题、文案、封面、时长、
互动数和发布时间，再写回原记录。

只使用 Python 标准库，便于直接双击或在本机 Terminal 运行。
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import mimetypes
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


HERE = Path(__file__).resolve().parent
CONFIG_PATH = HERE / "config.json"
ENV_PATH = HERE / ".env"
TOKEN_CACHE = HERE / ".feishu_token_cache.json"
DEFAULT_BASE_URL = "https://open.feishu.cn"


DEFAULT_FIELDS = {
    "url": "作品链接",
    "platform": "平台",
    "title": "作品标题",
    "caption": "文案",
    "cover": "封面",
    "cover_url": "封面图链接",
    "duration": "时长",
    "likes": "点赞",
    "comments": "评论",
    "shares": "分享",
    "published_at": "发布时间",
    "status": "抓取状态",
    "fetched_at": "抓取时间",
    "error": "错误信息",
}

FIELD_SPECS = [
    ("作品链接", 1, None),
    ("平台", 1, None),
    ("作品标题", 1, None),
    ("文案", 1, None),
    ("封面", 1, None),
    ("封面图链接", 1, None),
    ("时长", 1, None),
    ("点赞", 2, None),
    ("评论", 2, None),
    ("分享", 2, None),
    ("发布时间", 1, None),
    ("抓取状态", 1, None),
    ("抓取时间", 1, None),
    ("错误信息", 1, None),
]

TEXT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


def load_dotenv(path: Path = ENV_PATH) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def load_config(path: Path = CONFIG_PATH) -> Dict[str, Any]:
    load_dotenv()
    if path.exists():
        cfg = json.loads(path.read_text(encoding="utf-8"))
    else:
        cfg = {}

    feishu = cfg.setdefault("feishu", {})
    feishu.setdefault("app_id", os.environ.get("FEISHU_APP_ID", ""))
    feishu.setdefault("app_secret", os.environ.get("FEISHU_APP_SECRET", ""))
    feishu.setdefault("app_token", os.environ.get("FEISHU_APP_TOKEN", ""))
    feishu.setdefault("table_id", os.environ.get("FEISHU_TABLE_ID", ""))
    feishu.setdefault("base_url", os.environ.get("FEISHU_BASE_URL", DEFAULT_BASE_URL))

    cfg.setdefault("fields", {})
    cfg["fields"] = {**DEFAULT_FIELDS, **cfg.get("fields", {})}
    cfg.setdefault("platforms", {})
    return cfg


def require_feishu_credentials(cfg: Dict[str, Any]) -> Dict[str, str]:
    feishu = cfg.get("feishu") or {}
    missing = [k for k in ("app_id", "app_secret") if not feishu.get(k)]
    if missing:
        raise SystemExit("缺少飞书配置：" + "、".join(f"feishu.{x}" for x in missing))
    return feishu


def require_feishu(cfg: Dict[str, Any]) -> Dict[str, str]:
    feishu = require_feishu_credentials(cfg)
    missing = [k for k in ("app_token", "table_id") if not feishu.get(k)]
    if missing:
        raise SystemExit("缺少飞书表格配置：" + "、".join(f"feishu.{x}" for x in missing))
    return feishu


def now_text() -> str:
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def base_url(feishu: Dict[str, str]) -> str:
    return (feishu.get("base_url") or DEFAULT_BASE_URL).rstrip("/")


def http_json(
    method: str,
    url: str,
    *,
    token: Optional[str] = None,
    body: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: int = 30,
) -> Tuple[int, Any]:
    final_headers = {"Content-Type": "application/json; charset=utf-8"}
    if headers:
        final_headers.update(headers)
    if token:
        final_headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, headers=final_headers, method=method.upper())
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            return e.code, json.loads(raw)
        except json.JSONDecodeError:
            return e.code, {"code": e.code, "msg": raw[:500]}
    except urllib.error.URLError as e:
        return 0, {"code": "NETWORK_ERROR", "msg": str(getattr(e, "reason", e))}


def tenant_access_token(cfg: Dict[str, Any], force: bool = False) -> str:
    feishu = require_feishu_credentials(cfg)
    if not force and TOKEN_CACHE.exists():
        try:
            cached = json.loads(TOKEN_CACHE.read_text(encoding="utf-8"))
            if cached.get("tenant_access_token") and cached.get("expires_at", 0) > time.time() + 60:
                return cached["tenant_access_token"]
        except Exception:
            pass

    status, payload = http_json(
        "POST",
        base_url(feishu) + "/open-apis/auth/v3/tenant_access_token/internal",
        body={"app_id": feishu["app_id"], "app_secret": feishu["app_secret"]},
    )
    if status >= 400 or not isinstance(payload, dict) or payload.get("code") != 0:
        raise SystemExit("获取 tenant_access_token 失败：\n" + json.dumps(payload, ensure_ascii=False, indent=2))
    token = payload["tenant_access_token"]
    TOKEN_CACHE.write_text(
        json.dumps({"tenant_access_token": token, "expires_at": time.time() + int(payload.get("expire", 7200))}),
        encoding="utf-8",
    )
    return token


def feishu_api(cfg: Dict[str, Any], method: str, endpoint: str, body: Optional[Dict[str, Any]] = None) -> Any:
    feishu = require_feishu(cfg)
    token = tenant_access_token(cfg)
    status, payload = http_json(method, base_url(feishu) + endpoint, token=token, body=body)
    if status >= 400 or not isinstance(payload, dict) or payload.get("code") not in (0, None):
        raise SystemExit("飞书 API 调用失败：\n" + json.dumps(payload, ensure_ascii=False, indent=2))
    return payload


def field_payload(name: str, typ: int, options: Optional[List[str]] = None) -> Dict[str, Any]:
    payload: Dict[str, Any] = {"field_name": name, "type": typ}
    if typ == 3 and options:
        payload["property"] = {"options": [{"name": x} for x in options]}
    return payload


def records_endpoint(cfg: Dict[str, Any]) -> str:
    feishu = require_feishu(cfg)
    app_token = urllib.parse.quote(feishu["app_token"])
    table_id = urllib.parse.quote(feishu["table_id"])
    return f"/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records"


def fields_endpoint(cfg: Dict[str, Any]) -> str:
    feishu = require_feishu(cfg)
    app_token = urllib.parse.quote(feishu["app_token"])
    table_id = urllib.parse.quote(feishu["table_id"])
    return f"/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/fields"


def list_fields(cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    payload = feishu_api(cfg, "GET", fields_endpoint(cfg))
    return (payload.get("data") or {}).get("items") or []


def list_records(cfg: Dict[str, Any], page_size: int = 100) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    page_token = ""
    while True:
        query = {"page_size": str(page_size)}
        if page_token:
            query["page_token"] = page_token
        endpoint = records_endpoint(cfg) + "?" + urllib.parse.urlencode(query)
        payload = feishu_api(cfg, "GET", endpoint)
        data = payload.get("data") or {}
        items.extend(data.get("items") or [])
        if not data.get("has_more"):
            return items
        page_token = data.get("page_token") or ""
        if not page_token:
            return items


def update_record(cfg: Dict[str, Any], record_id: str, fields: Dict[str, Any]) -> None:
    endpoint = records_endpoint(cfg) + "/" + urllib.parse.quote(record_id)
    feishu_api(cfg, "PUT", endpoint, {"fields": fields})


def as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        parts = []
        for item in value:
            if isinstance(item, dict):
                parts.append(str(item.get("text") or item.get("name") or item.get("link") or ""))
            else:
                parts.append(str(item))
        return "".join(parts).strip()
    if isinstance(value, dict):
        return str(value.get("text") or value.get("name") or value.get("link") or "").strip()
    return str(value).strip()


def normalize_url(raw: str) -> str:
    raw = raw.strip()
    m = re.search(r"https?://[^\s)）>]+", raw)
    return m.group(0) if m else raw


def detect_platform(url: str) -> str:
    host = urllib.parse.urlparse(url).netloc.lower()
    if "douyin" in host or "iesdouyin" in host:
        return "抖音"
    if "xiaohongshu" in host or "xhslink" in host:
        return "小红书"
    if "weixin.qq.com" in host or "channels.weixin" in host:
        return "视频号"
    return "未知"


def platform_cookie(cfg: Dict[str, Any], platform: str) -> str:
    info = (cfg.get("platforms") or {}).get(platform) or {}
    env_key = {"抖音": "DOUYIN_COOKIE", "小红书": "XHS_COOKIE", "视频号": "WEIXIN_COOKIE"}.get(platform, "")
    return info.get("cookie") or (os.environ.get(env_key) if env_key else "") or ""


def fetch_text(url: str, cfg: Dict[str, Any], platform: str) -> Tuple[str, str]:
    headers = dict(TEXT_HEADERS)
    cookie = platform_cookie(cfg, platform)
    if cookie:
        headers["Cookie"] = cookie
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=25) as resp:
        final_url = resp.geturl()
        raw = resp.read()
        charset = resp.headers.get_content_charset() or "utf-8"
        return raw.decode(charset, errors="replace"), final_url


def fetch_text_optional(url: str, cfg: Dict[str, Any], platform: str) -> Tuple[str, str]:
    try:
        return fetch_text(url, cfg, platform)
    except Exception:
        return "", url


def douyin_aweme_id(url: str) -> str:
    for pat in (r"/video/(\d+)", r"aweme_id=(\d+)", r"/note/(\d+)"):
        m = re.search(pat, url)
        if m:
            return m.group(1)
    return ""


def fetch_json_url(url: str, cfg: Dict[str, Any], platform: str) -> Optional[Dict[str, Any]]:
    headers = dict(TEXT_HEADERS)
    cookie = platform_cookie(cfg, platform)
    if cookie:
        headers["Cookie"] = cookie
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=25) as resp:
            return json.loads(resp.read().decode("utf-8", errors="replace"))
    except Exception:
        return None


def extract_douyin_api(url: str, cfg: Dict[str, Any]) -> Dict[str, Any]:
    aweme_id = douyin_aweme_id(url)
    if not aweme_id:
        return {}
    api = "https://www.douyin.com/aweme/v1/web/aweme/detail/?" + urllib.parse.urlencode({"aweme_id": aweme_id})
    payload = fetch_json_url(api, cfg, "抖音") or {}
    detail = payload.get("aweme_detail") or {}
    if not detail:
        return {}
    stat = detail.get("statistics") or {}
    video = detail.get("video") or {}
    cover = video.get("cover") or video.get("origin_cover") or video.get("dynamic_cover") or {}
    desc = str(detail.get("desc") or "").strip()
    return {
        "source_url": url,
        "final_url": url,
        "platform": "抖音",
        "title": clean_title(desc[:120]),
        "caption": desc,
        "cover_url": first_url(cover),
        "duration": to_duration(video.get("duration")),
        "likes": to_int(stat.get("digg_count")),
        "comments": to_int(stat.get("comment_count")),
        "shares": to_int(stat.get("share_count")),
        "published_at": to_time_text(detail.get("create_time")),
    }


def merge_meta(primary: Dict[str, Any], fallback: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(primary)
    for key, value in fallback.items():
        if out.get(key) in ("", None, [], {}):
            out[key] = value
    return out


def meta_content(text: str, *names: str) -> str:
    for name in names:
        patterns = [
            rf'<meta[^>]+(?:property|name)=["\']{re.escape(name)}["\'][^>]+content=["\']([^"\']*)["\']',
            rf'<meta[^>]+content=["\']([^"\']*)["\'][^>]+(?:property|name)=["\']{re.escape(name)}["\']',
        ]
        for pat in patterns:
            m = re.search(pat, text, flags=re.I | re.S)
            if m:
                return html.unescape(m.group(1)).strip()
    return ""


def title_tag(text: str) -> str:
    m = re.search(r"<title[^>]*>(.*?)</title>", text, flags=re.I | re.S)
    return html.unescape(re.sub(r"\s+", " ", m.group(1))).strip() if m else ""


def iter_json_objects(text: str) -> Iterable[Any]:
    render = re.search(r'<script[^>]+id=["\']RENDER_DATA["\'][^>]*>(.*?)</script>', text, flags=re.I | re.S)
    if render:
        raw = urllib.parse.unquote(html.unescape(render.group(1)))
        try:
            yield json.loads(raw)
        except Exception:
            pass

    next_data = re.search(r'<script[^>]+id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>', text, flags=re.I | re.S)
    if next_data:
        try:
            yield json.loads(html.unescape(next_data.group(1)))
        except Exception:
            pass

    for m in re.finditer(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', text, flags=re.I | re.S):
        try:
            yield json.loads(html.unescape(m.group(1)))
        except Exception:
            continue


def walk_json(obj: Any) -> Iterable[Tuple[str, Any]]:
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield str(k), v
            yield from walk_json(v)
    elif isinstance(obj, list):
        for item in obj:
            yield from walk_json(item)


def pick_first_json(obj: Any, keys: Iterable[str]) -> Any:
    wanted = {x.lower() for x in keys}
    for k, v in walk_json(obj):
        if k.lower() in wanted and v not in ("", None, [], {}):
            return v
    return None


def to_int(value: Any) -> Optional[int]:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return int(value)
    text = str(value).replace(",", "").strip()
    m = re.search(r"([\d.]+)\s*([w万kK]?)", text)
    if not m:
        return None
    num = float(m.group(1))
    unit = m.group(2).lower()
    if unit in ("w", "万"):
        num *= 10000
    elif unit == "k":
        num *= 1000
    return int(num)


def to_duration(value: Any) -> str:
    if value is None or value == "":
        return ""
    if isinstance(value, str) and ":" in value:
        return value.strip()
    try:
        seconds = float(value)
        if seconds > 10000:
            seconds = seconds / 1000
        seconds = int(round(seconds))
        return f"{seconds // 60:02d}:{seconds % 60:02d}"
    except Exception:
        return str(value).strip()


def to_time_text(value: Any) -> str:
    if value is None or value == "":
        return ""
    if isinstance(value, str):
        value = value.strip()
        if re.search(r"\d{4}[-/年]\d{1,2}", value):
            return value
        if value.isdigit():
            value = int(value)
        else:
            return value
    try:
        ts = int(value)
        if ts > 10_000_000_000:
            ts = ts // 1000
        return dt.datetime.fromtimestamp(ts).strftime("%Y年%m月%d日%H时%M分%S秒")
    except Exception:
        return str(value)


def first_url(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        for item in value:
            got = first_url(item)
            if got:
                return got
    if isinstance(value, dict):
        for key in ("url", "uri", "cover", "coverUrl", "originCover", "dynamicCover", "src"):
            got = first_url(value.get(key))
            if got:
                return got
    return ""


def clean_title(raw: str) -> str:
    raw = re.sub(r"\s+", " ", raw or "").strip()
    raw = re.sub(r"[-_ ]*(抖音|小红书|微信|视频号).*$", "", raw).strip()
    return raw


def extract_from_html(url: str, text: str, final_url: str, platform: str) -> Dict[str, Any]:
    platform = detect_platform(url)
    metas = {
        "title": meta_content(text, "og:title", "twitter:title", "title") or title_tag(text),
        "caption": meta_content(text, "description", "og:description", "twitter:description"),
        "cover_url": meta_content(text, "og:image", "twitter:image"),
    }

    found: Dict[str, Any] = {}
    for obj in iter_json_objects(text):
        title = pick_first_json(obj, ["title", "desc", "description", "noteTitle", "displayTitle"])
        caption = pick_first_json(obj, ["desc", "description", "content", "noteContent", "shareDesc"])
        cover = pick_first_json(obj, ["cover", "coverUrl", "originCover", "dynamicCover", "image", "thumbnailUrl"])
        duration = pick_first_json(obj, ["duration", "durationMillis", "videoDuration"])
        likes = pick_first_json(obj, ["diggCount", "likedCount", "likes", "likeCount", "liked_count"])
        comments = pick_first_json(obj, ["commentCount", "comments", "comment_count"])
        shares = pick_first_json(obj, ["shareCount", "shares", "share_count"])
        published = pick_first_json(obj, ["createTime", "create_time", "publishTime", "time", "datePublished"])
        if title and not found.get("title"):
            found["title"] = title
        if caption and not found.get("caption"):
            found["caption"] = caption
        if cover and not found.get("cover_url"):
            found["cover_url"] = first_url(cover)
        if duration and not found.get("duration"):
            found["duration"] = to_duration(duration)
        if likes is not None and found.get("likes") is None:
            found["likes"] = to_int(likes)
        if comments is not None and found.get("comments") is None:
            found["comments"] = to_int(comments)
        if shares is not None and found.get("shares") is None:
            found["shares"] = to_int(shares)
        if published and not found.get("published_at"):
            found["published_at"] = to_time_text(published)

    title = clean_title(str(found.get("title") or metas["title"] or ""))
    caption = str(found.get("caption") or metas["caption"] or "").strip()
    if not title and caption:
        title = caption[:80]

    return {
        "source_url": url,
        "final_url": final_url,
        "platform": platform,
        "title": title,
        "caption": caption,
        "cover_url": found.get("cover_url") or metas["cover_url"],
        "duration": found.get("duration") or "",
        "likes": found.get("likes"),
        "comments": found.get("comments"),
        "shares": found.get("shares"),
        "published_at": found.get("published_at") or "",
    }


def extract_from_page(url: str, cfg: Dict[str, Any]) -> Dict[str, Any]:
    platform = detect_platform(url)

    if platform == "抖音":
        api_meta = extract_douyin_api(url, cfg)
        if api_meta.get("title") or api_meta.get("caption"):
            return api_meta

    text, final_url = fetch_text(url, cfg, platform)
    meta = extract_from_html(url, text, final_url, platform)

    if platform == "抖音" and not (meta.get("title") or meta.get("caption") or meta.get("cover_url")):
        aweme_id = douyin_aweme_id(url)
        if aweme_id:
            share_url = f"https://www.iesdouyin.com/share/video/{aweme_id}/"
            share_text, share_final = fetch_text_optional(share_url, cfg, platform)
            if share_text:
                meta = merge_meta(meta, extract_from_html(share_url, share_text, share_final, platform))
    return meta


def fetch_binary(url: str, cfg: Dict[str, Any], platform: str) -> Tuple[bytes, str, str]:
    headers = dict(TEXT_HEADERS)
    cookie = platform_cookie(cfg, platform)
    if cookie:
        headers["Cookie"] = cookie
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        content_type = resp.headers.get_content_type() or "image/jpeg"
        ext = mimetypes.guess_extension(content_type) or ".jpg"
        return resp.read(), content_type, ext


def multipart_form_data(fields: Dict[str, str], file_field: str, filename: str, content_type: str, data: bytes) -> Tuple[bytes, str]:
    boundary = "----codex-" + uuid.uuid4().hex
    chunks: List[bytes] = []
    for key, value in fields.items():
        chunks.extend([
            f"--{boundary}\r\n".encode(),
            f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode(),
            str(value).encode(),
            b"\r\n",
        ])
    chunks.extend([
        f"--{boundary}\r\n".encode(),
        f'Content-Disposition: form-data; name="{file_field}"; filename="{filename}"\r\n'.encode(),
        f"Content-Type: {content_type}\r\n\r\n".encode(),
        data,
        b"\r\n",
        f"--{boundary}--\r\n".encode(),
    ])
    return b"".join(chunks), boundary


def upload_cover_to_feishu(cfg: Dict[str, Any], cover_url: str, platform: str) -> Optional[str]:
    """Best-effort upload for attachment/image fields. If Feishu rejects it, caller falls back to URL."""
    if not cover_url:
        return None
    feishu = require_feishu(cfg)
    try:
        data, content_type, ext = fetch_binary(cover_url, cfg, platform)
        body, boundary = multipart_form_data(
            {
                "file_name": "cover" + ext,
                "parent_type": "bitable_image",
                "parent_node": feishu["app_token"],
                "size": str(len(data)),
            },
            "file",
            "cover" + ext,
            content_type,
            data,
        )
        token = tenant_access_token(cfg)
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        }
        req = urllib.request.Request(
            base_url(feishu) + "/open-apis/drive/v1/medias/upload_all",
            data=body,
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=40) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        if payload.get("code") == 0:
            data_obj = payload.get("data") or {}
            file_obj = data_obj.get("file") or {}
            return data_obj.get("file_token") or file_obj.get("file_token")
    except Exception:
        return None
    return None


def build_update_fields(cfg: Dict[str, Any], meta: Dict[str, Any], field_types: Dict[str, int]) -> Dict[str, Any]:
    names = cfg["fields"]
    out: Dict[str, Any] = {
        names["platform"]: meta.get("platform") or "",
        names["title"]: meta.get("title") or "",
        names["caption"]: meta.get("caption") or "",
        names["duration"]: meta.get("duration") or "",
        names["published_at"]: meta.get("published_at") or "",
        names["status"]: "成功",
        names["fetched_at"]: now_text(),
        names["error"]: "",
    }

    for key, field_name in (("likes", names["likes"]), ("comments", names["comments"]), ("shares", names["shares"])):
        if meta.get(key) is not None:
            out[field_name] = meta[key]

    cover_url = meta.get("cover_url") or ""
    if cover_url:
        out[names["cover_url"]] = cover_url
        cover_name = names["cover"]
        cover_type = field_types.get(cover_name)
        if cover_type in (17, 18):
            token = upload_cover_to_feishu(cfg, cover_url, meta.get("platform") or "")
            if token:
                out[cover_name] = [{"file_token": token}]
        else:
            out[cover_name] = cover_url
    return {k: v for k, v in out.items() if k and v is not None}


def status_fields(cfg: Dict[str, Any], status: str, error: str) -> Dict[str, Any]:
    names = cfg["fields"]
    return {
        names["status"]: status,
        names["fetched_at"]: now_text(),
        names["error"]: error[:1000],
    }


def cmd_auth_test(_: argparse.Namespace) -> None:
    cfg = load_config()
    token = tenant_access_token(cfg, force=True)
    print(f"飞书连接成功：tenant_access_token={token[:8]}...（已缓存）")


def cmd_init_fields(_: argparse.Namespace) -> None:
    cfg = load_config()
    existing = {x.get("field_name") for x in list_fields(cfg)}
    created, skipped, failed = [], [], []
    for name, typ, options in FIELD_SPECS:
        if name in existing:
            skipped.append(name)
            continue
        try:
            feishu_api(cfg, "POST", fields_endpoint(cfg), field_payload(name, typ, options))
            created.append(name)
        except SystemExit as e:
            failed.append((name, str(e)))
    print(f"字段初始化完成：新建 {len(created)} 个，已存在 {len(skipped)} 个，失败 {len(failed)} 个")
    if created:
        print("新建字段：" + "、".join(created))
    if failed:
        for name, err in failed:
            print(f"- {name}: {err[:300]}")


def cmd_test_url(args: argparse.Namespace) -> None:
    cfg = load_config()
    meta = extract_from_page(normalize_url(args.url), cfg)
    print(json.dumps(meta, ensure_ascii=False, indent=2))


def should_process(record: Dict[str, Any], cfg: Dict[str, Any], all_rows: bool) -> Tuple[bool, str]:
    fields = record.get("fields") or {}
    names = cfg["fields"]
    url = normalize_url(as_text(fields.get(names["url"])))
    if not url:
        return False, ""
    if all_rows:
        return True, url
    title = as_text(fields.get(names["title"]))
    status = as_text(fields.get(names["status"]))
    if title and status == "成功":
        return False, url
    return True, url


def cmd_sync(args: argparse.Namespace) -> None:
    cfg = load_config()
    names = cfg["fields"]
    field_types = {x.get("field_name"): x.get("type") for x in list_fields(cfg)}
    records = list_records(cfg)
    done = skipped = failed = 0
    for record in records:
        if args.limit and done >= args.limit:
            break
        ok, url = should_process(record, cfg, args.all)
        if not ok:
            skipped += 1
            continue
        record_id = record.get("record_id")
        if not record_id:
            continue
        print(f"抓取：{url}")
        try:
            meta = extract_from_page(url, cfg)
            update_fields = build_update_fields(cfg, meta, field_types)
            if not meta.get("title") and not meta.get("caption"):
                update_fields.update(status_fields(cfg, "部分成功", "已访问链接，但页面没有暴露标题/文案；可能需要登录 cookie 或官方接口。"))
            update_record(cfg, record_id, update_fields)
            done += 1
        except Exception as e:
            failed += 1
            try:
                update_record(cfg, record_id, status_fields(cfg, "失败", str(e)))
            except Exception:
                pass
            print(f"失败：{e}")
    print(f"完成：处理 {done} 条，跳过 {skipped} 条，失败 {failed} 条")
    if names.get("cover") == "封面":
        print("提示：如果你的「封面」字段是附件字段但没有显示图片，请先看「封面图链接」字段。")


def cmd_make_config(_: argparse.Namespace) -> None:
    if CONFIG_PATH.exists():
        raise SystemExit(f"已存在 {CONFIG_PATH}，不覆盖。")
    example = {
        "feishu": {
            "app_id": "cli_在这里填AppID",
            "app_secret": "在这里填AppSecret",
            "app_token": "base后面的bascn或base token",
            "table_id": "tbl开头的数据表ID",
            "base_url": "https://open.feishu.cn",
        },
        "fields": DEFAULT_FIELDS,
        "platforms": {
            "抖音": {"cookie": ""},
            "小红书": {"cookie": ""},
            "视频号": {"cookie": ""},
        },
    }
    CONFIG_PATH.write_text(json.dumps(example, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"已创建 {CONFIG_PATH}")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="飞书多维表格作品链接采集器")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("make-config", help="创建 config.json 样例")
    s.set_defaults(fn=cmd_make_config)

    s = sub.add_parser("auth-test", help="测试飞书凭证和表格权限")
    s.set_defaults(fn=cmd_auth_test)

    s = sub.add_parser("init-fields", help="在飞书表里补齐采集字段")
    s.set_defaults(fn=cmd_init_fields)

    s = sub.add_parser("test-url", help="只测试一个作品链接，不写飞书")
    s.add_argument("url")
    s.set_defaults(fn=cmd_test_url)

    s = sub.add_parser("sync", help="扫描飞书表格，抓取并写回")
    s.add_argument("--limit", type=int, default=0, help="最多处理几条，0 表示不限")
    s.add_argument("--all", action="store_true", help="重新处理所有有链接的记录")
    s.set_defaults(fn=cmd_sync)

    return p


def main() -> None:
    args = build_parser().parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
