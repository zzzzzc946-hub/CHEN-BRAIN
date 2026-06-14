#!/bin/zsh
cd "$(dirname "$0")"
echo "启动飞书长连接监听。"
echo "飞书开放平台保持：使用 长连接 接收事件。"
python3 content_link_collector.py event-listener
