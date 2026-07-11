# Orange Desktop Collector MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local CHEN orange content collector app that opens in the browser, manages local collection tables, scrapes single links through the existing collector pipeline, saves results locally, and exports CSV.

**Architecture:** Add a small local API/UI server to the existing standard-library Python collector so the proven scraping, login, ASR, and error-classification logic is reused rather than rebuilt. Store only structured results in SQLite, and serve a single embedded HTML/CSS/JS interface with the orange mascot, platform cards, table management, view switching, and export controls.

**Tech Stack:** Python standard library (`http.server`, `sqlite3`, `csv`, `webbrowser`, `threading`), existing `content_link_collector.py` scraping helpers, browser-hosted HTML/CSS/JS, SQLite.

---

## File Structure

- Modify: `03｜CHEN操盘手系统/01｜CHEN外接大脑/作品链接采集器/content_link_collector.py`
  - Add SQLite helpers for desktop collection tables and items.
  - Add single-link desktop scrape orchestration that reuses `extract_from_page()` and `transcribe_from_meta()`.
  - Add embedded desktop HTML UI and local HTTP API handler.
  - Add `desktop-app` CLI command.
- Modify: `03｜CHEN操盘手系统/01｜CHEN外接大脑/作品链接采集器/test_webhook_helpers.py`
  - Add focused tests for local DB table creation, item persistence, and scrape orchestration with mocked scraper/ASR.
- Create: `03｜CHEN操盘手系统/01｜CHEN外接大脑/作品链接采集器/启动橙子内容采集助手.command`
  - Double-click launcher for the local desktop-style app.

## Task 1: Local SQLite Store

**Files:**
- Modify: `content_link_collector.py`
- Test: `test_webhook_helpers.py`

- [ ] **Step 1: Write failing tests**

Add tests that create a temporary SQLite DB, initialize it, create a table, and save/list one item.

```python
def test_desktop_db_creates_default_and_custom_tables(self):
    collector = load_collector()
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "desktop.sqlite3"
        collector.desktop_db_init(db)
        tables = collector.desktop_list_tables(db)
        self.assertEqual(tables[0]["name"], "默认采集表")
        custom = collector.desktop_create_table(db, "抖音选题库", "抖音")
        self.assertEqual(custom["name"], "抖音选题库")
        self.assertEqual(custom["default_platform"], "抖音")


def test_desktop_db_saves_and_lists_items(self):
    collector = load_collector()
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "desktop.sqlite3"
        collector.desktop_db_init(db)
        table = collector.desktop_list_tables(db)[0]
        saved = collector.desktop_save_item(db, table["id"], {
            "platform": "抖音",
            "source_url": "https://www.douyin.com/video/1",
            "source_type": "single",
            "title": "标题",
            "caption": "逐字稿",
            "cover_url": "https://example.com/cover.jpg",
            "duration": "01:00",
            "likes": 1,
            "comments": 2,
            "shares": 3,
            "published_at": "2026年01月01日00时00分00秒",
            "status": "成功",
            "error": "",
            "raw_metadata_json": "{}",
        })
        items = collector.desktop_list_items(db, table["id"])
        self.assertEqual(items[0]["id"], saved["id"])
        self.assertEqual(items[0]["title"], "标题")
```

- [ ] **Step 2: Run tests and confirm failure**

Run:

```bash
PYTHONPYCACHEPREFIX=/tmp/chen_collector_pycache python3 -m unittest test_webhook_helpers.py
```

Expected: FAIL because `desktop_db_init` and related functions do not exist.

- [ ] **Step 3: Implement store helpers**

Add `sqlite3` import, schema constants, and helpers:

```python
DESKTOP_DB_PATH = HERE / "desktop_collector.sqlite3"

def desktop_db_init(db_path: Path = DESKTOP_DB_PATH) -> None:
    ...

def desktop_list_tables(db_path: Path = DESKTOP_DB_PATH) -> List[Dict[str, Any]]:
    ...

def desktop_create_table(db_path: Path, name: str, default_platform: str = "抖音") -> Dict[str, Any]:
    ...

def desktop_save_item(db_path: Path, table_id: str, item: Dict[str, Any]) -> Dict[str, Any]:
    ...

def desktop_list_items(db_path: Path, table_id: str = "") -> List[Dict[str, Any]]:
    ...
```

- [ ] **Step 4: Run tests and confirm pass**

Run the same unittest command. Expected: PASS.

## Task 2: Local Scrape Orchestration

**Files:**
- Modify: `content_link_collector.py`
- Test: `test_webhook_helpers.py`

- [ ] **Step 1: Write failing scrape test**

Add a test that monkeypatches `extract_from_page` and `transcribe_from_meta`, then verifies one URL is saved with transcript and clear status.

