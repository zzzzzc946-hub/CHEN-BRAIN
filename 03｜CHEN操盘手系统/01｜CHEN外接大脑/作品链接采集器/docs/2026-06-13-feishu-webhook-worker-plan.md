# Feishu Webhook Worker Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the existing 60-second polling collector into a webhook-triggered worker that processes changed Feishu records immediately.

**Architecture:** Add a small Python HTTP server command to `content_link_collector.py`. The HTTP handler answers Feishu URL verification immediately, extracts record IDs from event payloads, enqueues them, and a background worker processes one Feishu row at a time using the existing metadata and Whisper logic.

**Tech Stack:** Python standard library `http.server`, `queue`, `threading`; existing Feishu API helpers; existing local Whisper and yt-dlp pipeline; Cloudflare Tunnel for public webhook URL.

---

### Task 1: Add Single-Record Processing Helpers

**Files:**
- Modify: `content_link_collector.py`

- [ ] Add `get_record(cfg, record_id)` using Feishu Bitable retrieve-record API.
- [ ] Add `process_record(record, cfg, field_types, transcribe=True)` that reuses existing extraction, update, and transcript code for exactly one row.
- [ ] Verify syntax with `PYTHONPYCACHEPREFIX=/tmp/chen-pycache python3 -m py_compile content_link_collector.py`.

### Task 2: Add Webhook Server Command

**Files:**
- Modify: `content_link_collector.py`

- [ ] Add recursive `extract_record_ids(payload)` for Feishu event payloads.
- [ ] Add URL verification response support for `challenge`.
- [ ] Add `cmd_webhook_server` that starts `ThreadingHTTPServer`, enqueues record IDs, and returns quickly.
- [ ] Add CLI command `webhook-server --host 127.0.0.1 --port 8787`.
- [ ] Verify URL verification with a local POST.
- [ ] Verify event enqueue with a local POST containing a known `record_id`.

### Task 3: Add Startup Files

**Files:**
- Create: `启动飞书Webhook服务.command`
- Create: `启动Cloudflare隧道.command`
- Modify: `README.md`

- [ ] Add a command file to start local webhook server.
- [ ] Add a command file to start `cloudflared tunnel --url http://127.0.0.1:8787`.
- [ ] Document the Feishu setup: start server, start tunnel, paste tunnel URL plus `/feishu/webhook` into Feishu event subscription.

### Task 4: Verification

**Files:**
- Modify if needed: `content_link_collector.py`

- [ ] Run Python syntax verification.
- [ ] Start webhook server locally.
- [ ] Send URL verification test payload.
- [ ] Send event test payload for one existing record.
- [ ] Confirm worker logs show queued and processed record.
- [ ] Check whether `cloudflared` exists; if not, report that Cloudflare Tunnel install is the remaining external setup.
