# 作品链接采集器

用途：在飞书多维表格第一列填入抖音 / 小红书 / 视频号作品链接后，自动抓取并写回：

- 作品标题
- 文案
- 封面 / 封面图链接
- 时长
- 点赞、评论、分享
- 发布时间
- 抓取状态和错误原因

## 1. 飞书表格字段

你的截图已有这些核心字段：

| 字段名 | 建议类型 |
|---|---|
| 作品链接 | 文本 |
| 作品标题 | 文本 |
| 文案 | 文本 |
| 封面 | 文本或附件 |
| 时长 | 文本 |
| 点赞 | 数字 |
| 评论 | 数字 |
| 分享 | 数字 |
| 发布时间 | 文本 |

工具还会补充这些字段，方便排查：

| 字段名 | 建议类型 |
|---|---|
| 平台 | 文本 |
| 封面图链接 | 文本 |
| 抓取状态 | 文本 |
| 抓取时间 | 文本 |
| 错误信息 | 文本 |

## 1.1 存储边界

飞书多维表格是本工具的唯一业务记录界面。工具只把标题、文案、封面链接、互动数据、发布时间、抓取状态和错误原因写回飞书。

视频、音频、字幕和截图不做长期本地保存。需要 ASR 时，程序只会把媒体临时下载到系统临时目录，抽取音频并完成转写后立即删除临时目录。失败时也会尽量清理临时目录，并把原因写入「抓取状态」和「错误信息」。

当前状态约定：

| 状态 | 含义 |
|---|---|
| 成功 | 已抓到可用信息，必要时已完成转写 |
| 部分成功 | 已抓到部分信息，但缺标题或缺文案 |
| 需Cookie | 平台要求登录态或 Cookie 过期 |
| 需ASR | 已知链接需要转写，但没有拿到可下载媒体直链 |
| ASR失败 | 下载或抽音频后，转写阶段失败 |
| 下载失败 | 媒体下载或 ffmpeg 抽音频失败 |
| VPN/网络异常 | YouTube 等海外平台访问失败，通常需要检查 VPN 或网络出口 |
| YouTube下载受限 | YouTube 已抓到基础信息，但音频分片下载被 403/风控拦截，无法继续 ASR |
| 字幕缺失 | YouTube 没有可用字幕，且当前没有可用 ASR 兜底 |
| yt-dlp缺失 | 本机没有找到 yt-dlp，无法稳定抓取 YouTube / Instagram |
| 待人工处理 | 其它无法自动判断的失败 |
| 待Downie人工下载 | 可人工用 Downie 兜底下载后再处理 |

## 2. 配置

复制配置样例：

```bash
cd "03｜CHEN操盘手系统/01｜CHEN外接大脑/作品链接采集器"
cp config.example.json config.json
```

填入：

- `feishu.app_id`
- `feishu.app_secret`
- `feishu.app_token`
- `feishu.table_id`
- `feishu.table_ids`（可选；复制表格后，把新表 URL 里的 `table=tbl...` 加到这里）
- `feishu.auto_discover_tables`（可选；为 `true` 时自动扫描同一个多维表格应用下的所有数据表）

`app_token` 和 `table_id` 从飞书多维表格 URL 里取：

```text
https://xxx.feishu.cn/base/{app_token}?table={table_id}&view=...
```

如果是在同一个知识库里复制出来的新表，`app_token` 通常不变，但 `table_id` 会变。开启 `auto_discover_tables` 后，监听服务会自动发现同一个 `app_token` 下的其他数据表；字段结构一致的表可以直接复用补全功能。

飞书自建应用需要开通 `bitable:app` 权限，并把应用添加为该多维表格的可编辑协作者。

### 2.1 YouTube / 海外平台安全模式

YouTube 抓取依赖 VPN、`yt-dlp`、字幕或音频下载。普通公开视频如果有字幕，工具会优先读取字幕；如果没有字幕，会临时下载音频并走 ASR，完成后删除临时文件。

