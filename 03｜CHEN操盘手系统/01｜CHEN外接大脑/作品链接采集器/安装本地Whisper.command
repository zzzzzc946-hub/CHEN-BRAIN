#!/bin/zsh
cd "$(dirname "$0")"
echo "正在安装本地 Whisper 转写引擎。首次安装会下载依赖，可能需要几分钟。"
python3 -m pip install --user -U openai-whisper
echo
echo "安装完成。按任意键关闭窗口。"
read -k 1
