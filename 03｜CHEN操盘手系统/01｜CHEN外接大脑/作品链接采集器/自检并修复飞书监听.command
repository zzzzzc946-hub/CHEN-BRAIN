#!/bin/zsh
set -u

APP_DIR="$HOME/Library/Application Support/ChenContentLinkCollector"
RUNTIME="$APP_DIR/content_link_collector.py"

echo "== CHEN 作品链接采集器：自检并修复 =="
echo

if [[ ! -f "$RUNTIME" ]]; then
  echo "未找到常驻脚本：$RUNTIME"
  echo "请先重新运行部署步骤。"
  echo
  read -k 1 "?按任意键退出..."
  exit 1
fi

python3 "$RUNTIME" health-check --repair

echo
echo "最新健康守护日志："
if [[ -f "$APP_DIR/logs/health.out.log" ]]; then
  tail -n 30 "$APP_DIR/logs/health.out.log"
else
  echo "暂无健康守护日志。"
fi

echo
echo "判断方式："
echo "- 表格若显示“成功”：系统已正常写入。"
echo "- 表格若显示“等待登录”：专用浏览器已可启动，但平台登录态需要你重新登录/播放目标内容。"
echo "- 表格若长期空白：本脚本会重启监听服务，等 1 分钟再看。"
echo
read -k 1 "?按任意键退出..."
