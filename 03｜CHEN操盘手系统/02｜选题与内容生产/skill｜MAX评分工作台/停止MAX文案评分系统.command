#!/bin/zsh
cd "$(dirname "$0")"

if [ ! -f max_score_server.pid ]; then
  echo "没有找到 max_score_server.pid。服务可能没有通过启动脚本运行。"
  printf "按任意键关闭窗口..."
  read -k 1
  exit 0
fi

pid="$(cat max_score_server.pid)"
if kill -0 "$pid" >/dev/null 2>&1; then
  kill "$pid"
  rm -f max_score_server.pid
  echo "MAX文案评分系统已停止。"
else
  rm -f max_score_server.pid
  echo "记录的进程已不存在，已清理 pid 文件。"
fi

printf "按任意键关闭窗口..."
read -k 1