YouTube 比国内平台更容易受 VPN 出口、Cookie 和风控影响。工具默认启用轻量安全模式：

```json
{
  "yt_dlp": {
    "enabled": true,
    "cookies_file": "cookies.txt",
    "cookies_from_browser": "",
    "proxy": "",
    "extractor_args": [],
    "js_runtimes": "",
    "youtube_retry_extractor_args": [
      "youtube:player_client=mweb",
      "youtube:player_client=web_safari",
      "youtube:player_client=ios",
      "youtube:player_client=android",
      "youtube:player_client=tv"
    ],
    "youtube_po_token": "",
    "youtube_po_token_provider": false,
    "download_format": "ba[ext=m4a]/ba/best[ext=mp4][height<=360]/18/best[height<=360]/best"
  },
  "youtube_safety": {
    "enabled": true,
    "preflight": true,
    "connectivity_check": false,
    "connectivity_url": "https://www.youtube.com/generate_204",
    "throttle_seconds": 3.0,
    "max_consecutive_network_failures": 2,
    "open_browser_before_scrape": true,
    "browser_gate_timeout": 12
  }
}
```

- `preflight`：采集前确认本机有可用 `yt-dlp`。
- `open_browser_before_scrape`：YouTube 单条/深采前先打开专用浏览器到目标视频，优先发现登录验证，并为页面文字稿兜底准备登录态。
- `browser_gate_timeout`：专用浏览器页面验证等待秒数；VPN 慢时可适当调高。
- `yt_dlp.proxy`：如 VPN 不是全局模式，可填本机代理，例如 `http://127.0.0.1:7897`。
- `yt_dlp.download_format`：YouTube 没字幕需要 ASR 时，默认优先下载音频或低码率 MP4，降低大分片下载失败概率。
- `yt_dlp.extractor_args`：全局追加给 yt-dlp 的 extractor 参数；没有明确需要时保持空数组。
- `yt_dlp.js_runtimes`：YouTube 新版 JS challenge 需要 JavaScript runtime；本机会自动优先使用 `~/.local/bin/node`，也可手动填 `node:/path/to/node`。
- `yt_dlp.youtube_retry_extractor_args`：YouTube 音频下载失败时自动尝试的 player client 策略。默认会在普通下载失败后继续试 `mweb / web_safari / ios / android / tv`。
- `yt_dlp.youtube_po_token`：YouTube GVS 分片下载被 403 拦截时可填 PO Token，例如 `mweb.gvs+TOKEN`。这是敏感配置，不要贴到日志或聊天里。
- `yt_dlp.youtube_po_token_provider`：如果已安装 yt-dlp PO Token Provider 插件，设为 `true` 后会优先使用 `mweb` 下载链路，让插件自动提供 PO Token。
- `connectivity_check`：如需更严格，可打开；每次 YouTube 采集前检查 VPN 是否能访问 YouTube。
- `throttle_seconds`：YouTube 频道候选深采时，每条之间默认等待 3 秒，避免过快触发限制。
- `max_consecutive_network_failures`：连续 2 条出现 VPN/网络异常时暂停后续深采。

遇到 `YouTube下载受限`，说明标题、封面、时长等基础信息通常已经抓到，但该视频没有可读字幕，且音频下载被 YouTube 或当前 VPN 出口拦截。系统会先自动重试多种 YouTube player client；仍失败时，优先处理 Cookie / VPN 节点 / PO Token，不建议默认启用浏览器实时录音。

桌面助手里提供 `诊断YouTube` 按钮。它默认做快速诊断，不下载音频，只检查：

- YouTube 链接和 yt-dlp 预检是否通过。
- yt-dlp 是否能拿到标题、时长等元数据。
- 是否有官方字幕/自动字幕。
- Cookie 文件、浏览器 Cookie、代理、PO Token、重试 client 是否已配置。
- 专用登录浏览器和 `yt_dlp.cookies_from_browser` 是否一致。

