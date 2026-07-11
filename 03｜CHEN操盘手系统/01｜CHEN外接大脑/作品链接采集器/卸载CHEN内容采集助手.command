#!/bin/zsh
set -e

echo "将卸载 CHEN 内容采集助手应用本体。"
echo "注意：默认不会删除你的采集数据库、视频、配置和日志。"
read "confirm?输入 UNINSTALL 确认卸载应用本体："
if [[ "$confirm" != "UNINSTALL" ]]; then
  echo "已取消。"
  exit 0
fi

launchctl bootout "gui/$(id -u)" "$HOME/Library/LaunchAgents/com.chen.content-link-collector.desktop-app.plist" 2>/dev/null || true
rm -rf "/Applications/CHEN 内容采集助手.app"

echo "已卸载应用本体。数据仍保留在：$HOME/Library/Application Support/ChenContentLinkCollector"
