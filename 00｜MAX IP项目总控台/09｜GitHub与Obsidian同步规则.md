# 09｜GitHub与Obsidian同步规则

## 一、文档定位

本文档用于定义 `CHEN BRAIN` 仓库在 Obsidian 与 GitHub 之间的同步规则。

本仓库是 Obsidian Markdown 知识库，GitHub 用于版本管理、备份、协同和变更追踪。

------------------------------------------------------------------------

## 二、同步原则

GitHub 同步遵循以下原则：

    同步知识资产
    同步协作规则
    同步必要配置
    不同步本地临时状态
    不同步密钥和隐私配置

------------------------------------------------------------------------

## 三、建议进入 GitHub 的内容

建议进入 GitHub 的内容包括：

    Markdown 文档
    Inbox 中需要保留的源文件
    系统说明文档
    协同规则文档
    Obsidian 核心配置
    非敏感插件配置

其中，Inbox 源文件可以作为原始资料归档保留，便于后续追溯转换来源。

------------------------------------------------------------------------

## 四、不建议进入 GitHub 的内容

不建议进入 GitHub 的内容包括：

    .DS_Store
    .obsidian/workspace.json
    .obsidian/workspace-mobile.json
    Obsidian 缓存
    搜索索引
    临时文件
    日志文件
    .env 文件
    API Key
    私钥
    本地证书

特别注意：

    .obsidian/plugins/obsidian-local-rest-api/data.json

该文件可能包含本地 API Key、证书和私钥，不应提交到 GitHub。

------------------------------------------------------------------------

## 五、Obsidian 插件配置规则

不要忽略整个 `.obsidian` 文件夹。

建议保留：

    .obsidian/app.json
    .obsidian/appearance.json
    .obsidian/community-plugins.json
    .obsidian/core-plugins.json
    .obsidian/graph.json
    .obsidian/plugins/*/manifest.json
    .obsidian/plugins/*/styles.css
    非敏感的 .obsidian/plugins/*/data.json

建议忽略：

    workspace 状态文件
    插件缓存
    搜索索引
    本地密钥配置

------------------------------------------------------------------------

## 六、提交前检查规则

每次提交前，应至少检查：

    git status
    是否有 .DS_Store
    是否有 workspace.json
    是否有 API Key、私钥或证书
    是否误删 Inbox 源文件
    是否误改五个一级目录名称

如果发现敏感配置进入 Git，应先从 Git 索引移除，但保留本地文件。

------------------------------------------------------------------------

## 七、推荐提交信息格式

知识库规则初始化：

    init: add CHEN BRAIN collaboration rules

日常知识库更新：

    update: refine MAX IP knowledge base

Inbox 文档归档：

    archive: add source docs to Inbox

AI 协同规则调整：

    docs: update AI collaboration rules

------------------------------------------------------------------------

## 八、Obsidian Git 使用提醒

Obsidian Git 可以用于自动备份和手动提交，但提交前仍应关注变更列表。

不建议让本地 workspace 状态、系统缓存和敏感插件配置自动进入提交。

如果自动备份产生异常变更，应优先检查 `.gitignore` 和 Git 索引状态。
