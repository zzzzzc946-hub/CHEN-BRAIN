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

## 2. 配置

复制配置样例：

```bash
cd "03｜CHEN操盘手系统/01｜客户与情报/作品链接采集器"
cp config.example.json config.json
```

填入：

- `feishu.app_id`
- `feishu.app_secret`
- `feishu.app_token`
- `feishu.table_id`

`app_token` 和 `table_id` 从飞书多维表格 URL 里取：

```text
https://xxx.feishu.cn/base/{app_token}?table={table_id}&view=...
```

飞书自建应用需要开通 `bitable:app` 权限，并把应用添加为该多维表格的可编辑协作者。

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

## 4. 平台限制

抖音公开网页通常最容易解析。小红书和视频号经常需要登录态，公开页面可能不暴露点赞、评论、分享、发布时间。

如果某个平台显示“部分成功”或“失败”，把浏览器里的登录 Cookie 填到 `config.json` 对应平台的 `cookie` 里再重试。Cookie 属于敏感信息，不要发给别人，也不要提交到 Git。

## 5. 封面字段说明

如果「封面」是文本字段，工具会写入封面图 URL。

如果「封面」是附件字段，工具会尝试把图片上传到飞书后写入附件；如果飞书接口或权限不接受，会退回到「封面图链接」字段，至少保证图片地址可用。
