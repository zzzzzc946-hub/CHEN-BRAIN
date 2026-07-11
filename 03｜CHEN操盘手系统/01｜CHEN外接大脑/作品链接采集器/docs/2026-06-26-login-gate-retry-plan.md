# 登录态守门员 V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a minimal login-gate loop so Feishu records that fail with platform login/cookie errors open the right login page and retry automatically after the user logs in.

**Architecture:** Keep the existing `content_link_collector.py` long-connection worker as the owner of record processing. Add small helper functions for platform login URL selection, browser opening with cooldown, and delayed retry scheduling. Do not create a new app or UI in V1.

**Tech Stack:** Python standard library, existing Feishu API helpers, existing LaunchAgent long-connection listener, macOS `open` command.

---

### Task 1: Add Login Gate Helper Tests

**Files:**
- Modify: `test_webhook_helpers.py`
- Modify: `content_link_collector.py`

- [ ] Add tests for `login_url_for_platform`, `should_trigger_login_gate`, and cooldown logic.
- [ ] Expected tests initially fail because helpers do not exist.

### Task 2: Implement Login Gate Helpers

**Files:**
- Modify: `content_link_collector.py`

- [ ] Add `LOGIN_STATUSES = {"需登录", "需Cookie"}`.
- [ ] Add `WAITING_LOGIN_STATUS = "等待登录"`.
- [ ] Add `login_url_for_platform(platform)` returning Douyin/Xiaohongshu home URLs.
- [ ] Add `should_trigger_login_gate(status)` for login/cookie statuses.
- [ ] Add `open_login_page_once(platform, state, lock, cooldown)` using macOS `open` with cooldown.
- [ ] Add `schedule_login_retry(...)` using `threading.Timer`, bounded by config.

### Task 3: Wire Login Gate Into Worker Failures

**Files:**
- Modify: `content_link_collector.py`

- [ ] When `webhook_worker` catches an exception, classify it.
- [ ] If classified as login/cookie, write `等待登录` with a concrete message.
- [ ] Open the platform login page once per cooldown.
- [ ] Schedule retry for the same table/record after `login_retry_interval` seconds.
- [ ] Keep non-login failures unchanged.

### Task 4: Config Defaults and Verification

**Files:**
- Modify: `content_link_collector.py`
- Modify: `config.example.json` if needed

- [ ] Add `login_gate` defaults: enabled true, retry interval 30, max retry attempts 20, open cooldown 300.
- [ ] Run `python3 -m unittest test_webhook_helpers.py`.
- [ ] Run `python3 -m py_compile content_link_collector.py`.
- [ ] Deploy runtime script and restart LaunchAgent.