```python
def test_desktop_scrape_single_url_reuses_existing_scraper_and_asr(self):
    collector = load_collector()
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "desktop.sqlite3"
        collector.desktop_db_init(db)
        table = collector.desktop_list_tables(db)[0]
        collector.extract_from_page = lambda url, cfg: {
            "platform": "抖音",
            "content_type": "video",
            "source_url": url,
            "title": "视频标题",
            "caption": "",
            "cover_url": "https://example.com/cover.jpg",
            "duration": "00:30",
            "likes": 10,
            "comments": 2,
            "shares": 1,
            "published_at": "2026年01月01日00时00分00秒",
            "media_url": "https://example.com/video.mp4",
        }
        collector.transcribe_from_meta = lambda cfg, meta: "这是逐字稿。"
        result = collector.desktop_scrape_single_url(db, table["id"], "https://www.douyin.com/video/1", {"asr": {}})
        self.assertEqual(result["status"], "成功")
        self.assertEqual(result["caption"], "这是逐字稿。")
        self.assertEqual(collector.desktop_list_items(db, table["id"])[0]["title"], "视频标题")
```

- [ ] **Step 2: Run tests and confirm failure**

Expected: FAIL because `desktop_scrape_single_url` does not exist.

- [ ] **Step 3: Implement scrape helper**

Implement `desktop_scrape_single_url(db_path, table_id, url, cfg, platform_hint="")` that normalizes URL, extracts metadata, transcribes video when caption is blank and media is available, maps fields into `desktop_save_item`, and stores status/error using existing `classify_processing_error`.

- [ ] **Step 4: Run tests and confirm pass**

Expected: PASS.

## Task 3: Desktop App HTTP API and UI

**Files:**
- Modify: `content_link_collector.py`

- [ ] **Step 1: Add API endpoints**

Add a `DesktopAppHandler` with:

```text
GET  /                         -> HTML UI
GET  /api/health                -> {ok:true}
GET  /api/tables                -> list local tables
POST /api/tables                -> create table
GET  /api/items?table_id=...    -> list results
POST /api/scrape                -> scrape one or more single links synchronously for MVP
GET  /api/export.csv?table_id=... -> CSV download
```

- [ ] **Step 2: Add embedded UI**

Embed HTML/CSS/JS matching the approved orange assistant direction: cute orange mascot with blink and hover juice animation, platform cards with real-looking platform badges, table creation sidebar, mode switch, textarea input, scrape button, result table/card/detail switching, help copy, and export CSV.

- [ ] **Step 3: Add CLI command**

Add parser command:

```python
s = sub.add_parser("desktop-app", help="启动橙子内容采集助手本地软件界面")
s.add_argument("--host", default="127.0.0.1")
s.add_argument("--port", type=int, default=51216)
s.add_argument("--open", action="store_true", help="启动后自动打开浏览器")
s.set_defaults(fn=cmd_desktop_app)
```

- [ ] **Step 4: Verify server endpoint**

Run:

```bash
python3 content_link_collector.py desktop-app --host 127.0.0.1 --port 51216
```

Then open `http://127.0.0.1:51216/api/health`. Expected: `{"ok": true}`.

## Task 4: Launcher Script

**Files:**
- Create: `启动橙子内容采集助手.command`

- [ ] **Step 1: Create double-click command**

Script content:

```bash
#!/bin/zsh
cd "$(dirname "$0")"
python3 content_link_collector.py desktop-app --host 127.0.0.1 --port 51216 --open
```

- [ ] **Step 2: Make executable**

Run:

```bash
chmod +x 启动橙子内容采集助手.command
```

## Task 5: Final Verification

**Files:**
- Modify: `content_link_collector.py`
- Modify: `test_webhook_helpers.py`
- Create: `启动橙子内容采集助手.command`

- [ ] **Step 1: Run syntax check**

```bash
PYTHONPYCACHEPREFIX=/tmp/chen_collector_pycache python3 -m py_compile content_link_collector.py
```

Expected: no output.

- [ ] **Step 2: Run unit tests**

```bash
PYTHONPYCACHEPREFIX=/tmp/chen_collector_pycache python3 -m unittest test_webhook_helpers.py
```

Expected: all tests pass.

- [ ] **Step 3: Start app and smoke test APIs**

```bash
python3 content_link_collector.py desktop-app --host 127.0.0.1 --port 51216
curl http://127.0.0.1:51216/api/health
curl http://127.0.0.1:51216/api/tables
```

Expected: health returns `ok:true`, tables returns at least the default collection table.

## Self-Review

Spec coverage: This plan covers the local app shell, platform selection, table creation, view switching, single-link scraping, local persistence, CSV export, and double-click launch. Homepage batch collection and Word/Excel export are intentionally left for the next slice after the MVP works.

Placeholder scan: No task uses TBD/TODO language. Each task includes target files, tests, commands, and concrete endpoint/function names.

Type consistency: `table_id`, `platform`, `source_url`, `source_type`, `title`, `caption`, `cover_url`, `duration`, `likes`, `comments`, `shares`, `published_at`, `status`, `error`, and `raw_metadata_json` match the design document data model.
