# CHEN BRAIN｜Codex入口

本仓库当前只保留两个核心系统：

1. `02｜MAX顶层思维系统`
2. `03｜CHEN操盘手系统`

`01｜Inbox｜md转换` 仅作为临时导入区。

## 任务判断

### 1. MAX思想 / 内容边界 / 用户调研 / 传播规则 / 语感校准

读取：

`02｜MAX顶层思维系统`

注意：

- `02｜MAX顶层思维系统` 是 MAX 大脑源。
- 默认不修改、不移动、不重构。

### 2. CHEN操盘 / 选题 / 内容生产 / 发布迭代 / 仓库规则

读取：

`03｜CHEN操盘手系统`

其中：

`03｜CHEN操盘手系统/00｜CHEN操盘手系统总纲`
负责系统总纲、协作规则、仓库规则、阶段进展。

`03｜CHEN操盘手系统/02｜选题与内容生产`
负责选题、内容生产、评分体系、发布迭代。

## 硬规则

- 不主动扩系统。
- 不创建新的一级目录。
- 不恢复 `00｜MAX IP项目总控台`。
- 不恢复 `04｜MAX × CHEN AI协同系统`。
- 不修改 `02｜MAX顶层思维系统` 的原始源文档。
- 不创建代码项目结构。
- 所有动作最终服务：
  更懂 MAX → 更懂 MAX 客户群体 → 判断是否有价值、是否有效 → 产出更准的选题和内容。

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

When the user types `/graphify`, use the installed graphify skill or instructions before doing anything else.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- Dirty graphify-out/ files are expected after hooks or incremental updates; dirty graph files are not a reason to skip graphify. Only skip graphify if the task is about stale or incorrect graph output, or the user explicitly says not to use it.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
