#!/bin/zsh
cd "$(dirname "$0")"
echo "启动 localtunnel，复制输出里的 https://...loca.lt"
echo "飞书事件订阅 URL 应填写：https://你的隧道地址/feishu/webhook"
npx --yes localtunnel --port 8787
