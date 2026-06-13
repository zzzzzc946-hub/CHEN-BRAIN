#!/bin/zsh
cd "$(dirname "$0")"
python3 content_link_collector.py sync
echo
echo "处理完成。按任意键关闭窗口。"
read -k 1