如快速诊断显示 `需下载音频`，表示该视频没有官方字幕；这时才需要进一步做下载探测或正式采集。下载探测会真实尝试音频下载，长视频可能较慢。
如果诊断提示专用浏览器和 Cookie 来源不一致，例如登录窗口是 Chrome 但 yt-dlp 读取 Edge Cookie，优先把两者统一到同一个浏览器，否则“已登录窗口”和“下载身份”会互相脱节。
桌面助手里的 `下载探测` 按钮会真实尝试 yt-dlp 音频下载和多 client / 多 Cookie 来源兜底，用来确认是否能进入 ASR。它可能比快速诊断慢，只建议在重要视频或需要排查下载限制时使用。
桌面助手里的 `启用PO模式` 会写入 `yt_dlp.youtube_po_token_provider=true`，后续下载探测会优先尝试 `mweb`，以便已安装的 PO Token Provider 插件自动提供 token。

## 3. 运行

测试飞书连接：

```bash
python3 content_link_collector.py auth-test
```

补齐字段：

```bash
python3 content_link_collector.py init-fields
```

测试单个链接，不写入飞书：

```bash
python3 content_link_collector.py test-url "https://www.douyin.com/video/7166664670857858340"
```

扫描表格并写回：

```bash
python3 content_link_collector.py sync
```

只处理前 3 条：

```bash
python3 content_link_collector.py sync --limit 3
```

重跑所有有链接的记录：

```bash
python3 content_link_collector.py sync --all
```

## 4. 长连接自动化模式（主方案）

长连接模式是当前推荐方案：本机程序主动连接飞书开放平台，飞书不需要访问你的公网 URL，也不会再受 localtunnel / Cloudflare 临时地址变化影响。

先安装飞书官方 SDK：

```bash
python3 -m pip install --user -U lark-oapi
```

启动长连接监听：

```bash
python3 content_link_collector.py event-listener
```

也可以双击：

```text
启动飞书长连接监听.command
```

飞书开放平台里保持：

```text
使用 长连接 接收事件
```

已添加事件建议保留：

```text
多维表格记录新增
多维表格记录变更
```

本地监听启动后，在飞书开放平台点击「重新验证」。验证成功后，你在多维表格新增或修改作品链接，长连接客户端会收到 `record_id`，然后复用同一套后台逻辑：

```text
record_id -> 读取飞书记录 -> 抓取作品信息 -> 本地 Whisper 转写音频 -> 写回飞书
```

长连接监听还带一个轻量保险补扫：默认每 15 秒只检查“有作品链接，但作品标题、文案、抓取状态都为空”的新行。这样即使飞书偶尔没有把事件推送到客户端，新链接也会被补进同一后台队列，不会回到全表重扫。

补扫间隔可以在 `config.json` 中调整：

```json
{
  "event": {
    "scan_interval": 15
  }
}
```

如果需要把监听做成 Mac 常驻服务，使用本目录里的：

```text
com.chen.content-link-collector.event-listener.plist
```

常驻服务的工作目录是：

```text
/Users/chen.zip/Library/Application Support/ChenContentLinkCollector
```

## 5. Webhook 自动化模式（备用）

轮询模式会每隔一段时间扫表。Webhook 模式更适合长期自动化：你在飞书新增或修改作品链接后，飞书事件会立刻通知本机 Worker，Worker 只处理这一条记录并写回结果。

本机启动 Webhook 服务：

```bash
python3 content_link_collector.py webhook-server --host 127.0.0.1 --port 8787
```

也可以双击：

```text
启动飞书Webhook服务.command
```

Cloudflare Tunnel 暴露公网地址：

```bash
cloudflared tunnel --url http://127.0.0.1:8787
```

也可以双击：

```text
启动Cloudflare隧道.command
```

Cloudflare 会输出一个 `https://...trycloudflare.com` 地址。在飞书开放平台的事件订阅里填写：

