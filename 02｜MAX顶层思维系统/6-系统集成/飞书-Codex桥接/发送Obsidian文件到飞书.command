#!/bin/zsh
cd "$(dirname "$0")"
echo "发送 Obsidian Markdown 文件到飞书"
echo ""
echo "请把 Markdown 文件拖到这个窗口里，然后按回车。"
read "filepath?文件路径: "
filepath=${filepath#\'}
filepath=${filepath%\'}
filepath=${filepath#\"}
filepath=${filepath%\"}
if [ -z "$filepath" ]; then
  echo "没有输入文件路径，已取消。"
  read
  exit 1
fi
python3 feishu_codex.py push-md-as-message --file "$filepath"
echo ""
echo "按回车关闭窗口。"
read
