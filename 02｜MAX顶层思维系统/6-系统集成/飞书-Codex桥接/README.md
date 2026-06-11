# 飞书-Codex桥接

这是一个最小可运行的飞书 OpenAPI 网关，让 Codex 可以通过命令行读写飞书。

## 1. 准备飞书应用

在飞书开放平台创建一个「企业自建应用」，拿到：

- App ID
- App Secret

然后根据你要用的能力给应用开权限并发布/启用，例如：

- 发送消息：`im:message`
- 读取云文档：云文档/Docx 读取相关权限
- 创建云文档：云文档/Docx 创建/编辑相关权限

具体权限名称以飞书开放平台后台为准。

## 2. 创建本地配置

```bash
cd "6-系统集成/飞书-Codex桥接"
cp .env.example .env
```

然后填写 `.env`：

```env
FEISHU_APP_ID=cli_xxx
FEISHU_APP_SECRET=xxx
FEISHU_RECEIVE_ID_TYPE=open_id
FEISHU_RECEIVE_ID=ou_xxx
```

`.env` 已经被 `.gitignore` 忽略，不要上传给别人。

## 3. 测试连通

```bash
python3 feishu_codex.py auth-test
```

看到 `OK` 就说明 Codex 已经能拿到飞书 tenant_access_token。

## 4. 常用命令

### 发送一段文本到飞书

```bash
python3 feishu_codex.py send-text --text "Codex 已接入飞书。"
```

### 把 Markdown 文件发送到飞书

```bash
python3 feishu_codex.py push-md-as-message --file ../../数字版AI\ MAX目录说明.md
```

### 读取飞书 Docx 纯文本到本地 Markdown

```bash
python3 feishu_codex.py pull-docx-to-vault \
  --document-id YOUR_DOCUMENT_ID \
  --title "飞书文档导入测试" \
  --out-dir ../../2-日常MAX语料
```

### 创建一个飞书云文档

```bash
python3 feishu_codex.py docx-create --title "Codex 输出测试"
```

### 调用任意飞书 OpenAPI

```bash
python3 feishu_codex.py api GET /open-apis/docx/v1/documents/YOUR_DOCUMENT_ID/raw_content
```

POST 示例：

```bash
python3 feishu_codex.py api POST /open-apis/im/v1/messages \
  --query receive_id_type=open_id \
  --body-json '{"receive_id":"ou_xxx","msg_type":"text","content":"{\\"text\\":\\"hello\\"}"}'
```

## 5. Codex 使用方式

之后你可以直接对 Codex 说：

- “读取这个飞书文档到 Obsidian：document_id=xxx”
- “把这篇内容发给飞书的默认接收人”
- “调用飞书 API 创建一个标题为 xxx 的文档”

Codex 会使用本目录的 `feishu_codex.py` 执行。

## 6. 当前桥接能力

- tenant_access_token 获取与缓存
- 发送飞书文本消息
- Markdown 文件分段发送到飞书
- 读取飞书 Docx 纯文本并保存到 Obsidian
- 创建飞书 Docx 文档
- 任意 OpenAPI 原始调用

这是最小桥。后续可以继续升级为：

- 飞书事件订阅 Webhook
- Codex MCP Server
- 飞书多维表格同步
- 飞书文档块级写入与格式保留

## 7. 无代码双击脚本

如果你不想使用命令行，直接按这个顺序双击：

1. `双击测试飞书连接.command`：测试 App ID / App Secret 是否能连接飞书。
2. `配置默认接收人.command`：填写默认接收人，建议新手先选 `email`。
3. `发送测试消息.command`：给默认接收人发送一条测试消息。
4. `导入飞书文档到Obsidian.command`：输入飞书文档 document_id，导入到 `2-日常MAX语料/`。
5. `发送Obsidian文件到飞书.command`：把 Markdown 文件拖进窗口，发送到飞书。
6. `通过邮箱查询飞书用户ID.command`：输入飞书绑定邮箱，查询 open_id / user_id。
7. `通过手机号查询飞书用户ID.command`：输入飞书绑定手机号，查询 open_id / user_id。
8. `打开飞书通讯录权限页面.command`：打开飞书权限页面，申请 `contact:user.id:readonly`。
9. `打开飞书消息权限页面.command`：打开飞书权限页面，申请消息发送权限。
10. `打开飞书机器人能力页面.command`：打开飞书应用后台，启用机器人能力。

如果发送消息失败，优先检查：

- 飞书应用是否已经启用机器人能力。
- 飞书应用是否开通消息发送权限。
- 飞书应用是否已经发布/安装到企业。
- 接收人 ID 类型是否填对。