```text
https://...trycloudflare.com/feishu/webhook
```

如果当前网络无法建立 Cloudflare Tunnel，可以用 localtunnel：

```bash
npx --yes localtunnel --port 8787
```

也可以双击：

```text
启动LocalTunnel隧道.command
```

localtunnel 会输出一个 `https://...loca.lt` 地址。在飞书开放平台的事件订阅里填写：

```text
https://...loca.lt/feishu/webhook
```

飞书 URL verification 会收到：

```json
{"challenge": "xxx"}
```

服务会返回：

```json
{"challenge": "xxx"}
```

收到真实记录事件后，服务会从事件里提取 `record_id`，后台队列处理对应一行。Webhook 请求会先快速返回，视频下载和本地 Whisper 转写在后台慢慢完成。

## 6. 服务器部署版

服务器版适合长期使用：飞书直接请求服务器，不依赖本机网络、VPN、睡眠状态或 Cloudflare 临时隧道。

### 服务器要求

- Linux 服务器
- Docker 和 Docker Compose
- 开放入站端口 `8787`
- 建议至少 `2C4G`；本地 Whisper `small` 模型会占用 CPU 和内存，视频越长越慢

### 部署文件

服务器部署相关文件：

```text
Dockerfile
docker-compose.yml
requirements-server.txt
config.server.example.json
chen-content-link-collector.service.example
```

### 部署步骤

在服务器上创建目录：

```bash
sudo mkdir -p /opt/chen-content-link-collector
sudo chown "$USER":"$USER" /opt/chen-content-link-collector
```

上传本目录里的部署文件和 `content_link_collector.py` 到：

```text
/opt/chen-content-link-collector
```

复制配置：

```bash
cd /opt/chen-content-link-collector
cp config.server.example.json config.json
```

编辑 `config.json`，填入：

- `feishu.app_id`
- `feishu.app_secret`
- `feishu.app_token`
- `feishu.table_id`
- `feishu.table_ids`（可选，多张同结构表时填写）
- `feishu.auto_discover_tables`（可选，自动扫描同一个多维表格应用下的所有数据表）

如果需要处理受限抖音链接，把浏览器导出的 Netscape 格式 Cookie 放到：

```text
/opt/chen-content-link-collector/cookies.txt
```

启动服务：

```bash
docker compose up -d --build
```

看日志：

```bash
docker compose logs -f content-link-collector
```

测试健康检查：

```bash
curl http://服务器IP:8787/health
```

飞书事件订阅 URL 填：

```text
http://服务器IP:8787/feishu/webhook
```

如果服务器有域名和 HTTPS 反向代理，建议填：

```text
https://你的域名/feishu/webhook
```

### 开机自启

复制 systemd 示例：

```bash
sudo cp chen-content-link-collector.service.example /etc/systemd/system/chen-content-link-collector.service
sudo systemctl daemon-reload
sudo systemctl enable --now chen-content-link-collector
```

查看状态：

```bash
sudo systemctl status chen-content-link-collector
```

## 7. 平台限制

抖音公开网页通常最容易解析。小红书和视频号经常需要登录态，公开页面可能不暴露点赞、评论、分享、发布时间。

如果某个平台显示“部分成功”或“失败”，把浏览器里的登录 Cookie 填到 `config.json` 对应平台的 `cookie` 里再重试。Cookie 属于敏感信息，不要发给别人，也不要提交到 Git。

服务器不能直接读取你 Mac 浏览器里的 Edge/Chrome 登录态；服务器要处理受限链接，需要上传 `cookies.txt` 或接入稳定的数据接口。

## 8. 封面字段说明

如果「封面」是文本字段，工具会写入封面图 URL。

如果「封面」是附件字段，工具会尝试把图片上传到飞书后写入附件；如果飞书接口或权限不接受，会退回到「封面图链接」字段，至少保证图片地址可用。
