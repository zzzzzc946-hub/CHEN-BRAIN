# AI 协同配置清单

更新时间：2026-06-11

这份清单记录 MAX BRAIN 当前适合 Codex 深度协作的配置状态，以及下一步优化方向。

---

## 1. 当前可用能力

### 本机与基础环境

- macOS 15.2
- Apple Silicon / M3
- 16GB 内存
- 当前库规模约为轻量级文本知识库，性能足够。

### 已可用工具

- Codex 桌面端
- Obsidian
- Claudian Obsidian 插件
- 飞书
- Google Chrome
- WPS Office
- Eagle
- Homebrew
- ripgrep
- pandoc
- sqlite3

### Codex 插件能力

- 文档处理
- 表格处理
- PPT 处理
- 浏览器控制
- 电脑控制
- Node REPL

---

## 2. 已完成优化

- 新增根目录 `.gitignore`，避免把密钥、缓存、会话、系统文件纳入版本管理。
- 新增 `AGENTS.md`，作为 Codex 进入本库后的项目级协作规则。
- 新增 `0-Codex协作入口.md`，固定不同任务的资料调用路径。
- 梳理飞书桥接位置：`6-系统集成/飞书-Codex桥接/`。

---

## 3. 建议安装的工具链

这些工具用于提升批量处理、内容转写、图片 OCR、GitHub 协作和脚本工程化能力。

```bash
brew install fd fzf gh ffmpeg imagemagick tesseract uv pipx yq
```

用途：

- `fd`：更快找文件。
- `fzf`：交互式选择文件和命令历史。
- `gh`：GitHub 仓库、issue、PR 管理。
- `ffmpeg`：音视频抽取、压缩、转码。
- `imagemagick`：图片批处理。
- `tesseract`：OCR 识别图片文字。
- `uv`：Python 项目与依赖管理。
- `pipx`：安全安装 Python 命令行工具。
- `yq`：处理 YAML 配置。

---

## 4. 飞书桥接状态

当前已有：

- `.env.example`
- 本地 `.env`，已被忽略，不进入版本管理
- token 缓存文件，已被忽略，不进入版本管理
- `.gitignore`
- `feishu_codex.py`
- `README.md`

待完成：

1. 确认飞书开放平台应用权限是否完整。
2. 运行连通测试。
3. 验证消息发送、文档读取、文档创建三个核心动作。
4. 根据实际使用频率决定是否升级为 MCP Server 或事件订阅 Webhook。

安全规则：

- `.env` 不进入 Git。
- token 缓存不进入 Git。
- Codex 不主动输出 App Secret。

---

## 5. 推荐工作流

### 内容生产

选题输入 → Codex 调用协作入口 → 生成初稿 → MAX 语感校准 → 内容评分 → 修改 → 入库。

### 价值观沉淀

日常收集 → 每周梳理报告 → 用户审核 → Codex 正式归档 → 更新汇总。

### 飞书协作

飞书收集素材 → Codex 拉到 Obsidian → 结构化整理 → 生成内容/报告 → 推回飞书。

### 评分工具

内容进入评分体系 → 输出分数和偏差 → 生成修改建议 → 进入成品库。

---

## 6. 下一阶段优化

优先级从高到低：

1. 完成 Git 初始提交，建立版本回溯能力。
2. 接通飞书 `.env` 与权限，验证消息发送和文档读取。
3. 给 `maxscore-codex` 补一个固定测试样本和使用说明。
4. 把常用任务沉淀成可复用命令：
   - 内容评分
   - 语感校准
   - 价值观梳理
   - 飞书导入
   - 飞书发送
5. 建立每周例行任务：
   - 价值观梳理
   - 内容成品复盘
   - 语感校准库更新
