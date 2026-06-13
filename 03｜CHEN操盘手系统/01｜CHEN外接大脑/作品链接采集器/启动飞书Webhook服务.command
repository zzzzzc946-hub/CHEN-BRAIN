#!/bin/zsh
cd "$(dirname "$0")"
echo "启动飞书 Webhook 服务：http://127.0.0.1:8787/feishu/webhook"
python3 content_link_collector.py webhook-server --host 127.0.0.1 --port 8787
