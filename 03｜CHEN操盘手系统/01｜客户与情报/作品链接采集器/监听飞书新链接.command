#!/bin/zsh
cd "$(dirname "$0")"
echo "开始监听飞书多维表格。"
echo "你往第一列放入新作品链接后，本窗口会自动抓取元数据，并逐条转写文案。"
echo "窗口不要关闭；要停止时按 Control+C。"
echo
python3 content_link_collector.py watch --interval 60 --sync-limit 20 --transcribe-limit 1
echo
echo "监听已停止。按任意键关闭窗口。"
read -k 1
