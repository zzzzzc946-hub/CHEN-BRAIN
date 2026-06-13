#!/bin/zsh
cd "$(dirname "$0")"
echo "开始批量转写飞书表格里「文案」为空的作品。"
echo "本地 Whisper 会逐条下载视频、抽音频、转写并写回飞书。"
echo "过程可能很久，窗口不要关闭。"
echo
python3 content_link_collector.py transcribe-missing
echo
echo "批量转写完成。按任意键关闭窗口。"
read -k 1
