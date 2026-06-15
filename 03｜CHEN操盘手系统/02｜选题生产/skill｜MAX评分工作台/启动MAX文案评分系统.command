#!/bin/zsh
cd "$(dirname "$0")"
mkdir -p logs

if [ -f max_score_server.pid ]; then
  old_pid="$(cat max_score_server.pid)"
  if kill -0 "$old_pid" >/dev/null 2>&1; then
    open "http://127.0.0.1:8765/"
    echo "MAX文案评分系统已在运行：http://127.0.0.1:8765/"
    echo "PID: $old_pid"
    printf "按任意键关闭窗口..."
    read -k 1
    exit 0
  fi
fi

python3 max_score.py serve --port 8765 > logs/max_score_server.log 2>&1 &
server_pid=$!
echo "$server_pid" > max_score_server.pid
sleep 1
open "http://127.0.0.1:8765/"

echo "MAX文案评分系统已启动：http://127.0.0.1:8765/"
echo "记录库：scores_db.json"
echo "日志：logs/max_score_server.log"
echo "停止服务：双击 停止MAX文案评分系统.command"
echo "保持这个窗口打开，评分系统会持续运行。关闭窗口或双击停止脚本即可停止服务。"

wait "$server_pid"
rm -f max_score_server.pid
