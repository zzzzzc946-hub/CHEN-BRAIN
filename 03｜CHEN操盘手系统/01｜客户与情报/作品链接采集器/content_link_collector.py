#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
作品链接采集器

把飞书多维表格第一列的抖音 / 小红书 / 视频号链接解析成标题、逐字稿、封面、时长、
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
import shutil
import subprocess
import sys
import tempfile
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

TRANSCRIPT_KEYS = [
    "transcript",
    "subtitle",
    "subtitles",
    "captionText",
    "caption_text",
    "asrText",
    "asr_text",
    "voiceText",
    "voice_text",
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
    cfg.setdefault("asr", {})
    cfg["asr"].setdefault("backend", "local")
    cfg["asr"].setdefault("local_model", "base")
    cfg["asr"].setdefault("language", "zh")
    cfg["asr"].setdefault("initial_prompt", "以下是中文短视频口播逐字稿，请保留自然的中文标点、英文专有名词和段落。")
    cfg["asr"].setdefault("format_transcript", True)
    cfg.setdefault("yt_dlp", {})
    cfg["yt_dlp"].setdefault("enabled", True)
    cfg["yt_dlp"].setdefault("cookies_file", str(HERE / "cookies.txt"))
    cfg["yt_dlp"].setdefault("cookies_from_browser", "")
    cfg.setdefault("openai", {})
    cfg["openai"].setdefault("transcribe_model", "gpt-4o-transcribe")
    cfg["openai"].setdefault("language", "zh")
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


def has_ytdlp_cookie(cfg: Dict[str, Any]) -> bool:
    ytdlp_cfg = cfg.get("yt_dlp") or {}
    cookies_file = ytdlp_cfg.get("cookies_file") or str(HERE / "cookies.txt")
    if cookies_file and Path(cookies_file).expanduser().exists():
        return True
    return bool((ytdlp_cfg.get("cookies_from_browser") or "").strip())


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


def pick_video_url(video: Dict[str, Any]) -> str:
    for key in ("play_addr", "download_addr", "playAddr", "downloadAddr"):
        value = video.get(key)
        if isinstance(value, dict):
            for list_key in ("url_list", "urlList", "urls"):
                for item in value.get(list_key) or []:
                    if isinstance(item, str) and item.startswith(("http://", "https://")):
                        return item
            direct = value.get("url")
            if isinstance(direct, str) and direct.startswith(("http://", "https://")):
                return direct
        got = first_url(value)
        if got.startswith(("http://", "https://")):
            return got
    for item in video.get("bit_rate") or []:
        if isinstance(item, dict):
            got = pick_video_url(item.get("play_addr") or {})
            if got:
                return got
    return ""


def is_media_url(value: str) -> bool:
    return isinstance(value, str) and value.startswith(("http://", "https://"))


def media_url_or_empty(meta: Dict[str, Any]) -> str:
    got = meta.get("media_url") or ""
    return got if is_media_url(got) else ""


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
    transcript = pick_first_json(detail, TRANSCRIPT_KEYS)
    return {
        "source_url": url,
        "final_url": url,
        "platform": "抖音",
        "title": clean_title(desc[:120]),
        "caption": str(transcript or "").strip(),
        "cover_url": first_url(cover),
        "duration": to_duration(video.get("duration")),
        "likes": to_int(stat.get("digg_count")),
        "comments": to_int(stat.get("comment_count")),
        "shares": to_int(stat.get("share_count")),
        "published_at": to_time_text(detail.get("create_time")),
        "media_url": pick_video_url(video),
    }


def merge_meta(primary: Dict[str, Any], fallback: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(primary)
    for key, value in fallback.items():
        if out.get(key) in ("", None, [], {}):
            out[key] = value
    return out


def ytdlp_path() -> Optional[str]:
    found = shutil.which("yt-dlp")
    if found:
        return found
    user_bin = Path.home() / "Library" / "Python" / "3.9" / "bin" / "yt-dlp"
    if user_bin.exists():
        return str(user_bin)
    return None


def extract_with_ytdlp(url: str, cfg: Dict[str, Any]) -> Dict[str, Any]:
    ytdlp_cfg = cfg.get("yt_dlp") or {}
    if not ytdlp_cfg.get("enabled", True):
        return {}
    exe = ytdlp_path()
    if not exe:
        return {}
    cmd = [exe, "--dump-json", "--no-warnings", "--no-playlist", url]
    cookies_file = ytdlp_cfg.get("cookies_file") or ""
    if cookies_file and Path(cookies_file).expanduser().exists():
        cmd.extend(["--cookies", str(Path(cookies_file).expanduser())])
    cookies_from_browser = (ytdlp_cfg.get("cookies_from_browser") or "").strip()
    if cookies_from_browser:
        cmd.extend(["--cookies-from-browser", cookies_from_browser])
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=60)
    if result.returncode != 0 or not result.stdout.strip():
        err = (result.stderr or "").strip()
        if "Fresh cookies" in err or "cookies" in err.lower():
            if cookies_from_browser:
                raise RuntimeError(f"yt-dlp 已读取 {cookies_from_browser} 浏览器 Cookie，但抖音要求刷新登录态。请在浏览器里重新打开/登录抖音后再试。")
            raise RuntimeError("yt-dlp 需要登录 Cookie；请配置 cookies.txt 或 cookies_from_browser。")
        return {}
    payload = json.loads(result.stdout.splitlines()[-1])
    formats = payload.get("formats") or []
    media_url = payload.get("url") or ""
    if not is_media_url(media_url):
        for fmt in reversed(formats):
            got = fmt.get("url")
            if is_media_url(got):
                media_url = got
                break
    return {
        "source_url": url,
        "final_url": payload.get("webpage_url") or url,
        "platform": detect_platform(url),
        "title": clean_title(payload.get("title") or payload.get("description") or ""),
        "caption": "",
        "cover_url": payload.get("thumbnail") or "",
        "duration": to_duration(payload.get("duration")),
        "likes": to_int(payload.get("like_count")),
        "comments": to_int(payload.get("comment_count")),
        "shares": to_int(payload.get("repost_count")),
        "published_at": to_time_text(payload.get("timestamp") or payload.get("upload_date")),
        "media_url": media_url,
    }


def load_openai_key(cfg: Dict[str, Any]) -> str:
    load_dotenv()
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if key:
        return key
    raise SystemExit("缺少 OPENAI_API_KEY。请先双击「保存OpenAI密钥.command」保存你手动创建的 key。")


def download_media_file(url: str, cfg: Dict[str, Any], platform: str) -> Path:
    headers = dict(TEXT_HEADERS)
    cookie = platform_cookie(cfg, platform)
    if cookie:
        headers["Cookie"] = cookie
    req = urllib.request.Request(url, headers=headers)
    tmp_dir = Path(tempfile.mkdtemp(prefix="content-asr-"))
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            content_type = resp.headers.get_content_type() or "video/mp4"
            ext = mimetypes.guess_extension(content_type) or ".mp4"
            path = tmp_dir / ("media" + ext)
            with path.open("wb") as f:
                shutil.copyfileobj(resp, f)
            return path
    except Exception:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise


def ffmpeg_path() -> str:
    found = shutil.which("ffmpeg")
    if found:
        return found
    fallback = Path.home() / ".local" / "bin" / "ffmpeg"
    if fallback.exists():
        return str(fallback)
    raise RuntimeError("本机没有找到 ffmpeg，无法从视频抽取音频。")


def extract_audio_file(media_path: Path) -> Path:
    audio_path = media_path.parent / "audio.mp3"
    cmd = [
        ffmpeg_path(),
        "-y",
        "-i",
        str(media_path),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-b:a",
        "48k",
        str(audio_path),
    ]
    result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0 or not audio_path.exists() or audio_path.stat().st_size == 0:
        raise RuntimeError("ffmpeg 抽取音频失败：" + (result.stderr or "")[-500:])
    return audio_path


def multipart_mixed(parts: List[Dict[str, Any]]) -> Tuple[bytes, str]:
    boundary = "----codex-" + uuid.uuid4().hex
    chunks: List[bytes] = []
    for part in parts:
        chunks.append(f"--{boundary}\r\n".encode())
        if "filename" in part:
            chunks.append(
                f'Content-Disposition: form-data; name="{part["name"]}"; filename="{part["filename"]}"\r\n'.encode()
            )
            chunks.append(f"Content-Type: {part.get('content_type') or 'application/octet-stream'}\r\n\r\n".encode())
            chunks.append(part["data"])
        else:
            chunks.append(f'Content-Disposition: form-data; name="{part["name"]}"\r\n\r\n'.encode())
            chunks.append(str(part.get("value", "")).encode("utf-8"))
        chunks.append(b"\r\n")
    chunks.append(f"--{boundary}--\r\n".encode())
    return b"".join(chunks), boundary


def openai_transcribe_file(cfg: Dict[str, Any], path: Path) -> str:
    api_key = load_openai_key(cfg)
    openai_cfg = cfg.get("openai") or {}
    parts = [
        {"name": "model", "value": openai_cfg.get("transcribe_model") or "gpt-4o-transcribe"},
        {"name": "response_format", "value": "json"},
        {
            "name": "file",
            "filename": path.name,
            "content_type": mimetypes.guess_type(str(path))[0] or "video/mp4",
            "data": path.read_bytes(),
        },
    ]
    if openai_cfg.get("language"):
        parts.insert(1, {"name": "language", "value": openai_cfg["language"]})
    body, boundary = multipart_mixed(parts)
    req = urllib.request.Request(
        "https://api.openai.com/v1/audio/transcriptions",
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenAI 转写失败 HTTP {e.code}: {raw[:500]}")
    text = str(payload.get("text") or "").strip()
    if not text:
        raise RuntimeError("OpenAI 转写返回为空")
    return text


def local_whisper_transcribe_file(cfg: Dict[str, Any], path: Path) -> str:
    try:
        import whisper  # type: ignore
    except ImportError:
        raise RuntimeError("本地 Whisper 未安装。请先运行「安装本地Whisper.command」。")
    asr_cfg = cfg.get("asr") or {}
    model_name = asr_cfg.get("local_model") or "base"
    language = asr_cfg.get("language") or "zh"
    model = whisper.load_model(model_name)
    result = model.transcribe(
        str(path),
        language=language,
        fp16=False,
        initial_prompt=asr_cfg.get("initial_prompt") or None,
        condition_on_previous_text=True,
    )
    text = str(result.get("text") or "").strip()
    if not text:
        raise RuntimeError("本地 Whisper 转写返回为空")
    if asr_cfg.get("format_transcript", True):
        text = format_transcript_text(text)
    return text


def format_transcript_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    if not text:
        return ""
    if re.search(r"[。！？；：,.!?]", text):
        text = re.sub(r"\s*([。！？；：,.!?])\s*", r"\1", text)
        text = re.sub(r"([。！？])", r"\1\n", text)
        return re.sub(r"\n{2,}", "\n", text).strip()

    break_words = [
        "大家好", "今天", "首先", "第一", "第二", "第三", "然后", "所以", "但是",
        "其实", "因为", "如果", "比如", "最后", "总结一下", "说白了", "你会发现",
    ]
    for word in break_words:
        text = text.replace(word, "。" + word)
    text = text.lstrip("。")

    chunks: List[str] = []
    current = ""
    for part in re.split(r"(。)", text):
        if not part:
            continue
        current += part
        if part == "。" or len(current) >= 80:
            chunks.append(current.rstrip("。") + "。")
            current = ""
    if current:
        chunks.append(current.rstrip("。") + "。")
    return "\n".join(x.strip() for x in chunks if x.strip())


def transcribe_audio_file(cfg: Dict[str, Any], path: Path) -> str:
    backend = ((cfg.get("asr") or {}).get("backend") or "local").lower()
    if backend == "openai":
        return openai_transcribe_file(cfg, path)
    if backend == "local":
        return local_whisper_transcribe_file(cfg, path)
    if backend == "auto":
        try:
            return local_whisper_transcribe_file(cfg, path)
        except Exception as local_error:
            try:
                return openai_transcribe_file(cfg, path)
            except Exception as openai_error:
                raise RuntimeError(f"本地 Whisper 失败：{local_error}；OpenAI 失败：{openai_error}")
    raise RuntimeError(f"未知 ASR backend：{backend}，可用值：local / openai / auto")


def transcribe_from_meta(cfg: Dict[str, Any], meta: Dict[str, Any]) -> str:
    media_url = media_url_or_empty(meta)
    if not media_url:
        raise RuntimeError("未拿到视频/音频直链；需要平台登录 Cookie 或浏览器采集模式。")
    path = download_media_file(media_url, cfg, meta.get("platform") or "")
    try:
        audio_path = extract_audio_file(path)
        return transcribe_audio_file(cfg, audio_path)
    finally:
        shutil.rmtree(path.parent, ignore_errors=True)


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
        "description": meta_content(text, "description", "og:description", "twitter:description"),
        "cover_url": meta_content(text, "og:image", "twitter:image"),
    }

    found: Dict[str, Any] = {}
    for obj in iter_json_objects(text):
        title = pick_first_json(obj, ["title", "desc", "description", "noteTitle", "displayTitle"])
        transcript = pick_first_json(obj, TRANSCRIPT_KEYS)
        cover = pick_first_json(obj, ["cover", "coverUrl", "originCover", "dynamicCover", "image", "thumbnailUrl"])
        duration = pick_first_json(obj, ["duration", "durationMillis", "videoDuration"])
        likes = pick_first_json(obj, ["diggCount", "likedCount", "likes", "likeCount", "liked_count"])
        comments = pick_first_json(obj, ["commentCount", "comments", "comment_count"])
        shares = pick_first_json(obj, ["shareCount", "shares", "share_count"])
        published = pick_first_json(obj, ["createTime", "create_time", "publishTime", "time", "datePublished"])
        if title and not found.get("title"):
            found["title"] = title
        if transcript and not found.get("caption"):
            found["caption"] = transcript
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
    description = str(metas["description"] or "").strip()
    caption = str(found.get("caption") or "").strip()
    if not title and description:
        title = description[:80]

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
    if not (meta.get("title") and (meta.get("media_url") or platform != "抖音")):
        try:
            meta = merge_meta(meta, extract_with_ytdlp(url, cfg))
        except RuntimeError as e:
            if not meta.get("title"):
                raise
            meta["yt_dlp_error"] = str(e)
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


def keep_existing_fields(fields: Dict[str, Any], field_types: Dict[str, int]) -> Dict[str, Any]:
    return {k: v for k, v in fields.items() if k in field_types}


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
    return keep_existing_fields({k: v for k, v in out.items() if k and v is not None}, field_types)


def status_fields(cfg: Dict[str, Any], status: str, error: str, field_types: Optional[Dict[str, int]] = None) -> Dict[str, Any]:
    names = cfg["fields"]
    fields = {
        names["status"]: status,
        names["fetched_at"]: now_text(),
        names["error"]: error[:1000],
    }
    return keep_existing_fields(fields, field_types) if field_types is not None else fields


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
    try:
        meta = extract_from_page(normalize_url(args.url), cfg)
    except Exception as e:
        meta = {
            "source_url": normalize_url(args.url),
            "platform": detect_platform(normalize_url(args.url)),
            "title": "",
            "caption": "",
            "error": str(e),
        }
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
    error = as_text(fields.get(names["error"]))
    if "Cookie" in error and not has_ytdlp_cookie(cfg):
        return False, url
    return True, url


def cmd_sync(args: argparse.Namespace) -> None:
    cfg = load_config()
    names = cfg["fields"]
    field_types = {x.get("field_name"): x.get("type") for x in list_fields(cfg)}
    records = list_records(cfg)
    done = skipped = failed = attempted = 0
    for record in records:
        if args.limit and attempted >= args.limit:
            break
        ok, url = should_process(record, cfg, args.all)
        if not ok:
            skipped += 1
            continue
        record_id = record.get("record_id")
        if not record_id:
            continue
        print(f"抓取：{url}", flush=True)
        try:
            meta = extract_from_page(url, cfg)
            update_fields = build_update_fields(cfg, meta, field_types)
            if not meta.get("title"):
                update_fields.update(status_fields(cfg, "部分成功", "已访问链接，但页面没有暴露标题；可能需要登录 cookie 或官方接口。", field_types))
            elif not meta.get("caption"):
                update_fields.update(status_fields(cfg, "部分成功", "已抓到作品信息，但未抓到视频逐字稿；需要字幕/ASR能力。", field_types))
            if update_fields:
                update_record(cfg, record_id, update_fields)
            done += 1
        except Exception as e:
            failed += 1
            try:
                fields = status_fields(cfg, "失败", str(e), field_types)
                if fields:
                    update_record(cfg, record_id, fields)
            except Exception:
                pass
            print(f"失败：{e}", flush=True)
    print(f"完成：处理 {done} 条，跳过 {skipped} 条，失败 {failed} 条", flush=True)
    if names.get("cover") == "封面":
        print("提示：如果你的「封面」字段是附件字段但没有显示图片，请先看「封面图链接」字段。")


def cmd_clean_fake_transcripts(args: argparse.Namespace) -> None:
    cfg = load_config()
    names = cfg["fields"]
    field_types = {x.get("field_name"): x.get("type") for x in list_fields(cfg)}
    if names["caption"] not in field_types:
        raise SystemExit(f"表里没有字段：{names['caption']}")
    records = list_records(cfg)
    cleaned = skipped = 0
    for record in records:
        fields = record.get("fields") or {}
        title = as_text(fields.get(names["title"]))
        caption = as_text(fields.get(names["caption"]))
        if title and caption and title == caption:
            update = keep_existing_fields({
                names["caption"]: "",
                names["status"]: "部分成功",
                names["fetched_at"]: now_text(),
                names["error"]: "已清空错误文案：原内容只是作品标题/描述，不是视频逐字稿。",
            }, field_types)
            update_record(cfg, record["record_id"], update)
            cleaned += 1
            print(f"清空：{title[:60]}", flush=True)
        else:
            skipped += 1
    print(f"完成：清空 {cleaned} 条，跳过 {skipped} 条", flush=True)


def cmd_transcribe_url(args: argparse.Namespace) -> None:
    cfg = load_config()
    meta = extract_from_page(normalize_url(args.url), cfg)
    text = transcribe_from_meta(cfg, meta)
    print(text)


def cmd_transcribe_missing(args: argparse.Namespace) -> None:
    cfg = load_config()
    names = cfg["fields"]
    field_types = {x.get("field_name"): x.get("type") for x in list_fields(cfg)}
    records = list_records(cfg)
    done = skipped = failed = attempted = 0
    for record in records:
        if args.limit and attempted >= args.limit:
            break
        fields = record.get("fields") or {}
        url = normalize_url(as_text(fields.get(names["url"])))
        title = as_text(fields.get(names["title"]))
        caption = as_text(fields.get(names["caption"]))
        error = as_text(fields.get(names["error"]))
        if not url or (caption and not args.all):
            skipped += 1
            continue
        if not args.all and not title and "Cookie" in error:
            skipped += 1
            continue
        attempted += 1
        print(f"转写：{url}", flush=True)
        try:
            meta = extract_from_page(url, cfg)
            text = transcribe_from_meta(cfg, meta)
            update = keep_existing_fields({
                names["caption"]: text,
                names["status"]: "成功",
                names["fetched_at"]: now_text(),
                names["error"]: "",
            }, field_types)
            update_record(cfg, record["record_id"], update)
            done += 1
        except Exception as e:
            failed += 1
            update = keep_existing_fields({
                names["status"]: "部分成功",
                names["fetched_at"]: now_text(),
                names["error"]: f"逐字稿转写未完成：{e}",
            }, field_types)
            try:
                update_record(cfg, record["record_id"], update)
            except Exception:
                pass
            print(f"失败：{e}", flush=True)
    print(f"完成：转写 {done} 条，跳过 {skipped} 条，失败 {failed} 条", flush=True)


def cmd_format_transcripts(args: argparse.Namespace) -> None:
    cfg = load_config()
    names = cfg["fields"]
    field_types = {x.get("field_name"): x.get("type") for x in list_fields(cfg)}
    records = list_records(cfg)
    done = skipped = 0
    for record in records:
        if args.limit and done >= args.limit:
            break
        fields = record.get("fields") or {}
        caption = as_text(fields.get(names["caption"]))
        if not caption:
            skipped += 1
            continue
        formatted = format_transcript_text(caption)
        if formatted == caption:
            skipped += 1
            continue
        update_record(cfg, record["record_id"], keep_existing_fields({
            names["caption"]: formatted,
            names["fetched_at"]: now_text(),
        }, field_types))
        done += 1
    print(f"完成：格式化 {done} 条，跳过 {skipped} 条", flush=True)


def cmd_watch(args: argparse.Namespace) -> None:
    cfg = load_config()
    print(f"开始监听飞书表格：每 {args.interval} 秒扫描一次。按 Ctrl+C 停止。", flush=True)
    while True:
        try:
            cmd_sync(argparse.Namespace(limit=args.sync_limit, all=False))
            cmd_transcribe_missing(argparse.Namespace(limit=args.transcribe_limit, all=False))
        except KeyboardInterrupt:
            print("已停止监听。", flush=True)
            return
        except Exception as e:
            print(f"监听循环出错：{e}", flush=True)
        time.sleep(args.interval)


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

    s = sub.add_parser("clean-fake-transcripts", help="清空与标题完全相同的伪逐字稿")
    s.set_defaults(fn=cmd_clean_fake_transcripts)

    s = sub.add_parser("transcribe-url", help="测试单个链接的音频转写，不写飞书")
    s.add_argument("url")
    s.set_defaults(fn=cmd_transcribe_url)

    s = sub.add_parser("transcribe-missing", help="转写飞书表格里文案为空的记录")
    s.add_argument("--limit", type=int, default=0, help="最多处理几条，0 表示不限")
    s.add_argument("--all", action="store_true", help="重转所有有链接的记录")
    s.set_defaults(fn=cmd_transcribe_missing)

    s = sub.add_parser("format-transcripts", help="给已有逐字稿做轻量标点和分段")
    s.add_argument("--limit", type=int, default=0, help="最多处理几条，0 表示不限")
    s.set_defaults(fn=cmd_format_transcripts)

    s = sub.add_parser("watch", help="持续监听飞书表格新链接并自动抓取/转写")
    s.add_argument("--interval", type=int, default=60, help="扫描间隔秒数")
    s.add_argument("--sync-limit", type=int, default=20, help="每轮最多抓取元数据条数")
    s.add_argument("--transcribe-limit", type=int, default=1, help="每轮最多转写条数")
    s.set_defaults(fn=cmd_watch)

    return p


def main() -> None:
    args = build_parser().parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
