#!/bin/zsh
cd "$(dirname "$0")"
set -e
ARCH="$(uname -m)"
if [[ "$ARCH" == "arm64" ]]; then
  ASSET="cloudflared-darwin-arm64.tgz"
else
  ASSET="cloudflared-darwin-amd64.tgz"
fi
URL="https://github.com/cloudflare/cloudflared/releases/latest/download/$ASSET"
echo "下载 $URL"
curl -L -o "$ASSET" "$URL"
tar -xzf "$ASSET"
chmod +x cloudflared
echo "安装完成：$(pwd)/cloudflared"
./cloudflared --version
read "?按回车退出"
