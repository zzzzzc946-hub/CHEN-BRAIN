# 2026-07-09 回归防护栅栏

这个文件用于防止后续改 UI、网页分享、日报页、App 安装或桌面服务时，把已经完成的功能误删、误覆盖、误同步成旧版本。

## 不可回退能力

以下能力一旦已经上线，后续改动必须保留：

- 采集表格里的 `打开今日日报`、`加入今日日报`、`移出今日日报`、`日报日期`。
- 日报页右上角 `日报时间轴` 是日期选择浮层，不能改回跳转刷新。
- 日报页左侧只显示 `当天素材`，不把日期列表塞回左侧。
- 日报页工具栏必须可操作：`工作台`、`视频专注`、`文稿阅读`、`表格总览`、`字段配置`、`筛选`、`排序`、`行高`、`调整空间`。
- `字段配置`、`筛选`、`排序`、`行高` 必须真实控制下方表格或日报内容，不能只显示说明文字。
- 多维表格字段必须尽量对齐飞书字段：`作品链接`、`平台`、`作品标题`、`文案`、`封面图链接`、`时长`、`点赞`、`评论`、`分享`、`发布时间`、`抓取状态`、`抓取时间`、`错误信息`。
- 日报扩展字段必须保留：`MAX口喷卡片`、`日报日期`、`加入日报`、`日报排序`、`Max反馈`。
- 动态背景和操作反馈不能被删：`dailyDrift`、粒子 canvas、按钮 hover/active 过渡。
- 登录处理入口必须保留：`打开登录浏览器`、`/api/browser/login`。
- 视频下载入口必须保留：`下载视频`、`/api/video/save`。

## 自动化栅栏

`test_webhook_helpers.py` 里新增了两组集中回归测试：

- `test_regression_guardrail_keeps_daily_workbench_contract`
- `test_regression_guardrail_keeps_collector_table_contract`

这两组测试的目的不是检查某个实现细节优雅不优雅，而是把用户已经确认过的关键操作入口、字段、日报功能和视觉动效锁住。以后任何改动如果误删这些能力，测试会直接失败。

## 每次改动后的强制流程

在同步运行版前，必须先跑：

```bash
PYTHONPYCACHEPREFIX=/tmp/chen-guardrail-pycache python3 -m py_compile content_link_collector.py test_webhook_helpers.py
PYTHONPYCACHEPREFIX=/tmp/chen-guardrail-pycache python3 -m unittest test_webhook_helpers.py
```

只有通过后才能同步：

```bash
cp content_link_collector.py "/Users/chen.zip/Library/Application Support/ChenContentLinkCollector/content_link_collector.py"
launchctl kickstart -k gui/$(id -u)/com.chen.content-link-collector.desktop-app
```

同步后必须验证运行版：

```bash
cmp -s content_link_collector.py "/Users/chen.zip/Library/Application Support/ChenContentLinkCollector/content_link_collector.py"; printf 'cmp_exit=%s\n' $?
curl -sS http://127.0.0.1:51216/daily | rg "dailyParticleCanvas|dailyColumns|setFieldPreset|表格总览"
curl -sS http://127.0.0.1:51216/ | rg "tablePrefsVersion=4|飞书字段配置|setColumnPreset|打开今日日报|下载视频"
```

## 操作原则

- 不用“整段替换旧 HTML”来做小 UI 功能，除非先确认所有不可回退能力都被迁移。
- 不把源码改动视为上线，必须同步运行目录并重启桌面服务。
- 不清空数据库、不重建数据表、不删除已有日报数据。
- 如果新功能和旧功能冲突，先保旧功能，再单点增加新功能。
