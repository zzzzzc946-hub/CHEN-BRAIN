#!/bin/zsh
cd "$(dirname "$0")"
echo "启动 Cloudflare 临时隧道，复制输出里的 https://...trycloudflare.com"
echo "飞书事件订阅 URL 应填写：https://你的隧道地址/feishu/webhook"
if [[ -x "./cloudflared" ]]; then
  ./cloudflared tunnel --protocol http2 --url http://127.0.0.1:8787
elif command -v cloudflared >/dev/null 2>&1; then
  cloudflared tunnel --protocol http2 --url http://127.0.0.1:8787
else
  echo "未找到 cloudflared。请先安装 Cloudflare Tunnel 工具。"
  echo "下载地址：https://github.com/cloudflare/cloudflared/releases/latest"
  read "?按回车退出"
fi
