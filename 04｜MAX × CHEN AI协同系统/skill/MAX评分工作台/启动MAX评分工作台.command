#!/bin/zsh
cd "$(dirname "$0")"
python3 max_score.py serve --port 8765 &
sleep 1
open "http://127.0.0.1:8765/"
echo "MAX评分工作台已启动：http://127.0.0.1:8765/"
echo "如果端口已被占用，请先关闭之前的 python3 服务。"
read -n 1 -s "?按任意键关闭窗口..."
