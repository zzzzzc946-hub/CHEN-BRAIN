# CHEN 内容采集助手 Git 工作树划分

建立时间：2026-07-09

## 原则

- `main` 保持为当前整合主线，不在主线里同时推进多个新功能。
- 每个正在实现的功能模块使用一个独立 Codex 窗口和一个独立 Git worktree。
- 仅当功能进入实现阶段才派生 worktree；只停留在规划、想法、讨论阶段的功能先不派生。
- 不修改 `02｜MAX顶层思维系统` 原始源文档。
- 运行产物、浏览器缓存、SQLite 数据库、日志、app bundle、tunnel 工具不进入 Git。

## 当前工作树

| 功能模块 | 分支 | 工作树路径 | 用途 |
| --- | --- | --- | --- |
| 采集器核心 | `codex/content-collector-core` | `.worktrees/content-collector-core` | 链接采集、表格数据、队列、导出、基础桌面服务 |
| Max 日报工作台 | `codex/max-daily-workbench` | `.worktrees/max-daily-workbench` | `/daily` 页面、日报时间轴、视频/口喷卡片展示 |
| 公网分享入口 | `codex/public-share-tunnel` | `.worktrees/public-share-tunnel` | localtunnel/Cloudflare/Tailscale 等公网入口、访问隔离、健康检查 |
| Mac 客户端 | `codex/native-mac-client` | `.worktrees/native-mac-client` | macOS app 壳、启动器、权限和本机体验 |
| 平台采集扩展 | `codex/platform-ingestion` | `.worktrees/platform-ingestion` | 抖音、小红书、B站、视频号、YouTube、Instagram 等平台适配 |

## 后续新功能流程

1. 新功能准备进入实现时，先确认它属于哪个已有模块。
2. 如果属于已有模块，进入对应 worktree 开发。
3. 如果是新的独立模块，先创建新 Codex 窗口和新 worktree，再写实现计划。
4. 如果只是规划或讨论，不创建 worktree。
5. 实现完成后，在对应 worktree 跑测试，再决定合并回 `main`。

## 常用命令

```bash
git worktree list
git -C ".worktrees/max-daily-workbench" status
git -C ".worktrees/public-share-tunnel" status
```

